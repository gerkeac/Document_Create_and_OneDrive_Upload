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

**Current Phase:** Phase 3 - Full Office Suite Support - Complete ✅

**Phase 1 Complete (✅):**
- ✅ Word document generation from markdown and JSON
- ✅ MCP server with FastMCP framework
- ✅ Health check endpoint
- ✅ Structured logging system
- ✅ Docker containerization
- ✅ Comprehensive test suite

**Phase 2 Complete (✅):**
- ✅ Microsoft OAuth token extraction from LibreChat headers
- ✅ OneDrive file upload via Microsoft Graph API
- ✅ Multi-user support with user-specific authentication
- ✅ OneDrive folder listing
- ✅ Automated folder creation
- 🚧 End-to-end testing with LibreChat (requires Azure setup)

**Phase 3 Complete (✅):**
- ✅ PowerPoint presentation generation (python-pptx)
- ✅ Excel spreadsheet generation (openpyxl)
- ✅ Multiple slide layouts (title, content, table, two-column, blank)
- ✅ Excel formulas and formatting support
- ✅ OneDrive integration for all document types
- ✅ Comprehensive test suite (60% coverage, 65/65 tests passing)

**Coming Next (Phase 4):**
- Production hardening
- Performance optimization
- Security audit
- Deployment to production

See [TASK_TRACKER.md](TASK_TRACKER.md) for detailed progress tracking.

## Documentation

- [Product Requirements Document (PRD)](PRD.md) - Complete project specification
- [Task Tracker](TASK_TRACKER.md) - Development progress and task breakdown
- [Deployment Guide](DEPLOYMENT.md) - Docker, Portainer, and production deployment
- [Azure Setup Guide](AZURE_SETUP.md) - OAuth and Azure App Registration
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

### 4. Run the Server

**Option A: Development Mode**
```bash
# Run directly with uv
uv run python -m mcp_document_server.server
```

