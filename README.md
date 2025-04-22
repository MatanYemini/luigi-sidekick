# AI‑Ready Dev Container & Repo Assistant

This project ships a **Docker‑based developer environment** coupled with a small **FastAPI server** that can:

1. **Clone any public Git repository** into a local `repos/` directory (`POST /repos/clone`).
2. **Query that repository with OpenAI Codex CLI** in _full‑auto_ mode (`POST /codex`).

It's designed as a lightweight, reproducible sandbox for experimenting with Codex CLI against arbitrary codebases.

---

## Stack Overview

- **Dockerfile** – Ubuntu 22 with:
  - Git, build‑essentials
  - Node 22 (LTS) + npm (global prefix set to `/usr/local`)
  - Python 3 + `fastapi` + `uvicorn[standard]`
  - `@openai/codex` CLI installed globally (`npm i -g @openai/codex`)
  - Claude Code CLI (`@anthropic-ai/claude-code`)
- **docker‑compose.yml**
  - `dev` – interactive shell for hacking
  - `api` – runs the FastAPI service on port `8000`
  - `mcp-atlassian` - runs the MCP server for Atlassian tools on port `9000`
- **FastAPI app** (`app/main.py`)
  - `/repos/clone` – clones a repo URL to `repos/<n>`
  - `/codex` – runs Codex CLI in that repo
  - `/claude-code` - runs Claude Code CLI in that repo
  - `/jira/issue` - fetches Jira issue information
  - `/jira/execute` - analyzes Jira issues with Claude Code
  - `/luigi-init` - generates repository analysis documents

## Backend Architecture

### Project Structure

```
app/
├── config.py           # Configuration settings and constants
├── main.py             # FastAPI application entrypoint
├── models/             # Pydantic data models
│   ├── ai_models.py    # Models for AI code generation requests
│   ├── jira_models.py  # Models for Jira API integration
│   └── repo_models.py  # Models for repository operations
├── routes/             # API route handlers
│   ├── codetools.py    # AI code generation endpoints (Codex & Claude)
│   ├── jira.py         # Jira integration endpoints
│   └── repo.py         # Repository management endpoints
└── utils/              # Utility functions
    ├── claude.py       # Claude Code API integration
    ├── claude_utils.py # Helper functions for Claude integration
    ├── jira.py         # Jira API integration
    ├── jira_utils.py   # Helper functions for Jira integration
    └── utils.py        # General utility functions
```

### Key Components

#### 1. API Routes

The backend is organized into three main route modules:

- **repo.py**: Manages repository operations
  - `/repos/clone` - Clones external Git repositories into the local `repos/` directory
- **codetools.py**: Handles AI code generation
  - `/codex` - Runs OpenAI Codex in full-auto mode against a repository
  - `/claude-code` - Runs Claude Code in non-interactive mode against a repository
  - `/luigi-init` - Generates repository analysis documents using Claude Code
- **jira.py**: Provides Jira integration
  - `/jira/issue` - Fetches information about a Jira issue
  - `/jira/execute` - Analyzes a Jira issue using Claude Code and returns suggestions

#### 2. Data Models

The application uses Pydantic models for request/response validation:

- **ai_models.py**: Models for AI code generation
  - `CodexRequest` - Parameters for Codex queries (repo name, query)
  - `ClaudeCodeRequest` - Parameters for Claude Code queries
  - `LuigiRequest` - Parameters for repository analysis generation
- **jira_models.py**: Models for Jira integration
  - `JiraIssueRequest` - Parameters for Jira issue fetching
  - `JiraExecuteRequest` - Parameters for Jira issue analysis
  - `JiraIssueResponse` - Response format for issue information
  - `JiraExecuteResponse` - Response format for issue analysis
- **repo_models.py**: Models for repository operations
  - `RepoRequest` - Parameters for repository cloning (URL)

#### 3. Utility Modules

The application includes several utility modules:

- **utils.py**: General utility functions
  - `get_repo_path` - Gets the absolute path to a repository
  - `check_repo_exists` - Verifies a repository exists and returns its path
- **jira.py/jira_utils.py**: Jira integration utilities
  - `fetch_jira_issue` - Fetches issue information from Jira API
  - `extract_text_from_description` - Parses Atlassian Document Format
  - `check_affected_repositories` - Identifies repository information in Jira tickets
  - `extract_programming_info` - Extracts programming-relevant information from Jira issues
