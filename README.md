Azure DevOps (On-Prem) MCP Server

- Python MCP server exposing tools to read and manage Azure DevOps Server (on‑prem) Boards work items (Tasks, Bugs, PBIs, User Stories), Git Pull Requests, and Wiki pages.
- Works with Codex agents (and any MCP client) over stdio.

Features

- Work Items (Boards):
  - List projects: `list_projects`
  - Search with WIQL: `search_work_items`
  - Get work item: `get_work_item`
  - Create: `create_task`
  - Update fields/state/assignee/tags: `update_work_item`
  - Add history comment: `add_comment`
  - Assign: `assign_work_item`
  - Transition state: `transition_state`
  - Link items: `link_work_items`
- Pull Requests (Git):
  - List repositories: `list_repositories`
  - List PRs: `list_pull_requests`
  - Get PR: `get_pull_request`
  - Get PR diffs: `get_pr_diffs`
  - List PR commits: `list_pr_commits`
  - List PR threads: `list_pr_threads`
  - Comment on PR: `create_pr_comment`
  - List reviewers: `list_pr_reviewers`
  - Add reviewer: `add_pr_reviewer`
  - Set reviewer vote: `set_reviewer_vote`
  - Update PR: `update_pull_request`
  - Complete PR: `complete_pull_request`
  - Abandon PR: `abandon_pull_request`
- Wiki (Preview API):
  - List wikis: `list_wikis`
  - List pages: `list_wiki_pages`
  - Get page: `get_wiki_page`
  - Update page: `update_wiki_page`
  - Upsert page: `upsert_wiki_page`
  - Delete page: `delete_wiki_page`

Compatibility

- Azure DevOps Server 2019+ (most TFS/DevOps Server instances with PAT or NTLM auth).
- Auth: Personal Access Token (recommended) or NTLM (Windows Integrated).

Install (Poetry)

- Python 3.12+
- Install Poetry: `pip install poetry` or official installer
- In repo root: `poetry install`
- Run: `poetry run azure-devops-mcp`

Configure

- Required environment variables:
  - `AZDO_BASE_URL`: Base URL, e.g. `https://devops.corp.local/tfs` (or include collection like `/tfs/DefaultCollection`)
  - `AZDO_COLLECTION`: Optional if not included in `AZDO_BASE_URL` (e.g. `DefaultCollection`)
  - `AZDO_PROJECT`: Default project name
  - `AZDO_API_VERSION`: REST API version, default `7.0`
  - `AZDO_VERIFY_SSL`: `true|false`, default `true`
  - `AZDO_AUTH_TYPE`: `pat|ntlm`, default `pat`
  - For PAT: `AZDO_PAT` (scopes: Work Items read/write; for PRs Git read/write)
  - For NTLM: `AZDO_NTLM_USERNAME`, `AZDO_NTLM_PASSWORD`, optional `AZDO_NTLM_DOMAIN`
- Git (Pull Requests):
  - `AZDO_REPOSITORY`: Default repository name or ID

Examples

- PAT example:
  - `AZDO_BASE_URL=https://devops.corp.local/tfs`
  - `AZDO_COLLECTION=DefaultCollection`
  - `AZDO_PROJECT=MyProject`
  - `AZDO_PAT=xxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- NTLM example:
  - `AZDO_BASE_URL=https://tfs.corp.local/tfs/DefaultCollection`
  - `AZDO_PROJECT=Engineering`
  - `AZDO_AUTH_TYPE=ntlm`
  - `AZDO_NTLM_USERNAME=jdoe`
  - `AZDO_NTLM_PASSWORD=...`
  - `AZDO_NTLM_DOMAIN=CORP`

Run (manual)

- Start the MCP server via Poetry:
  - `poetry run azure-devops-mcp`
  - Or, after `poetry config virtualenvs.create false && poetry install`, run `azure-devops-mcp`

Use with Codex agents

- Add a server entry to your Codex MCP configuration:
  - `"mcpServers": { "azure-devops-mcp": { "command": "azure-devops-mcp" } }`
- If your launcher doesn’t inherit env vars, wrap with Poetry:
  - `"mcpServers": { "azure-devops-mcp": { "command": "poetry", "args": ["run", "azure-devops-mcp"] } }`
- Ensure the above environment variables are set in the process that launches the server.

Docker

- Build: `docker build -t azure-devops-mcp:latest .`
- Run (PAT example):
  - `docker run --rm -it \
     -e AZDO_BASE_URL=https://devops.corp.local/tfs \
     -e AZDO_COLLECTION=DefaultCollection \
     -e AZDO_PROJECT=MyProject \
     -e AZDO_AUTH_TYPE=pat \
     -e AZDO_PAT=xxxxxxxxxxxxxxxxxxxxxxxxxxxx \
     -e AZDO_REPOSITORY=MyRepo \
     azure-devops-mcp:latest`