**Option B: Docker (Recommended for Production)**
```bash
# Build and start the container
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

**Option C: Portainer Deployment**

For Portainer deployment, see the complete [Deployment Guide](DEPLOYMENT.md).

Quick summary:
1. Push your code to a git repository (already includes `uv.lock`)
2. In Portainer: **Stacks** → **Add Stack** → **Repository** method
3. Enter your git URL and set compose path to `docker-compose.yml`
4. Deploy - Portainer builds and deploys automatically!

**Testing the Server:**
```bash
# The server will expose MCP tools on port 3000
# You can test it by integrating with LibreChat (Phase 2)
# or using the FastMCP client in tests
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
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Docker Compose setup
└── .env.example               # Environment configuration template
```

## MCP Tools

### ✅ `health_check` (Implemented)
Check the health and status of the MCP Document Generator server.

**Parameters:** None

**Returns:**
```json
{
  "status": "healthy",
  "uptime_seconds": 3456,
  "version": "0.1.0",
  "phase": "Phase 1 - MVP",
  "temp_directory": "/tmp/mcp_documents",
  "temp_directory_accessible": true,
  "cached_files": 5
}
```

### ✅ `create_word_document` (Implemented - Phase 1 & 2)
Generate Word documents from markdown or JSON content, with optional OneDrive upload.

**Parameters:**
- `content` (string, required): Markdown or JSON string containing document content
- `format` (string, optional): Input format - "markdown" or "json" (default: "markdown")
- `filename` (string, optional): Desired filename without extension (auto-generated if not provided)
- `upload_to_onedrive` (boolean, optional): Whether to upload to OneDrive (default: false, requires OAuth)
- `onedrive_path` (string, optional): OneDrive folder path (default: "/Documents/LibreChat")
- `title` (string, optional): Document title for metadata
- `author` (string, optional): Document author for metadata

**Returns (without OneDrive upload):**
```json
{
  "success": true,
  "filename": "document_20251013_143022.docx",
  "local_path": "/tmp/mcp_documents/document_20251013_143022.docx",
  "file_size_bytes": 45632,
  "message": "Document created successfully"
}
```

**Returns (with OneDrive upload):**
```json
{
  "success": true,
  "filename": "document_20251013_143022.docx",
  "local_path": "/tmp/mcp_documents/document_20251013_143022.docx",
  "file_size_bytes": 45632,
  "onedrive_url": "https://onedrive.live.com/...",
  "onedrive_file_id": "01ABCDEF...",
  "onedrive_filename": "document_20251013_143022.docx",
  "message": "Document created and uploaded to OneDrive successfully"
}
```

**Supported Markdown Features:**
- Headings (H1-H6)
- Paragraphs with inline formatting (bold, italic, bold+italic)
- Bulleted lists
- Numbered lists
- Tables
- Document metadata

**Authentication Requirements:**
- OneDrive upload requires OAuth authentication via LibreChat
- See [Azure Setup Guide](AZURE_SETUP.md) for configuration

### ✅ `create_powerpoint_presentation` (Implemented - Phase 3)
Create PowerPoint presentations from structured slide data with multiple layouts and OneDrive upload support.

**Parameters:**
- `slides` (array, required): List of slide objects with layout, title, and content
- `filename` (string, optional): Desired filename without extension (auto-generated if not provided)
- `theme` (string, optional): Theme name - "default", "blue", "professional", "minimal" (default: "default")
- `upload_to_onedrive` (boolean, optional): Whether to upload to OneDrive (default: false, requires OAuth)
- `onedrive_path` (string, optional): OneDrive folder path (default: "/Documents/LibreChat")

**Supported Slide Layouts:**
- `title`: Title slide with title and subtitle
- `title_content`: Title + bulleted content
- `title_two_columns`: Title with left and right columns
- `title_table`: Title with table data
- `blank`: Blank slide with custom content

**Example Slide Data:**
```json
{
  "slides": [
    {
      "layout": "title",
      "title": "Q4 2025 Review",
      "subtitle": "Team Performance"
    },
    {
      "layout": "title_content",
      "title": "Key Achievements",
      "content": [
        "Launched 3 new features",
        "Increased user base by 40%",
        "Improved response time by 60%"
      ]
    },
    {
      "layout": "title_table",
      "title": "Q4 Results",
      "table": {
        "headers": ["Month", "Revenue", "Growth"],
        "rows": [
          ["October", "$100K", "10%"],
          ["November", "$120K", "20%"],
          ["December", "$150K", "25%"]
        ]
      }
    }
  ]
}
```

**Returns:**
```json
{
  "success": true,
  "filename": "presentation_20251013_143022.pptx",
  "local_path": "/tmp/mcp_documents/presentation_20251013_143022.pptx",
  "slide_count": 3,
  "file_size_bytes": 125632,
  "onedrive_url": "https://onedrive.live.com/...",
  "message": "Presentation created and uploaded to OneDrive successfully"
}
```

### ✅ `create_excel_spreadsheet` (Implemented - Phase 3)
Build Excel spreadsheets with data, formulas, formatting, and OneDrive upload support.

**Parameters:**
- `sheets` (array, required): List of worksheet objects with name, headers, and data
- `filename` (string, optional): Desired filename without extension (auto-generated if not provided)
- `include_formulas` (boolean, optional): Whether to process formula strings starting with "=" (default: true)
- `upload_to_onedrive` (boolean, optional): Whether to upload to OneDrive (default: false, requires OAuth)
- `onedrive_path` (string, optional): OneDrive folder path (default: "/Documents/LibreChat")

**Features:**
- Multiple worksheets per file
- Header row with bold styling and fill color
- Alternating row colors for readability
- Auto-sized columns
- Frozen header row
- Excel formulas (SUM, AVERAGE, etc.)
- Cell borders and formatting
- Number formatting (integers, decimals, currency)

**Example Sheet Data:**
```json
{
  "sheets": [
    {
      "name": "Budget",
      "headers": ["Category", "Q1", "Q2", "Q3", "Q4", "Total"],
      "data": [
        ["Marketing", 10000, 12000, 15000, 18000, "=SUM(B2:E2)"],
        ["Engineering", 50000, 52000, 54000, 56000, "=SUM(B3:E3)"],
        ["Total", "=SUM(B2:B3)", "=SUM(C2:C3)", "=SUM(D2:D3)", "=SUM(E2:E3)", "=SUM(F2:F3)"]
      ]
    }
  ]
}
```

**Returns:**
```json
{
  "success": true,
  "filename": "spreadsheet_20251013_143022.xlsx",
  "local_path": "/tmp/mcp_documents/spreadsheet_20251013_143022.xlsx",
  "sheet_count": 1,
  "total_rows": 3,
  "file_size_bytes": 89234,
  "onedrive_url": "https://onedrive.live.com/...",
  "message": "Spreadsheet created and uploaded to OneDrive successfully"
}
```

### ✅ `list_onedrive_folders` (Implemented - Phase 2)
List available folders in user's OneDrive for path selection.

**Parameters:**
- `parent_path` (string, optional): Parent folder path to list (default: "/")
- `max_depth` (integer, optional): Maximum folder depth to traverse (default: 2)

**Returns:**
```json
{
  "success": true,
  "folders": [
    "/Documents",
    "/Documents/Reports",
    "/Documents/LibreChat",
    "/Pictures",
    "/Projects"
  ],
  "parent_path": "/",
  "folder_count": 5,
  "message": "Retrieved 5 folders from OneDrive"
}
```

**Authentication Requirements:**
- Requires OAuth authentication via LibreChat
- See [Azure Setup Guide](AZURE_SETUP.md) for configuration

## LibreChat Configuration (Phase 2 - Ready for Testing)

**Prerequisites:**
1. Complete Azure App Registration setup (see [AZURE_SETUP.md](AZURE_SETUP.md))
2. Start the MCP Document Generator server (see instructions above)
3. Configure LibreChat to connect to the MCP server

Add to your `librechat.yaml`:

```yaml
mcpServers:
  document-generator:
    type: streamable-http
    url: "http://mcp-document-server:3000"  # Adjust for your deployment
    initTimeout: 150000  # 150 seconds for OAuth flow
    oauth:
      provider: "microsoft"
      clientId: "${MICROSOFT_CLIENT_ID}"
      clientSecret: "${MICROSOFT_CLIENT_SECRET}"
      authorizationUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
      tokenUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/token"
      scope: "Files.ReadWrite User.Read offline_access"
    headers:
      Authorization: "Bearer {{OAUTH_ACCESS_TOKEN}}"  # LibreChat passes token
      X-User-ID: "{{LIBRECHAT_USER_ID}}"  # User identification
    serverInstructions: true
