**Azure DevOps (On‑Prem) MCP Server**

- Python MCP server exposing tools to read and manage Azure DevOps Server (on‑prem) Boards work items (Tasks, Bugs, PBIs, User Stories).
- Works with Codex agents (and any MCP client) over stdio.

**Features**

- List projects: `list_projects`
- Search work items with WIQL: `search_work_items`
- Get work item by id: `get_work_item`
- Create task/user story/bug: `create_task`
- Update fields/state/assignee/tags: `update_work_item`
- Add history comment: `add_comment`
- Assign work item: `assign_work_item`
- Transition state: `transition_state`
- Link work items: `link_work_items`

**Compatibility**

- Azure DevOps Server 2019+ (and most TFS/DevOps Server instances with PAT or NTLM auth).
- Auth: Personal Access Token (recommended) or NTLM (Windows Integrated).

**Install (Poetry)**

- Python 3.9+
- Install Poetry (<https://python-poetry.org/>): `pip install poetry` or official installer
- In repo root: `poetry install`
- Run: `poetry run azure-devops-mcp`

**Configure**

- Set these environment variables (e.g., in your shell profile or process env):
  - `AZDO_BASE_URL`: Base URL to your server, e.g. `https://tfs.corp.local/tfs` or `https://devops.corp.local/tfs/DefaultCollection`
  - `AZDO_COLLECTION`: Optional when not included in `AZDO_BASE_URL`, e.g. `DefaultCollection`
  - `AZDO_PROJECT`: Default project name (used when not passed in tools)
  - `AZDO_API_VERSION`: REST API version, default `7.0` (use a version supported by your server)
  - `AZDO_VERIFY_SSL`: `true|false`, default `true`
  - `AZDO_AUTH_TYPE`: `pat|ntlm`, default `pat`
  - For PAT: `AZDO_PAT`: Personal Access Token with Work Items scope (Read & Write)
  - For NTLM: `AZDO_NTLM_USERNAME`, `AZDO_NTLM_PASSWORD`, optional `AZDO_NTLM_DOMAIN`

Examples:

- PAT on 2019/2020/2022:
  - `AZDO_BASE_URL=https://devops.corp.local/tfs`
  - `AZDO_COLLECTION=DefaultCollection`
  - `AZDO_PROJECT=MyProject`
  - `AZDO_PAT=xxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- NTLM (only if PAT unavailable):
  - `AZDO_BASE_URL=https://tfs.corp.local/tfs/DefaultCollection`
  - `AZDO_PROJECT=Engineering`
  - `AZDO_AUTH_TYPE=ntlm`
  - `AZDO_NTLM_USERNAME=jdoe`
  - `AZDO_NTLM_PASSWORD=...`
  - `AZDO_NTLM_DOMAIN=CORP`

**Run (manual)**

- Start the MCP server via Poetry:
  - `poetry run azure-devops-mcp`
  - Or, after `poetry config virtualenvs.create false && poetry install`, use: `azure-devops-mcp`

**Use with Codex agents**

- Add a server entry to your Codex MCP configuration (example JSON snippet):
  - `"mcpServers": { "azure-devops-mcp": { "command": "azure-devops-mcp" } }`
- If your launcher doesn’t inherit env vars, wrap with Poetry to ensure the environment is correct:
  - `"mcpServers": { "azure-devops-mcp": { "command": "poetry", "args": ["run", "azure-devops-mcp"] } }`
- Ensure the above environment variables are set in the process starting Codex so the server inherits them.
- Tools will appear to the agent as callable functions; pass parameters per tool signatures below.

**Docker**

- Build:
  - `docker build -t azure-devops-mcp:latest .`
- Run (PowerShell example with PAT):
  - `docker run --rm -it`
    `-e AZDO_BASE_URL=https://devops.corp.local/tfs`
    `-e AZDO_COLLECTION=DefaultCollection`
    `-e AZDO_PROJECT=MyProject`
    `-e AZDO_AUTH_TYPE=pat`
    `-e AZDO_PAT=xxxxxxxxxxxxxxxxxxxxxxxxxxxx`
    `azure-devops-mcp:latest`
- Run (NTLM example):
  - `docker run --rm -it`
    `-e AZDO_BASE_URL=https://tfs.corp.local/tfs/DefaultCollection`
    `-e AZDO_PROJECT=Engineering`
    `-e AZDO_AUTH_TYPE=ntlm`
    `-e AZDO_NTLM_USERNAME=jdoe`
    `-e AZDO_NTLM_PASSWORD=...`
    `-e AZDO_NTLM_DOMAIN=CORP`
    `azure-devops-mcp:latest`

Notes:

- MCP servers typically run over stdio and are launched by the MCP client. Containerization is handy for standardizing dependencies and secrets. If Codex needs to spawn the server inside Docker, use a wrapper script or configure Codex to execute `docker run ...` as the command for this MCP server.

**Docker Compose**

- Copy env template and edit:
  - `copy .env.example .env` (Windows) or `cp .env.example .env`
- Build image: `docker compose build`
- Run interactively: `docker compose run --rm azure-devops-mcp`
- Use with Codex: set the MCP server command to `docker compose run --rm azure-devops-mcp` so Codex launches the server inside the container.

Compose file: `docker-compose.yml:1`; Env template: `.env.example:1`

**Wrapper Scripts (recommended for Codex)**

- Windows: `bin/azure-devops-mcp.cmd`
  - Use in Codex config as the command: `"command": "bin/azure-devops-mcp.cmd"`
- macOS/Linux: `bin/azure-devops-mcp.sh`
  - Make executable once: `chmod +x bin/azure-devops-mcp.sh`
  - Use in Codex config as the command: `"command": "bin/azure-devops-mcp.sh"`
- Both wrappers run `docker compose run --rm azure-devops-mcp` from the repo root and load env from `.env`.

**Tools**

- `list_projects()`
  - Returns list of projects.
- `search_work_items(wiql, project?, top=50, expand="Relations")`
  - Runs a WIQL query in `project` (defaults to `AZDO_PROJECT`).
  - Returns expanded work item docs. Example WIQL: `Select [System.Id] From WorkItems Where [System.TeamProject] = @project And [System.WorkItemType] = 'Task' Order By [System.ChangedDate] DESC`.
- `get_work_item(id, expand="All")`
  - Returns a single work item with fields/relations.
- `create_task(project?, title, description?, assigned_to?, area_path?, iteration_path?, tags?, work_item_type="Task", state?)`
  - Creates a work item (Task/Bug/User Story/PBI) in `project`.
- `update_work_item(id, title?, description?, assigned_to?, state?, add_tags?, remove_tags?, fields?, comment?)`
  - Sets fields/state/assignee; adds tags; appends a history comment.
  - Note: selective tag removal requires reading/replacing tags; this server does not compute removals automatically.
- `add_comment(id, text)`
  - Adds a history entry to the work item.
- `assign_work_item(id, assigned_to)`
  - Assigns the item to a user display name or email.
- `transition_state(id, new_state)`
  - Moves the item to a new workflow state.
- `link_work_items(source_id, target_id, link_type="System.LinkTypes.Hierarchy-Forward")`
  - Creates a work item relation (default: parent->child).

**On‑Prem Notes**

- Collections: On many on‑prem instances the REST path includes a collection (e.g., `.../tfs/DefaultCollection`). You can set this via `AZDO_COLLECTION` or include it in `AZDO_BASE_URL`.
- API Versions: Use a version supported by your server: Azure DevOps Server 2020 usually supports `6.0` and `7.0` preview; 2022+ supports `7.0`. If you see version errors, lower `AZDO_API_VERSION`.
- Comments: For broad compatibility, comments are added via `System.History` field updates.

**Permissions**

- PAT scope: Work Items (Read & Write) at minimum.
- Assigning/updating items also requires project permissions (e.g., edit work items in this node).

**Troubleshooting**

- Authentication failures:
  - PAT: ensure PAT is valid and not expired; try a browser REST call with the same PAT.
  - NTLM: confirm domain\username and password; test with `curl --ntlm`.
- API version errors: adjust `AZDO_API_VERSION` (e.g., `6.0`, `7.0`).
- SSL/PKI issues: set `AZDO_VERIFY_SSL=false` for test environments or install your enterprise root CA.

**Development**

- Install: `poetry install`
- Run with logging: `set MCP_LOG_LEVEL=DEBUG` (Windows) then `poetry run azure-devops-mcp`
- Code layout:
  - `src/azure_devops_mcp/server.py`: MCP server entry and tool definitions
  - `src/azure_devops_mcp/ado_client.py`: minimal Azure DevOps REST client (PAT/NTLM)
  - `src/azure_devops_mcp/config.py`: environment configuration loader

**Locking & Reproducibility**

- Generate lock file: `poetry lock` (or use helpers `scripts/generate-lock.ps1` / `scripts/generate-lock.sh`)
- Commit `poetry.lock` for deterministic installs. The Dockerfile already copies `poetry.lock*` to leverage layer caching and reproducible dependency resolution.

**Security**

- Store PATs securely (OS keychain/secret manager). Avoid committing env values.
- Prefer PAT over NTLM for service integrations.

**License**

- Provided as‑is, no warranty. Use within your organization as appropriate.