- **claude.py/claude_utils.py**: Claude Code integration utilities
  - `execute_with_claude` - Executes Claude Code CLI with Jira ticket information

## Integration with External Services

### MCP Atlassian Integration

This project includes the [MCP Atlassian](https://github.com/sooperset/mcp-atlassian) server that provides Model Context Protocol support for Atlassian tools:

- **Confluence** - Create, read, update, and search Confluence pages and spaces
- **Jira** - Work with Jira issues, projects, sprints, and more

#### Key Features

- Access Confluence spaces with `confluence://{space_key}`
- Access Jira projects with `jira://{project_key}`
- Search content, manage pages, create issues, and more
- SSE transport interface on port 9000

To use the MCP Atlassian server:

1. Create a `.env` file based on the `.env.example` template
2. Add your Atlassian credentials (API tokens, URLs, etc.)
3. The MCP service is accessible at `http://localhost:9000/sse` from your host machine

### Jira REST API Integration

The backend integrates directly with the Jira REST API for fetching issue details and implementing solutions:

- **Issue Retrieval**: Fetches complete issue data including custom fields
- **Content Parsing**: Processes Atlassian Document Format (ADF) content
- **Claude Integration**: Passes issue information to Claude Code for implementation

#### Authentication

Jira API integration requires the following environment variables:

- `JIRA_BASE_URL` - Your Jira instance URL
- `JIRA_EMAIL` - User email for authentication
- `JIRA_API_TOKEN` - API token from Atlassian account settings

### Claude Code Integration

The backend integrates with Claude Code CLI for:

- **Code analysis** - Analyzes repositories and generates documentation
- **Issue implementation** - Implements solutions for Jira tickets
- **Repository exploration** - Navigates codebases to understand their structure

Claude Code is run in non-interactive mode and is allowed to use specific tools (Edit, Bash, Search, etc.) to interact with repositories.

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
curl -X POST http://localhost:8000/repos/clone \
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

### POST `/repos/clone`

Clone a Git repo into `repos/`. Automatically detects if it's GitHub or Bitbucket based on the URL.

#### Request

The API is now simplified - you only need to provide the repository URL:

```json
{
  "url": "https://github.com/user/repo.git"
}
```

OR

```json
{
  "url": "https://bitbucket.org/workspace/repo.git"
}
```

For Bitbucket repositories, authentication is handled automatically using environment variables:

```env
# Preferred authentication method for Bitbucket repositories
BITBUCKET_USERNAME=your_username
BITBUCKET_APP_PASSWORD=your_app_password

# Fallback method (only used if username/app_password not provided)
BITBUCKET_TOKEN=your_repository_access_token
```

When username and app password are provided, the system will automatically convert your URL:

```
From: https://bitbucket.org/YOURREPO/YOURREPONAME.git
To:   https://username:app_password@bitbucket.org/YOURREPO/YOURREPONAME.git
```

The system will automatically:

1. Detect if the URL is from Bitbucket
2. Apply the appropriate credentials from environment variables
3. Prioritize username + app password authentication over Repository Access Token

#### Response

```json
{
  "status": "success",
  "path": "/workspace/repos/repo",
  "repo_name": "repo",
  "repo_type": "bitbucket" // or "github/other"
}
```

### POST `/codex`

Run OpenAI Codex CLI in the specified repo.

| Field   | Type   | Description                                        |
| ------- | ------ | -------------------------------------------------- |
| `repo`  | string | Folder name inside `repos/` (from `/repos/clone`). |
| `query` | string | Natural‑language prompt for Codex.                 |

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

| Field  | Type   | Description                                                                                                        |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------ |
| `repo` | string | (Optional) Folder name inside `repos/` (from `/repos/clone`). If not provided, all repositories will be processed. |

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

## Running the Backend

### Local Development

To run the backend locally for development:

1. Clone the repository and navigate to the project directory
2. Set up environment variables in a `.env` file
3. Start the services using Docker Compose

```bash
# Build and start the API service
OPENAI_API_KEY=<your-key> docker compose up --build api

# Build and start all services (API and MCP-Atlassian)
OPENAI_API_KEY=<your-key> docker compose up --build
```

The API will be available at http://localhost:8000 with auto-reload enabled for development.

### Interactive Development Shell

For development and debugging, you can run an interactive shell with all tools installed:

```bash
# Start an interactive shell
docker compose run --rm dev

# Inside container
node -v              # Check Node.js version
codex -h             # View Codex CLI help
claude -h            # View Claude Code CLI help
python -m app.main   # Run the FastAPI app directly
```

### Environment Variables

The backend requires several environment variables to function properly:

- **OPENAI_API_KEY**: Required for Codex functionality
- **CLAUDE_API_KEY**: Required for Claude Code functionality
- **BITBUCKET_USERNAME**: Username for Bitbucket App Password authentication
- **BITBUCKET_APP_PASSWORD**: App Password for Bitbucket authentication
- **BITBUCKET_TOKEN**: Repository Access Token for Bitbucket authentication
- **JIRA_BASE_URL**: URL to your Jira instance (e.g., https://your-domain.atlassian.net)
- **JIRA_EMAIL**: Email address for Jira authentication
- **JIRA_API_TOKEN**: API token for Jira authentication

You can set these in a `.env` file or pass them directly to Docker Compose.

## API Workflow Examples

### Repository Analysis Workflow

1. Clone a repository:

   ```bash
   curl -X POST http://localhost:8000/repos/clone \
     -H 'Content-Type: application/json' \
     -d '{"url": "https://github.com/example/repo.git"}'
   ```

2. Generate a repository analysis document:
   ```bash
   curl -X POST http://localhost:8000/luigi-init \
     -H 'Content-Type: application/json' \
     -d '{"repo": "repo"}'
   ```

### Jira Integration Workflow

1. Fetch a Jira issue:

   ```bash
   curl -X POST http://localhost:8000/jira/issue \
     -H 'Content-Type: application/json' \
     -d '{"issueId": "PROJECT-123"}'
   ```

2. Analyze and implement a solution for the issue:
   ```bash
   curl -X POST http://localhost:8000/jira/execute \
     -H 'Content-Type: application/json' \
     -d '{"issueId": "PROJECT-123", "repository": "repo"}'
   ```

## Tips & Notes

- **Approval mode** – We use `--approval-mode full-auto` to let Codex apply edits & run commands by itself within the container. Adjust as needed (`suggest`, `auto-edit`).
- **Timeouts** – The `/codex` and `/claude-code` endpoints time out after 5 minutes; the `/jira/execute` endpoint times out after 10 minutes. Tweak these in their respective modules if your queries take longer.
- **Private repos** – You can configure SSH keys or PATs in the container for private clones (left as an exercise).
- **Persistent globals** – `docker-compose.yml` mounts a `npm_global` volume so globally installed Node packages persist between rebuilds.
- **Error handling** – All endpoints include appropriate error handling with HTTP status codes and detailed error messages.
- **FastAPI auto‑reload** – Enabled for development (`--reload` flag), so code changes take effect immediately.

---

## Troubleshooting

### Common Issues

#### API Connection Issues

- **Symptom**: Unable to connect to the API at http://localhost:8000
- **Solution**: Ensure Docker Compose is running and check logs with `docker compose logs api`

#### Jira API Issues

- **Symptom**: Errors when trying to fetch Jira issues (HTTP 502 or 504)
- **Solution**: Verify your Jira credentials in the `.env` file and ensure network connectivity

#### Claude Code or Codex Timeout

- **Symptom**: Requests to `/codex`, `/claude-code`, or `/jira/execute` time out
- **Solution**: For complex repositories or queries, increase the timeout in the respective endpoint handlers

### Logs and Debugging

- View API logs with `docker compose logs api`
- View MCP Atlassian logs with `docker compose logs mcp-atlassian`
- For more detailed debugging, use the interactive shell:
  ```bash
  docker compose run --rm dev
  ```

## Security Considerations

- The API has no authentication by default - it should be deployed behind a secure gateway in production
- API keys for Jira, OpenAI, and Claude are stored in environment variables - secure these appropriately
- Repository data is stored locally in the `repos/` directory - ensure appropriate filesystem permissions

## Roadmap / Ideas

- Add authentication and rate-limiting to the API endpoints
- Implement WebSocket streaming for real-time output from Claude Code and Codex
- Support incremental repository updates (pull instead of fresh clone)
- Add more advanced Jira ticket analysis and classification features
- Implement a web interface for repository analysis and visualization
- Add support for more AI models and tools beyond Codex and Claude Code
- Enhance error handling and retry mechanisms for API integrations

Pull requests welcome – happy hacking! 🚀
