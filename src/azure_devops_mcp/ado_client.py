from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

import requests
from requests_ntlm import HttpNtlmAuth

from .config import AzureDevOpsConfig


class AzureDevOpsError(RuntimeError):
    pass


class AzureDevOpsClient:
    def __init__(self, cfg: AzureDevOpsConfig):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.verify = cfg.verify_ssl

        if cfg.auth_type == "pat":
            # PAT as basic auth: username can be anything, PAT is password
            token = f":{cfg.pat}".encode("utf-8")
            b64 = base64.b64encode(token).decode("ascii")
            self.session.headers.update({
                "Authorization": f"Basic {b64}",
            })
        else:  # ntlm
            domain_prefix = f"{cfg.ntlm_domain}\\" if cfg.ntlm_domain else ""
            self.session.auth = HttpNtlmAuth(domain_prefix + cfg.ntlm_username, cfg.ntlm_password)

        # Default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "azure-devops-mcp/0.1.0",
        })

    # URL helpers
    def _collection_prefix(self) -> str:
        # On-prem often at {base}/tfs/{collection}; allow users to include collection in base or as separate var
        if self.cfg.collection:
            return f"{self.cfg.base_url}/{self.cfg.collection.strip('/') }"
        return self.cfg.base_url

    def _api(self, path: str, project: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> str:
        base = self._collection_prefix()
        if project:
            base = f"{base}/{project.strip('/')}"
        if not path.startswith("/"):
            path = "/" + path
        # Always include api-version if not present in params
        if params is None or "api-version" not in (params or {}):
            # We add api-version as query string later via requests params
            pass
        return f"{base}{path}"

    def _ensure_params(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        p = dict(params or {})
        p.setdefault("api-version", self.cfg.api_version)
        return p

    # Basic HTTP helpers
    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = self.session.get(url, params=self._ensure_params(params))
        if not resp.ok:
            raise AzureDevOpsError(f"GET {url} failed: {resp.status_code} {resp.text}")
        return resp.json()

    def _post(self, url: str, json: Any, params: Optional[Dict[str, Any]] = None, content_type: Optional[str] = None) -> Dict[str, Any]:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        resp = self.session.post(url, json=json, params=self._ensure_params(params), headers=headers)
        if not resp.ok:
            raise AzureDevOpsError(f"POST {url} failed: {resp.status_code} {resp.text}")
        return resp.json()

    def _patch(self, url: str, json: Any, params: Optional[Dict[str, Any]] = None, content_type: Optional[str] = None) -> Dict[str, Any]:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        resp = self.session.patch(url, json=json, params=self._ensure_params(params), headers=headers)
        if not resp.ok:
            raise AzureDevOpsError(f"PATCH {url} failed: {resp.status_code} {resp.text}")
        return resp.json()

    def _put(
        self,
        url: str,
        json: Any,
        params: Optional[Dict[str, Any]] = None,
        content_type: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        hdrs: Dict[str, str] = dict(headers or {})
        if content_type:
            hdrs["Content-Type"] = content_type
        resp = self.session.put(url, json=json, params=self._ensure_params(params), headers=hdrs)
        if not resp.ok:
            raise AzureDevOpsError(f"PUT {url} failed: {resp.status_code} {resp.text}")
        return resp.json()

    def _delete(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = self.session.delete(url, params=self._ensure_params(params))
        if not resp.ok:
            raise AzureDevOpsError(f"DELETE {url} failed: {resp.status_code} {resp.text}")
        # Some delete endpoints return an empty body
        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code}

    # Public API
    def list_projects(self) -> List[Dict[str, Any]]:
        url = self._api("/_apis/projects")
        data = self._get(url)
        return data.get("value", [])

    def wiql_query(self, wiql: str, project: Optional[str] = None, top: Optional[int] = None) -> List[int]:
        proj = project or self.cfg.default_project
        if not proj:
            raise AzureDevOpsError("Project is required (set AZDO_PROJECT or pass project)")
        url = self._api("/_apis/wit/wiql", project=proj)
        payload: Dict[str, Any] = {"query": wiql}
        if top is not None:
            payload["top"] = top
        data = self._post(url, json=payload)
        # WIQL returns workItems: [{id, url}]
        items = data.get("workItems", [])
        return [it.get("id") for it in items if "id" in it]

    def get_work_item(self, id: int, expand: Optional[str] = None) -> Dict[str, Any]:
        url = self._api(f"/_apis/wit/workitems/{id}")
        params = {}
        if expand:
            params["$expand"] = expand
        return self._get(url, params=params)

    def get_work_items(self, ids: List[int], expand: Optional[str] = None) -> List[Dict[str, Any]]:
        if not ids:
            return []
        url = self._api("/_apis/wit/workitemsbatch")
        body: Dict[str, Any] = {"ids": ids}
        if expand:
            body["$expand"] = expand
        data = self._post(url, json=body)
        return data.get("value", []) or data.get("workItems", [])

    def create_work_item(
        self,
        project: str,
        work_item_type: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = self._api(f"/_apis/wit/workitems/${work_item_type}", project=project)
        patch_ops: List[Dict[str, Any]] = []
        for key, value in fields.items():
            patch_ops.append({"op": "add", "path": f"/fields/{key}", "value": value})
        return self._patch(url, json=patch_ops, content_type="application/json-patch+json")

    def update_work_item(self, id: int, ops: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = self._api(f"/_apis/wit/workitems/{id}")
        return self._patch(url, json=ops, content_type="application/json-patch+json")

    def add_history_comment(self, id: int, text: str) -> Dict[str, Any]:
        ops = [{"op": "add", "path": "/fields/System.History", "value": text}]
        return self.update_work_item(id, ops)

    def link_work_items(self, source_id: int, target_id: int, link_type: str) -> Dict[str, Any]:
        # Relation object requires URL to target work item
        target_url = f"{self._collection_prefix()}/_apis/wit/workItems/{target_id}"
        ops = [
            {
                "op": "add",
                "path": "/relations/-",
                "value": {"rel": link_type, "url": target_url},
            }
        ]
        return self.update_work_item(source_id, ops)

    # Wiki APIs (preview)
    def list_wikis(self, project: Optional[str] = None) -> List[Dict[str, Any]]:
        """List wikis in a project or collection.

        Uses preview API version for broader compatibility with Wiki endpoints.
        """
        url = self._api("/_apis/wiki/wikis", project=project or self.cfg.default_project)
        params = {"api-version": "7.1-preview.1"}
        data = self._get(url, params=params)
        return data.get("value", [])

    def list_wiki_pages(
        self,
        wiki: str,
        project: Optional[str] = None,
        path: Optional[str] = None,
        recursion_level: Optional[str] = None,
        include_content: bool = False,
    ) -> Dict[str, Any]:
        """List pages for a wiki. Optionally scope by `path` and include content.

        Returns the raw response which includes a `value` array of pages.
        """
        proj = project or self.cfg.default_project
        if not proj:
            raise AzureDevOpsError("Project is required (set AZDO_PROJECT or pass project)")
        url = self._api(f"/_apis/wiki/wikis/{wiki}/pages", project=proj)
        params: Dict[str, Any] = {"api-version": "7.1-preview.1"}
        if path:
            params["path"] = path
        if recursion_level:
            params["recursionLevel"] = recursion_level
        if include_content:
            params["includeContent"] = "true"
        return self._get(url, params=params)

    def get_wiki_page(
        self,
        wiki: str,
        path: str,
        project: Optional[str] = None,
        include_content: bool = True,
    ) -> Dict[str, Any]:
        """Get a single wiki page by path. Returns metadata and optionally content."""
        proj = project or self.cfg.default_project
        if not proj:
            raise AzureDevOpsError("Project is required (set AZDO_PROJECT or pass project)")
        url = self._api(f"/_apis/wiki/wikis/{wiki}/pages", project=proj)
        params: Dict[str, Any] = {"api-version": "7.1-preview.1", "path": path}
        if include_content:
            params["includeContent"] = "true"
        return self._get(url, params=params)

    def upsert_wiki_page(
        self,
        wiki: str,
        path: str,
        content: str,
        project: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a wiki page by path with markdown content."""
        proj = project or self.cfg.default_project
        if not proj:
            raise AzureDevOpsError("Project is required (set AZDO_PROJECT or pass project)")
        url = self._api(f"/_apis/wiki/wikis/{wiki}/pages", project=proj)
        params: Dict[str, Any] = {"api-version": "7.1-preview.1", "path": path}
        body: Dict[str, Any] = {"content": content}
        if comment:
            body["comment"] = comment
        return self._put(url, json=body, params=params)

    def update_wiki_page(
        self,
        wiki: str,
        path: str,
        content: str,
        project: Optional[str] = None,
        comment: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing wiki page by path with markdown content.

        Uses optimistic concurrency via `If-Match` header. If `version` is not
        provided, the current version is fetched first. This avoids accidentally
        creating a new page and ensures we edit an existing one.
        """
        proj = project or self.cfg.default_project
        if not proj:
            raise AzureDevOpsError("Project is required (set AZDO_PROJECT or pass project)")

        # Resolve current version if not provided
        current_version: Optional[str] = version
        if current_version is None:
            url_get = self._api(f"/_apis/wiki/wikis/{wiki}/pages", project=proj)
            params_get: Dict[str, Any] = {"api-version": "7.1-preview.1", "path": path}
            page = self._get(url_get, params=params_get)
            # Azure DevOps typically returns eTag for pages; fall back to version if present
            current_version = (
                (page.get("eTag") if isinstance(page, dict) else None)
                or (str(page.get("version")) if isinstance(page, dict) and page.get("version") is not None else None)
            )
            if not current_version:
                raise AzureDevOpsError("Unable to determine current page version; pass version explicitly")

        url_put = self._api(f"/_apis/wiki/wikis/{wiki}/pages", project=proj)
        params_put: Dict[str, Any] = {"api-version": "7.1-preview.1", "path": path}
        body: Dict[str, Any] = {"content": content}
        if comment:
            body["comment"] = comment
        # Set If-Match for optimistic concurrency control
        headers = {"If-Match": str(current_version)}
        return self._put(url_put, json=body, params=params_put, headers=headers)

    def delete_wiki_page(
        self,
        wiki: str,
        path: str,
        project: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete a wiki page by path."""
        proj = project or self.cfg.default_project
        if not proj:
            raise AzureDevOpsError("Project is required (set AZDO_PROJECT or pass project)")
        url = self._api(f"/_apis/wiki/wikis/{wiki}/pages", project=proj)
        params: Dict[str, Any] = {"api-version": "7.1-preview.1", "path": path}
        if comment:
            params["comment"] = comment
        return self._delete(url, params=params)

    # Convenience helpers for common fields
    @staticmethod
    def build_fields(
        title: Optional[str] = None,
        description: Optional[str] = None,
        assigned_to: Optional[str] = None,
        state: Optional[str] = None,
        area_path: Optional[str] = None,
        iteration_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        if title is not None:
            fields["System.Title"] = title
        if description is not None:
            fields["System.Description"] = description
        if assigned_to is not None:
            fields["System.AssignedTo"] = assigned_to
        if state is not None:
            fields["System.State"] = state
        if area_path is not None:
            fields["System.AreaPath"] = area_path
        if iteration_path is not None:
            fields["System.IterationPath"] = iteration_path
        if tags is not None:
            fields["System.Tags"] = "; ".join(tag.strip() for tag in tags if tag and tag.strip())
        if extra:
            fields.update(extra)
        return fields

    @staticmethod
    def patch_from_fields(fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"op": "add", "path": f"/fields/{k}", "value": v} for k, v in fields.items()]
