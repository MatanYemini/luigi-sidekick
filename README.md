# AI‑Ready Dev Container & Repo Assistant

This project ships a **Docker‑based developer environment** coupled with a small **FastAPI server** that can:

1. **Clone any public Git repository** into a local `repos/` directory (`POST /clone`).
2. **Query that repository with OpenAI Codex CLI** in _full‑auto_ mode (`POST /codex`).

It's designed as a lightweight, reproducible sandbox for experimenting with Codex CLI against arbitrary codebases.

---

## Stack Overview

- **Dockerfile** – Ubuntu 22 with:
  - Git, build‑essentials
  - Node 22 (LTS) + npm (global prefix set to `/usr/local`)
  - Python 3 + `fastapi` + `uvicorn[standard]`
  - `@openai/codex` CLI installed globally (`npm i -g @openai/codex`)
- **docker‑compose.yml**
  - `dev` – interactive shell for hacking
  - `api` – runs the FastAPI service on port `8000`
  - `mcp-atlassian` - runs the MCP server for Atlassian tools on port `9000`
- **FastAPI app** (`app/main.py`)
  - `/clone` – clones a repo URL to `repos/<n>`
  - `/codex` – runs Codex CLI in that repo

## MCP Atlassian Integration

This project includes the [MCP Atlassian](https://github.com/sooperset/mcp-atlassian) server that provides Model Context Protocol support for Atlassian tools:

- **Confluence** - Create, read, update, and search Confluence pages and spaces
- **Jira** - Work with Jira issues, projects, sprints, and more

### Key Features

- Access Confluence spaces with `confluence://{space_key}`
- Access Jira projects with `jira://{project_key}`
- Search content, manage pages, create issues, and more
- SSE transport interface on port 9000

To use the MCP Atlassian server:

1. Create a `.env` file based on the `.env.example` template
2. Add your Atlassian credentials (API tokens, URLs, etc.)
3. The MCP service is accessible at `http://localhost:9000/sse` from your host machine

### Networking

All services are connected to a custom Docker network (`luigi-network`), which allows:

- Service-to-service communication using service names as hostnames
- The API service can access the MCP Atlassian server at `http://mcp-atlassian:9000/sse`
- The MCP Atlassian service can access the API service at `http://api:8000`
- Both services expose their ports to the host for external access

---

## Quick Start

### 1 — Prerequisites

- Docker & Docker Compose
- An OpenAI API key with access to Codex CLI models

### 2 — Build & Start

```bash
# Build images & start the API
OPENAI_API_KEY=<your‑key> docker compose up --build api
```

The API is now listening on http://localhost:8000.

### 3 — Clone a Repository

```bash
curl -X POST http://localhost:8000/clone \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://github.com/openai/gpt-2.git"}'
```

Response:

```json
{
  "status": "success",
  "path": "/workspace/repos/gpt-2"
}
```

### 4 — Ask Codex a Question

```bash
curl -X POST http://localhost:8000/codex \
  -H 'Content-Type: application/json' \
  -d '{"repo": "gpt-2", "query": "summarize the project structure"}'
```

The server will run:

```
codex -a full-auto "summarize the project structure"
```

inside `repos/gpt-2` and stream back Codex's stdout/stderr.

---

## API Reference

### POST `/clone`

Clone a Git repo into `repos/`.

| Field | Type         | Description              |
| ----- | ------------ | ------------------------ |
| `url` | string (URL) | Full Git repository URL. |

Response: `{ status: "success", path: "<filesystem‑path>" }`

### POST `/codex`

Run OpenAI Codex CLI in the specified repo.

| Field   | Type   | Description                                  |
| ------- | ------ | -------------------------------------------- |
| `repo`  | string | Folder name inside `repos/` (from `/clone`). |
| `query` | string | Natural‑language prompt for Codex.           |

Returns Codex stdout/stderr.

### POST `/jira/issue`

Fetches information about a Jira issue from the Jira REST API and checks if the "Affected Repositories" field is filled.

| Field      | Type   | Description                                                                                                                                    |
| ---------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `issueId`  | string | The Jira issue ID (e.g., PROJECT-123) - Optional, but either issueId or issueUrl must be provided                                              |
| `issueUrl` | string | URL to the Jira issue (e.g., https://your-domain.atlassian.net/browse/PROJECT-123) - Optional, but either issueId or issueUrl must be provided |

Response:

```json
{
  "issue_id": "PROJECT-123",
  "title": "Issue title",
  "details": "Issue description",
  "labels": ["bug", "priority-high"],
  "fields": {
    // All issue fields from Jira
  },
  "message": "Please fill 'Affected repositories'" // or "I have enough information to work on this ticket"
}
```

Status codes:

- 200: Success
- 400: Bad Request (missing both issueId and issueUrl, or invalid issueUrl)
- 404: Issue not found
- 502: Error connecting to Jira API
- 504: Request to Jira API timed out

Example usage:

```bash
# Using curl with issueId
curl -X POST http://localhost:8000/jira/issue \
  -H 'Content-Type: application/json' \
  -d '{"issueId": "PROJECT-123"}'

# Using curl with issueUrl
curl -X POST http://localhost:8000/jira/issue \
  -H 'Content-Type: application/json' \
  -d '{"issueUrl": "https://your-domain.atlassian.net/browse/PROJECT-123"}'

# Using the test script
python -m tests.test_jira_endpoint --id PROJECT-123
python -m tests.test_jira_endpoint --url https://your-domain.atlassian.net/browse/PROJECT-123
```

### POST `/luigi-init`

Ensures repositories have a luigi.md file with comprehensive code analysis. If the file doesn't exist, it creates one using Claude Code analysis.

| Field  | Type   | Description                                                                                                  |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------ |
| `repo` | string | (Optional) Folder name inside `repos/` (from `/clone`). If not provided, all repositories will be processed. |

Response when providing a specific repo:

- If file already exists: `{ status: "success", message: "luigi.md already exists", path: "<file-path>" }`
- If file created successfully: `{ status: "success", message: "luigi.md successfully created", path: "<file-path>" }`
- If file creation partially succeeded: `{ status: "partial_success", message: "Created template luigi.md file..." }`

Response when processing all repos:

```json
{
  "status": "success",
  "repos_processed": 3,
  "results": [
    {
      "repo": "repo1",
      "result": {
        "status": "success",
        "message": "luigi.md already exists",
        "path": "..."
      }
    },
    {
      "repo": "repo2",
      "result": {
        "status": "success",
        "message": "luigi.md successfully created",
        "path": "..."
      }
    },
    {
      "repo": "repo3",
      "result": { "status": "error", "message": "Repository not found" }
    }
  ]
}
```

---

## Tips & Notes

- **Approval mode** – We use `--approval-mode full-auto` to let Codex apply edits & run commands by itself within the container. Adjust as needed (`suggest`, `auto-edit`).
- **Timeout** – The `/codex` endpoint times out after 5 minutes; tweak in `app/main.py` if your queries take longer.
- **Private repos** – You can configure SSH keys or PATs in the container for private clones (left as an exercise).
- **Persistent globals** – `docker-compose.yml` mounts a `npm_global` volume so globally installed Node packages persist between rebuilds.

---

## Development & Debugging

```bash
# Interactive shell with all tools
docker compose run --rm dev

# Inside container
node -v  # v22.x
codex -h # see CLI help
```

FastAPI auto‑reload is enabled (`--reload` flag), so code changes take effect immediately.

---

## Roadmap / Ideas

- Expose additional Codex CLI flags (model selection, quiet mode).
- Add authentication / rate‑limiting to the API.
- Support incremental repo updates (pull instead of fresh clone).
- Stream Codex output back via WebSocket for real‑time UI.

Pull requests welcome – happy hacking! 🚀