- Run (NTLM example):
  - `docker run --rm -it \
     -e AZDO_BASE_URL=https://tfs.corp.local/tfs/DefaultCollection \
     -e AZDO_PROJECT=Engineering \
     -e AZDO_AUTH_TYPE=ntlm \
     -e AZDO_NTLM_USERNAME=jdoe \
     -e AZDO_NTLM_PASSWORD=... \
     -e AZDO_NTLM_DOMAIN=CORP \
     -e AZDO_REPOSITORY=MyRepo \
     azure-devops-mcp:latest`

Docker Compose

- Copy env template and edit:
  - Windows: `copy .env.example .env`
  - macOS/Linux: `cp .env.example .env`
- Build image: `docker compose build`
- Run interactively: `docker compose run --rm azure-devops-mcp`
- Use with Codex: set the MCP server command to `docker compose run --rm azure-devops-mcp`.

Tools (signatures)

- Work Items
  - `list_projects()`
  - `search_work_items(wiql, project?, top=50, expand="Relations")`
  - `get_work_item(id, expand="All")`
  - `create_task(project?, title, description?, assigned_to?, area_path?, iteration_path?, tags?, work_item_type="Task", state?)`
  - `update_work_item(id, title?, description?, assigned_to?, state?, add_tags?, remove_tags?, fields?, comment?)`
  - `add_comment(id, text)`
  - `assign_work_item(id, assigned_to)`
  - `transition_state(id, new_state)`
  - `link_work_items(source_id, target_id, link_type="System.LinkTypes.Hierarchy-Forward")`
- Pull Requests
  - `list_repositories(project?)`
  - `list_pull_requests(repository?, project?, status='active', creator_id?, reviewer_id?, target_ref_name?, source_ref_name?, top?)`
  - `get_pull_request(pr_id, repository?, project?)`
  - `get_pr_diffs(pr_id, repository?, project?, include_content=true, base_version?, target_version?, base_version_type?, target_version_type?)`
  - `list_pr_commits(pr_id, repository?, project?)`
  - `list_pr_threads(pr_id, repository?, project?)`
  - `create_pr_comment(pr_id, text, repository?, project?, file_path?, start_line?, end_line?)`
  - `list_pr_reviewers(pr_id, repository?, project?)`
  - `add_pr_reviewer(pr_id, reviewer_id, repository?, project?)`
  - `set_reviewer_vote(pr_id, reviewer_id, vote, repository?, project?)`
  - `update_pull_request(pr_id, repository?, project?, title?, description?, auto_complete_set?, completion_options?, status?)`
  - `complete_pull_request(pr_id, repository?, project?, delete_source_branch?, merge_commit_message?, merge_strategy?, transition_work_items?, squash_merge?)`
  - `abandon_pull_request(pr_id, repository?, project?)`
- Wiki (Preview)
  - `list_wikis(project?)`
  - `list_wiki_pages(wiki, project?, path?, recursion_level?, include_content=false)`
  - `get_wiki_page(wiki, path, project?, include_content=true)`
  - `update_wiki_page(wiki, path, content, project?, comment?, version?)`
  - `upsert_wiki_page(wiki, path, content, project?, comment?)`
  - `delete_wiki_page(wiki, path, project?, comment?)`

On-Prem Notes

- Collections: Many on‑prem instances include a collection in the REST base path (e.g., `/tfs/DefaultCollection`). Set via `AZDO_COLLECTION` or include in `AZDO_BASE_URL`.
- API Versions: Use a version supported by your server (e.g., 6.0, 7.0). If you see version errors, lower `AZDO_API_VERSION`.
- Comments: For work items, comments are added via `System.History` updates for compatibility.

Permissions

- PAT scope: Work Items (Read & Write) at minimum; for PR tools include Git permissions; for Wiki tools include Wiki permissions as required.
- Ensure project permissions allow editing work items and completing PRs.

Troubleshooting

- Auth failures:
  - PAT: verify PAT validity; try a REST call in a browser.
  - NTLM: confirm domain\username and password; test with `curl --ntlm`.
- API version errors: adjust `AZDO_API_VERSION` (e.g., `6.0`, `7.0`).
- SSL/PKI issues: set `AZDO_VERIFY_SSL=false` for test environments or install your enterprise root CA.

Development

- Install: `poetry install`
- Run with logging: set `MCP_LOG_LEVEL=DEBUG` then `poetry run azure-devops-mcp`
- Code layout:
  - `src/azure_devops_mcp/server.py`
  - `src/azure_devops_mcp/ado_client.py`
  - `src/azure_devops_mcp/config.py`

Locking & Reproducibility

- Generate lock file: `poetry lock` (or use helper scripts in `scripts/` if present)
- Commit `poetry.lock` for deterministic installs. The Dockerfile copies `poetry.lock*` to leverage layer caching.

Security

- Store PATs securely (OS keychain/secret manager). Avoid committing env values.
- Prefer PAT over NTLM for service integrations.
