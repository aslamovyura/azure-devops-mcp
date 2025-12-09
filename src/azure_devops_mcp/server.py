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


def main():
    # Allow simple logging control
    os.environ.setdefault("MCP_LOG_LEVEL", "INFO")
    mcp.run()


if __name__ == "__main__":
    main()

