# MCP Document Generator Server

An MCP (Model Context Protocol) server that generates Microsoft Office documents (Word, PowerPoint, Excel) from LLM outputs and uploads them to Microsoft OneDrive.

## Features

- 📝 **Word Documents**: Generate `.docx` files from markdown or JSON
- 📊 **PowerPoint Presentations**: Create `.pptx` slide decks from structured content
- 📈 **Excel Spreadsheets**: Build `.xlsx` files with data, formulas, and formatting
- ☁️ **OneDrive Integration**: Automatic upload to user's OneDrive with OAuth authentication
- 🔐 **Multi-User Support**: Secure, isolated sessions for up to 100 concurrent users
- 🔄 **LibreChat Integration**: Native MCP support with OAuth flow

## Project Status

**Current Phase:** Phase 0 - Setup & Planning

See [TASK_TRACKER.md](TASK_TRACKER.md) for detailed progress tracking.

## Documentation

- [Product Requirements Document (PRD)](PRD.md) - Complete project specification
- [Task Tracker](TASK_TRACKER.md) - Development progress and task breakdown
- [FastMCP Development Guidelines](AGENTS.md) - Required reading for developers
- [LibreChat MCP Integration](LIBRECHAT_MCP.md) - OAuth and multi-user patterns

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Microsoft Azure App Registration (for OneDrive integration)
- LibreChat instance with MCP support

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd Document_Create_and_OneDrive_Upload

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your Azure App credentials
nano .env
```

### 3. Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run pre-commit checks
uv run pre-commit run --all-files
```

### 4. Run the Server (Coming in Phase 1)

```bash
# Development mode
uv run python -m mcp_document_server.server

# Production mode (Docker)
docker-compose up --build
```

## Development Workflow

Before every commit, ensure:

1. **Sync dependencies:** `uv sync`
2. **Run pre-commit hooks:** `uv run pre-commit run --all-files`
3. **Run tests:** `uv run pytest`

See [AGENTS.md](AGENTS.md) for detailed development guidelines.

## Project Structure

```
.
├── src/mcp_document_server/
│   ├── server.py              # Main MCP server
│   ├── generators/            # Document generation modules
│   │   ├── word_generator.py
│   │   ├── powerpoint_generator.py
│   │   └── excel_generator.py
│   ├── onedrive/              # OneDrive integration
│   │   ├── client.py
│   │   └── auth.py
│   └── utils/                 # Utility functions
├── tests/                     # Test suite
├── docs/                      # Additional documentation
├── pyproject.toml             # Project configuration
├── Dockerfile                 # Docker configuration (coming soon)
└── docker-compose.yml         # Docker Compose setup (coming soon)
```

## MCP Tools (Planned)

### `create_word_document`
Generate Word documents from markdown or JSON content.

### `create_powerpoint_presentation`
Create PowerPoint presentations from structured slide data.

### `create_excel_spreadsheet`
Build Excel spreadsheets with data and formulas.

### `list_onedrive_folders`
List available folders in user's OneDrive.

## LibreChat Configuration (Coming in Phase 2)

Add to your `librechat.yaml`:

```yaml
mcpServers:
  document-generator:
    url: "http://mcp-document-server:3000"
    transport: "streamableHttp"
    oauth:
      provider: "microsoft"
      clientId: "${MICROSOFT_CLIENT_ID}"
      clientSecret: "${MICROSOFT_CLIENT_SECRET}"
      authorizationUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
      tokenUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/token"
      scope: "Files.ReadWrite User.Read offline_access"
```

## Azure App Registration Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to "App registrations" → "New registration"
3. Configure:
   - **Name:** LibreChat Document Generator
   - **Supported account types:** Multitenant
   - **Redirect URI:** Add your LibreChat callback URL
4. Under "API permissions," add:
   - `Files.ReadWrite` (Delegated)
   - `User.Read` (Delegated)
5. Under "Certificates & secrets," create a new client secret
6. Copy Client ID, Tenant ID, and Client Secret to `.env`

## Contributing

1. Review [AGENTS.md](AGENTS.md) for coding standards
2. Create a feature branch
3. Make changes with tests
4. Run validation: `uv sync && uv run pre-commit run --all-files && uv run pytest`
5. Submit pull request

## License

[Your License Here]

## Support

For issues, questions, or contributions, please see [TASK_TRACKER.md](TASK_TRACKER.md) or open an issue.

---

**Version:** 0.1.0 (Phase 0 - Setup)
**Last Updated:** 2025-10-13
