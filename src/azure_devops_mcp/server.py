from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .ado_client import AzureDevOpsClient, AzureDevOpsError
from .config import AzureDevOpsConfig


def _client() -> AzureDevOpsClient:
    cfg = AzureDevOpsConfig.from_env()
    return AzureDevOpsClient(cfg)


mcp = FastMCP("azure-devops-mcp", json_response=True)


@mcp.tool()
def list_projects() -> List[Dict[str, Any]]:
    """List accessible Azure DevOps projects."""
    client = _client()
    return client.list_projects()


@mcp.tool()
def search_work_items(
    wiql: str,
    project: Optional[str] = None,
    top: Optional[int] = 50,
    expand: Optional[str] = "Relations",
) -> List[Dict[str, Any]]:
    """Search work items using WIQL; returns expanded work item documents.

    - wiql: e.g. "Select [System.Id] From WorkItems Where [System.TeamProject] = @project And [System.WorkItemType] = 'Task' Order By [System.ChangedDate] DESC"
    - project: fallback to AZDO_PROJECT when omitted
    - top: max number of results
    - expand: None|Relations|Fields|Links|All
    """
    client = _client()
    ids = client.wiql_query(wiql, project=project, top=top)
    return client.get_work_items(ids, expand=expand)


@mcp.tool()
def get_work_item(id: int, expand: Optional[str] = "All") -> Dict[str, Any]:
    """Get a single work item by id."""
    client = _client()
    return client.get_work_item(id, expand=expand)