```

**Configuration Notes:**
- `type: streamable-http` - Required for production (not STDIO or SSE)
- `initTimeout: 150000` - Allows time for user OAuth authentication
- `headers.Authorization` - LibreChat automatically passes OAuth access token
- `headers.X-User-ID` - User isolation for multi-user support
- `scope: offline_access` - Enables refresh tokens for long-lived sessions

**URL Options:**
- Local development: `http://localhost:3000`
- Docker Compose: `http://mcp-document-server:3000`
- Production: Your Cloudflare tunnel URL or direct server URL

**Testing the Integration:**
1. Start your MCP server and LibreChat
2. In LibreChat, look for the MCP Settings panel or status indicator
3. You should see "OAuth Required" for the `document-generator` server
4. Click authenticate and complete the Microsoft login flow
5. Once authenticated, status should show "Connected"
6. Test by asking: "Create a Word document and upload it to my OneDrive"

See [AZURE_SETUP.md](AZURE_SETUP.md) for detailed setup and troubleshooting.

## Azure App Registration Setup

For complete step-by-step instructions, see [AZURE_SETUP.md](AZURE_SETUP.md).

**Quick Setup:**
1. Go to [Azure Portal](https://portal.azure.com) → "App registrations" → "New registration"
2. Configure application:
   - **Name:** LibreChat Document Generator
   - **Supported account types:** Multitenant (or single tenant)
   - **Redirect URI:** Add your LibreChat OAuth callback URL
3. Add **API permissions:**
   - `Files.ReadWrite` (Delegated)
   - `User.Read` (Delegated)
   - `offline_access` (Delegated - for refresh tokens)
4. Create **client secret** under "Certificates & secrets"
5. Copy credentials to LibreChat's environment configuration

**Important:** The MCP server receives OAuth tokens from LibreChat via HTTP headers.
You don't need to configure credentials in the MCP server's `.env` file.

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

**Version:** 0.2.0 (Phase 2 - OneDrive Integration - In Progress)
**Last Updated:** 2025-10-13

**Phase 2 Status:**
- ✅ Core OneDrive integration complete
- ✅ OAuth token extraction from LibreChat
- ✅ Multi-user support implemented
- 🚧 End-to-end testing with LibreChat (requires Azure setup)