@mcp.tool()
def create_task(
    project: Optional[str] = None,
    title: str = "",
    description: str = "",
    assigned_to: Optional[str] = None,
    area_path: Optional[str] = None,
    iteration_path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    work_item_type: str = "Task",
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new work item (default type Task) in a project.

    Common work item types: Task, Bug, User Story, Product Backlog Item.
    """
    client = _client()
    proj = project or client.cfg.default_project
    if not proj:
        raise AzureDevOpsError("Project is required (set AZDO_PROJECT or pass project)")
    fields = AzureDevOpsClient.build_fields(
        title=title or "Untitled",
        description=description or None,
        assigned_to=assigned_to,
        state=state,
        area_path=area_path,
        iteration_path=iteration_path,
        tags=tags,
    )
    return client.create_work_item(proj, work_item_type, fields)


@mcp.tool()
def update_work_item(
    id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    assigned_to: Optional[str] = None,
    state: Optional[str] = None,
    add_tags: Optional[List[str]] = None,
    remove_tags: Optional[List[str]] = None,
    fields: Optional[Dict[str, Any]] = None,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a work item: set fields/state/assignee/tags and optionally add a comment."""
    client = _client()
    ops: List[Dict[str, Any]] = []
    # Simple fields
    f = AzureDevOpsClient.build_fields(
        title=title,
        description=description,
        assigned_to=assigned_to,
        state=state,
    )
    if fields:
        f.update(fields)
    for k, v in f.items():
        ops.append({"op": "add", "path": f"/fields/{k}", "value": v})

    # Tags adjustments
    if add_tags:
        ops.append({"op": "add", "path": "/fields/System.Tags", "value": "; ".join(add_tags)})
    if remove_tags:
        # Note: Removing specific tags requires reading current tags and replacing; here we simply replace with a filtered set is not implemented.
        # For safety, we add an explicit replace instruction with computed value if user provided replacement via fields.
        pass

    # History comment
    if comment:
        ops.append({"op": "add", "path": "/fields/System.History", "value": comment})

    return client.update_work_item(id, ops)


@mcp.tool()
def add_comment(id: int, text: str) -> Dict[str, Any]:
    """Add a history comment to a work item."""
    client = _client()
    return client.add_history_comment(id, text)


@mcp.tool()
def assign_work_item(id: int, assigned_to: str) -> Dict[str, Any]:
    """Assign a work item to a user (display name or email)."""
    client = _client()
    ops = [{"op": "add", "path": "/fields/System.AssignedTo", "value": assigned_to}]
    return client.update_work_item(id, ops)


@mcp.tool()
def transition_state(id: int, new_state: str) -> Dict[str, Any]:
    """Move a work item to a new state (e.g., New, Active, Resolved, Closed)."""
    client = _client()
    ops = [{"op": "add", "path": "/fields/System.State", "value": new_state}]
    return client.update_work_item(id, ops)


@mcp.tool()
def link_work_items(
    source_id: int,
    target_id: int,
    link_type: str = "System.LinkTypes.Hierarchy-Forward",
) -> Dict[str, Any]:
    """Link two work items (default: parent->child hierarchy forward)."""
    client = _client()
    return client.link_work_items(source_id, target_id, link_type)


# Git: Repositories
@mcp.tool()
def list_repositories(project: Optional[str] = None) -> List[Dict[str, Any]]:
    """List Git repositories for a project."""
    client = _client()
    return client.list_repositories(project=project)


# Git: Pull Requests
@mcp.tool()
def list_pull_requests(
    repository: Optional[str] = None,
    project: Optional[str] = None,
    status: str = "active",
    creator_id: Optional[str] = None,
    reviewer_id: Optional[str] = None,
    target_ref_name: Optional[str] = None,
    source_ref_name: Optional[str] = None,
    top: Optional[int] = 25,
) -> List[Dict[str, Any]]:
    """List pull requests in a repository with optional filters."""
    client = _client()
    return client.list_pull_requests(
        repository=repository,
        project=project,
        status=status,
        creator_id=creator_id,
        reviewer_id=reviewer_id,
        target_ref_name=target_ref_name,
        source_ref_name=source_ref_name,
        top=top,
    )


@mcp.tool()
def get_pr_diffs(
    pr_id: int,
    repository: Optional[str] = None,
    project: Optional[str] = None,
    include_content: bool = False,
    top: Optional[int] = None,
    skip: Optional[int] = None,
) -> Dict[str, Any]:
    """Get diffs of the code in a Pull Request.

    - Returns file-level change list via `diffs/commits`.
    - `include_content=true` requests hunk content where the server supports it; some on-prem versions omit hunks regardless.
    - If branch refs cannot be resolved (TF401175), the server falls back to commit IDs automatically.
    """
    client = _client()
    return client.get_pr_diffs(
        pr_id,
        repository=repository,
        project=project,
        include_content=include_content,
        top=top,
        skip=skip,
    )


@mcp.tool()
def get_pull_request(
    pr_id: int,
    repository: Optional[str] = None,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """Get a single pull request."""
    client = _client()
    return client.get_pull_request(pr_id, repository=repository, project=project)


@mcp.tool()
def list_pr_commits(
    pr_id: int,
    repository: Optional[str] = None,
    project: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List commits included in a pull request."""
    client = _client()
    return client.list_pr_commits(pr_id, repository=repository, project=project)


@mcp.tool()
def list_pr_threads(
    pr_id: int,
    repository: Optional[str] = None,
    project: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List discussion threads for a pull request."""
    client = _client()
    return client.list_pr_threads(pr_id, repository=repository, project=project)


@mcp.tool()
def get_pr_file_content(
    pr_id: int,
    path: str,
    repository: Optional[str] = None,
    project: Optional[str] = None,
    side: str = "source",
) -> Dict[str, Any]:
    """Download file content at a PR's source/target.

    - side: 'source' | 'target' | 'both'
    - Returns base64-encoded content plus commit/ref metadata.
    - Uses Git items API with `versionDescriptor` so it works without direct file URL auth.
    """
    client = _client()
    return client.get_pr_file_content(
        pr_id,
        path,
        repository=repository,
        project=project,
        side=side,
    )


@mcp.tool()
def create_pr_comment(
    pr_id: int,
    text: str,
    repository: Optional[str] = None,
    project: Optional[str] = None,
    file_path: Optional[str] = None,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a PR comment (optionally file/line-scoped)."""
    client = _client()
    return client.create_pr_comment(
        pr_id,
        text,
        repository=repository,
        project=project,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
    )


@mcp.tool()
def list_pr_reviewers(
    pr_id: int,
    repository: Optional[str] = None,
    project: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List reviewers and their vote states."""
    client = _client()
    return client.list_pr_reviewers(pr_id, repository=repository, project=project)


@mcp.tool()
def add_pr_reviewer(
    pr_id: int,
    reviewer_id: str,
    repository: Optional[str] = None,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a reviewer to a pull request by identity ID."""
    client = _client()
    return client.add_pr_reviewer(pr_id, reviewer_id, repository=repository, project=project)


@mcp.tool()
def set_reviewer_vote(
    pr_id: int,
    reviewer_id: str,
    vote: int,
    repository: Optional[str] = None,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """Set a reviewer's vote on a PR. Votes: -10, -5, 0, 5, 10."""
    client = _client()
    return client.set_reviewer_vote(pr_id, reviewer_id, vote, repository=repository, project=project)


@mcp.tool()
def update_pull_request(
    pr_id: int,
    repository: Optional[str] = None,
    project: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    auto_complete_set: Optional[bool] = None,
    completion_options: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a pull request title/description/auto-complete/options/status."""
    client = _client()
    return client.update_pull_request(
        pr_id,
        repository=repository,
        project=project,
        title=title,
        description=description,
        auto_complete_set=auto_complete_set,
        completion_options=completion_options,
        status=status,
    )


@mcp.tool()
def complete_pull_request(
    pr_id: int,
    repository: Optional[str] = None,
    project: Optional[str] = None,
    delete_source_branch: Optional[bool] = None,
    merge_commit_message: Optional[str] = None,
    merge_strategy: Optional[str] = None,
    transition_work_items: Optional[bool] = None,
    squash_merge: Optional[bool] = None,
) -> Dict[str, Any]:
    """Complete (merge) a pull request with optional completion options."""
    client = _client()
    return client.complete_pull_request(
        pr_id,
        repository=repository,
        project=project,
        delete_source_branch=delete_source_branch,
        merge_commit_message=merge_commit_message,
        merge_strategy=merge_strategy,
        transition_work_items=transition_work_items,
        squash_merge=squash_merge,
    )


@mcp.tool()
def abandon_pull_request(
    pr_id: int,
    repository: Optional[str] = None,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """Abandon (close without merging) a pull request."""
    client = _client()
    return client.abandon_pull_request(pr_id, repository=repository, project=project)

# Test tools
@mcp.tool()
def list_test_plans(project: Optional[str] = None) -> List[Dict[str, Any]]:
    """List test plans for a project."""
    client = _client()
    return client.list_test_plans(project=project)


@mcp.tool()
def list_test_suites(plan_id: int, project: Optional[str] = None) -> List[Dict[str, Any]]:
    """List test suites under a test plan."""
    client = _client()
    return client.list_test_suites(plan_id, project=project)


@mcp.tool()
def list_test_cases(
    plan_id: int,
    suite_id: int,
    project: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List test cases assigned to a suite within a plan."""
    client = _client()
    return client.list_test_cases(plan_id, suite_id, project=project)


@mcp.tool()
def create_test_case(
    project: Optional[str] = None,
    title: str = "",
    description: str = "",
    assigned_to: Optional[str] = None,
    area_path: Optional[str] = None,
    iteration_path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    state: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a Test Case work item with common fields."""
    client = _client()
    proj = project or client.cfg.default_project
    if not proj:
        raise AzureDevOpsError("Project is required (set AZDO_PROJECT or pass project)")
    return client.create_test_case(
        project=proj,
        title=title or "Untitled",
        description=description or None,
        assigned_to=assigned_to,
        area_path=area_path,
        iteration_path=iteration_path,
        tags=tags,
        state=state,
        extra_fields=extra_fields,
    )


@mcp.tool()
def add_test_case_to_suite(
    plan_id: int,
    suite_id: int,
    test_case_id: int,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a test case (by work item id) to a test suite."""
    client = _client()
    return client.add_test_case_to_suite(plan_id, suite_id, test_case_id, project=project)


@mcp.tool()
def remove_test_case_from_suite(
    plan_id: int,
    suite_id: int,
    test_case_id: int,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """Remove a test case from a test suite."""
    client = _client()
    return client.remove_test_case_from_suite(plan_id, suite_id, test_case_id, project=project)


@mcp.tool()
def get_suite_test_case_work_items(
    plan_id: int,
    suite_id: int,
    project: Optional[str] = None,
    expand: Optional[str] = "Fields",
) -> List[Dict[str, Any]]:
    """Return underlying Test Case work items for cases in a suite (batch)."""
    client = _client()
    return client.get_suite_test_case_work_items(plan_id, suite_id, project=project, expand=expand)


@mcp.tool()
def get_test_case_steps_from_work_item(work_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse and extract test steps from a Test Case work item fields.

    Looks at `Microsoft.VSTS.TCM.Steps` field, parses the XML, and returns
    a simplified list of {action, expected} pairs. Returns empty list on
    missing or unparsable steps.
    """
    steps_xml = None
    fields = work_item.get('fields') if isinstance(work_item, dict) else None
    if isinstance(fields, dict):
        steps_xml = fields.get('Microsoft.VSTS.TCM.Steps')
    client = _client()
    return client.parse_test_steps_xml(steps_xml)


@mcp.tool()
def list_work_item_attachments(work_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List attachment metadata (name + URL) from a work item document."""
    client = _client()
    return client.extract_attachments_from_work_item(work_item)


@mcp.tool()
def download_attachment(url: str) -> str:
    """Download an attachment by its relation URL and return as base64 string."""
    import base64
    client = _client()
    data = client.download_attachment(url)
    return base64.b64encode(data).decode('ascii')


@mcp.tool()
def get_test_case_work_item(id: int, expand: Optional[str] = "All") -> Dict[str, Any]:
    """Get a single Test Case work item by id (expanded)."""
    client = _client()
    return client.get_test_case_work_item(id)


@mcp.tool()
def get_test_case_steps(id: int) -> List[Dict[str, Any]]:
    """Fetch a Test Case work item and extract its steps as {action, expected}."""
    client = _client()
    wi = client.get_test_case_work_item(id)
    fields = wi.get('fields') if isinstance(wi, dict) else None
    steps_xml = (fields or {}).get('Microsoft.VSTS.TCM.Steps') if isinstance(fields, dict) else None
    return client.parse_test_steps_xml(steps_xml)
# Wiki tools
@mcp.tool()
def list_wikis(project: Optional[str] = None) -> List[Dict[str, Any]]:
    """List wikis in a project or collection."""
    client = _client()
    return client.list_wikis(project=project or client.cfg.default_project)


@mcp.tool()
def list_wiki_pages(
    wiki: str,
    project: Optional[str] = None,
    path: Optional[str] = None,
    recursion_level: Optional[str] = None,
    include_content: bool = False,
) -> Dict[str, Any]:
    """List pages in a wiki; optionally filter by path and include content."""
    client = _client()
    return client.list_wiki_pages(
        wiki=wiki,
        project=project,
        path=path,
        recursion_level=recursion_level,
        include_content=include_content,
    )


@mcp.tool()
def get_wiki_page(
    wiki: str,
    path: str,
    project: Optional[str] = None,
    include_content: bool = True,
) -> Dict[str, Any]:
    """Get a single wiki page by path."""
    client = _client()
    return client.get_wiki_page(wiki=wiki, path=path, project=project, include_content=include_content)


@mcp.tool()
def upsert_wiki_page(
    wiki: str,
    path: str,
    content: str,
    project: Optional[str] = None,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update a wiki page with markdown content."""
    client = _client()
    return client.upsert_wiki_page(wiki=wiki, path=path, content=content, project=project, comment=comment)


@mcp.tool()
def update_wiki_page(
    wiki: str,
    path: str,
    content: str,
    project: Optional[str] = None,
    comment: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing wiki page with markdown content.

    Uses optimistic concurrency via If-Match. Optionally pass a specific
    version/eTag to guard the update; if omitted, the current version is
    fetched first.
    """
    client = _client()
    return client.update_wiki_page(
        wiki=wiki,
        path=path,
        content=content,
        project=project,
        comment=comment,
        version=version,
    )


@mcp.tool()
def delete_wiki_page(
    wiki: str,
    path: str,
    project: Optional[str] = None,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a wiki page by path."""
    client = _client()
    return client.delete_wiki_page(wiki=wiki, path=path, project=project, comment=comment)


def main():
    # Allow simple logging control
    os.environ.setdefault("MCP_LOG_LEVEL", "INFO")
    mcp.run()


if __name__ == "__main__":
    main()
