# Product Requirements Document: MCP Document Generation & OneDrive Upload Server

**Version:** 1.0
**Date:** 2025-10-13
**Status:** Draft

---

## 1. Executive Summary

### 1.1 Overview
A Model Context Protocol (MCP) server that enables users to generate Microsoft Office documents (Word, PowerPoint, Excel) from conversational AI interactions via LibreChat and automatically upload them to their Microsoft OneDrive accounts.

### 1.2 Objectives
- Provide seamless document generation from LLM outputs (markdown/JSON)
- Enable secure, multi-user OneDrive integration with OAuth authentication
- Deploy as a containerized service supporting up to 100 concurrent users
- Integrate natively with LibreChat's MCP framework

### 1.3 Technology Stack
- **Language:** Python 3.11+
- **MCP Framework:** fastmcp (Python) - See [AGENTS.md](AGENTS.md) for development guidelines
- **Document Libraries:** python-docx, python-pptx, openpyxl
- **Authentication:** MSAL (Microsoft Authentication Library)
- **Deployment:** Docker, hosted via Portainer with Cloudflare tunnel exposure
- **MCP Client:** LibreChat with native MCP OAuth support - See [LIBRECHAT_MCP.md](LIBRECHAT_MCP.md)

---

## 2. User Stories & Use Cases

### 2.1 Primary User Stories

**US-1: Generate Word Document**
> As a LibreChat user, I want to ask the AI to create a Word document from our conversation so that I can download professionally formatted reports.

**US-2: Create PowerPoint Presentation**
> As a user, I want to generate a PowerPoint presentation from outlined content so that I can quickly create slide decks for meetings.

**US-3: Generate Excel Spreadsheet**
> As a user, I want to create Excel files with data tables and calculations so that I can work with structured data from AI outputs.

**US-4: Auto-upload to OneDrive**
> As a user, I want generated documents automatically saved to my OneDrive so that I can access them across devices without manual downloads.

**US-5: OAuth Authentication**
> As a user, I want to securely connect my Microsoft account once so that the server can access my OneDrive without storing my password.

### 2.2 Example Use Cases

**Use Case 1: Meeting Report Generation**
```
User: "Create a meeting report document with the key decisions we discussed and upload it to my OneDrive"
AI: [Generates structured content]
Server: Creates formatted DOCX → Uploads to OneDrive/Documents → Returns file link
```

**Use Case 2: Data Analysis Presentation**
```
User: "Turn this data analysis into a 10-slide presentation"
AI: [Generates slide content with titles, bullets, and data]
Server: Creates PPTX with formatted slides → Uploads to OneDrive → Returns link
```

**Use Case 3: Budget Spreadsheet**
```
User: "Create an Excel budget template with these categories and formulas"
AI: [Generates structured data and formulas]
Server: Creates XLSX with formatted tables → Uploads to OneDrive → Returns link
```

---

## 3. Functional Requirements

### 3.1 Document Generation

#### 3.1.1 Word Documents (.docx)
**Priority:** P0 (Must Have)

**Requirements:**
- **FR-1.1:** Accept markdown or JSON input from LLM
- **FR-1.2:** Support standard formatting:
  - Headings (H1-H6)
  - Paragraphs with bold, italic, underline
  - Bulleted and numbered lists
  - Tables
  - Images (base64 or URL)
- **FR-1.3:** Support document metadata (title, author, date)
- **FR-1.4:** Handle documents up to 50 pages
- **FR-1.5:** Typical processing time: 2-3 pages in <3 seconds

#### 3.1.2 PowerPoint Presentations (.pptx)
**Priority:** P0 (Must Have)

**Requirements:**
- **FR-2.1:** Accept structured JSON/markdown for slide content
- **FR-2.2:** Support slide layouts:
  - Title slide
  - Title + content (bullets)
  - Title + two columns
  - Title + table
  - Title + image
- **FR-2.3:** Support text formatting in slides
- **FR-2.4:** Handle presentations up to 50 slides
- **FR-2.5:** Support basic themes/colors

#### 3.1.3 Excel Spreadsheets (.xlsx)
**Priority:** P0 (Must Have)

**Requirements:**
- **FR-3.1:** Accept JSON/CSV-like data structures
- **FR-3.2:** Support features:
  - Multiple worksheets
  - Cell formatting (bold, colors, borders)
  - Basic formulas (SUM, AVERAGE, etc.)
  - Column width auto-sizing
  - Headers/footers
- **FR-3.3:** Handle workbooks up to 10,000 rows
- **FR-3.4:** Support data types (text, numbers, dates, currency)

### 3.2 OneDrive Integration

#### 3.2.1 File Upload
**Priority:** P0 (Must Have)

**Requirements:**
- **FR-4.1:** Upload generated files to user's OneDrive
- **FR-4.2:** Support custom folder paths (default: /Documents/LibreChat/)
- **FR-4.3:** Handle filename conflicts (append timestamp or increment)
- **FR-4.4:** Return shareable OneDrive link after upload
- **FR-4.5:** Support files up to 100MB

#### 3.2.2 Folder Management
**Priority:** P1 (Should Have)

**Requirements:**
- **FR-5.1:** Create folders if they don't exist
- **FR-5.2:** List user's OneDrive folders (for path selection)
- **FR-5.3:** Support nested folder structures

### 3.3 Authentication & Authorization

#### 3.3.1 Microsoft OAuth 2.0
**Priority:** P0 (Must Have)

**Requirements:**
- **FR-6.1:** Integrate with LibreChat's native MCP OAuth support
- **FR-6.2:** Request minimal required scopes:
  - `Files.ReadWrite` (OneDrive access)
  - `User.Read` (user identification)
- **FR-6.3:** Support token refresh automatically
- **FR-6.4:** Handle token expiration gracefully
- **FR-6.5:** Secure token storage (encrypted at rest)

#### 3.3.2 Multi-User Support
**Priority:** P0 (Must Have)

**Requirements:**
- **FR-7.1:** Isolate user sessions and tokens
- **FR-7.2:** Support up to 100 concurrent authenticated users
- **FR-7.3:** Associate generated documents with correct user accounts
- **FR-7.4:** Prevent cross-user data access

### 3.4 MCP Server Implementation

#### 3.4.1 MCP Tools/Resources
**Priority:** P0 (Must Have)

**Requirements:**
- **FR-8.1:** Expose MCP tools:
  - `create_word_document`
  - `create_powerpoint_presentation`
  - `create_excel_spreadsheet`
  - `upload_to_onedrive`
  - `list_onedrive_folders` (optional)
- **FR-8.2:** Clear tool descriptions and parameter schemas
- **FR-8.3:** Return structured responses with file URLs
- **FR-8.4:** Support tool chaining (generate → upload)

#### 3.4.2 Error Handling
**Priority:** P0 (Must Have)

**Requirements:**
- **FR-9.1:** Return user-friendly error messages
- **FR-9.2:** Handle authentication failures gracefully
- **FR-9.3:** Validate input before processing
- **FR-9.4:** Log errors for debugging (without exposing sensitive data)

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR-1:** Document generation: <5 seconds for typical documents (2-3 pages)
- **NFR-2:** OneDrive upload: <10 seconds for files <10MB
- **NFR-3:** Support 100 concurrent users without degradation
- **NFR-4:** API response time: <500ms for non-generation operations

### 4.2 Scalability
- **NFR-5:** Horizontally scalable (multiple container instances)
- **NFR-6:** Stateless design (tokens stored externally, not in memory)
- **NFR-7:** Handle peak loads of 50 simultaneous document generations

### 4.3 Security
- **NFR-8:** All OAuth tokens encrypted at rest
- **NFR-9:** No logging of sensitive user data
- **NFR-10:** HTTPS/TLS for all external communications
- **NFR-11:** Implement rate limiting per user (prevent abuse)
- **NFR-12:** Comply with Microsoft API usage policies

### 4.4 Reliability
- **NFR-13:** 99.5% uptime target
- **NFR-14:** Graceful degradation on OneDrive API failures
- **NFR-15:** Retry logic for transient failures (with exponential backoff)
- **NFR-16:** Health check endpoint for monitoring

### 4.5 Maintainability
- **NFR-17:** Comprehensive logging (info, warning, error levels)
- **NFR-18:** Clear code documentation and inline comments
- **NFR-19:** Unit test coverage >70%
- **NFR-20:** Docker image optimized for fast rebuilds

### 4.6 Compatibility
- **NFR-21:** Compatible with LibreChat's MCP implementation
- **NFR-22:** Support LibreChat's OAuth flow
- **NFR-23:** Generated documents compatible with Microsoft Office 2016+
- **NFR-24:** Generated documents compatible with LibreOffice 7+

---

## 5. Technical Architecture

**Reference Documents:**
- FastMCP patterns: [AGENTS.md](AGENTS.md)
- LibreChat integration: [LIBRECHAT_MCP.md](LIBRECHAT_MCP.md)

### 5.1 High-Level Components

```
┌─────────────────┐
│   LibreChat     │ (MCP Client with OAuth support)
│   + LLM         │ See: LIBRECHAT_MCP.md
└────────┬────────┘
         │ MCP Protocol (Streamable HTTP)
         │ (OAuth tokens passed per-user)
         ▼
┌─────────────────────────────────┐
│   MCP Document Server (Python)  │
│  ┌──────────────────────────┐   │
│  │  FastMCP Framework       │   │ See: AGENTS.md
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  Document Generators     │   │
│  │  - python-docx           │   │
│  │  - python-pptx           │   │
│  │  - openpyxl              │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  OneDrive Client (MSAL)  │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  Token Store (encrypted) │   │
│  └──────────────────────────┘   │
└────────┬────────────────────────┘
         │ Microsoft Graph API
         ▼
┌─────────────────┐
│ Microsoft       │
│ OneDrive        │
└─────────────────┘
```

### 5.2 Data Flow

**Document Creation Flow:**
1. User sends natural language request via LibreChat
2. LLM generates structured content (markdown/JSON)
3. LibreChat invokes MCP tool with user's OAuth token
4. MCP server validates token and generates document
5. Server uploads to OneDrive via Microsoft Graph API
6. Server returns OneDrive link to LibreChat
7. User receives link in chat interface

### 5.3 Authentication Flow

**See [LIBRECHAT_MCP.md](LIBRECHAT_MCP.md#oauth-authentication) for complete OAuth implementation details.**

LibreChat's native MCP OAuth flow:
1. User initiates OAuth via LibreChat MCP interface (click authentication indicator)
2. LibreChat opens OAuth provider (Microsoft) in browser with PKCE
3. User authorizes application
4. OAuth callback returns to LibreChat
5. LibreChat securely stores encrypted tokens per-user
6. LibreChat passes user-specific token with each MCP request
7. MCP server receives token via headers (e.g., `Authorization: {{PAT_TOKEN}}`)
8. Server validates and uses token for OneDrive API calls
9. LibreChat automatically refreshes tokens when refresh tokens available

**Key Implementation Points:**
- Use **Streamable HTTP transport** (production requirement per LIBRECHAT_MCP.md)
- Support **Client Discovery** for automatic client registration
- Implement **refresh token handling** for seamless re-authentication
- Use `customUserVars` for user-provided credentials if needed
- Set `initTimeout: 150000` (150s) for OAuth flows

---

## 6. MCP Tool Specifications

### 6.1 Tool: `create_word_document`

**Description:** Generate a Word document from markdown or structured JSON content.

**Parameters:**
```json
{
  "content": {
    "type": "string",
    "description": "Markdown or JSON string containing document content",
    "required": true
  },
  "format": {
    "type": "string",
    "enum": ["markdown", "json"],
    "description": "Input format",
    "default": "markdown"
  },
  "filename": {
    "type": "string",
    "description": "Desired filename (without extension)",
    "required": false
  },
  "upload_to_onedrive": {
    "type": "boolean",
    "description": "Whether to upload to OneDrive after creation",
    "default": true
  },
  "onedrive_path": {
    "type": "string",
    "description": "OneDrive folder path (e.g., '/Documents/Reports')",
    "default": "/Documents/LibreChat"
  }
}
```

**Returns:**
```json
{
  "success": true,
  "filename": "meeting_report_20251013_143022.docx",
  "onedrive_url": "https://onedrive.live.com/...",
  "file_size_bytes": 45632,
  "message": "Document created and uploaded successfully"
}
```

### 6.2 Tool: `create_powerpoint_presentation`

**Description:** Generate a PowerPoint presentation from structured slide content.

**Parameters:**
```json
{
  "slides": {
    "type": "array",
    "description": "Array of slide objects with title, content, layout",
    "required": true
  },
  "theme": {
    "type": "string",
    "enum": ["default", "blue", "professional", "minimal"],
    "default": "default"
  },
  "filename": {
    "type": "string",
    "description": "Desired filename (without extension)",
    "required": false
  },
  "upload_to_onedrive": {
    "type": "boolean",
    "default": true
  },
  "onedrive_path": {
    "type": "string",
    "default": "/Documents/LibreChat"
  }
}
```

**Returns:**
```json
{
  "success": true,
  "filename": "quarterly_review_20251013.pptx",
  "onedrive_url": "https://onedrive.live.com/...",
  "slide_count": 12,
  "file_size_bytes": 2456789,
  "message": "Presentation created and uploaded successfully"
}
```

### 6.3 Tool: `create_excel_spreadsheet`

**Description:** Generate an Excel spreadsheet from tabular data.

**Parameters:**
```json
{
  "sheets": {
    "type": "array",
    "description": "Array of worksheet objects with name and data",
    "required": true
  },
  "filename": {
    "type": "string",
    "description": "Desired filename (without extension)",
    "required": false
  },
  "include_formulas": {
    "type": "boolean",
    "description": "Whether to process formula strings",
    "default": true
  },
  "upload_to_onedrive": {
    "type": "boolean",
    "default": true
  },
  "onedrive_path": {
    "type": "string",
    "default": "/Documents/LibreChat"
  }
}
```

**Returns:**
```json
{
  "success": true,
  "filename": "budget_2025_20251013.xlsx",
  "onedrive_url": "https://onedrive.live.com/...",
  "sheet_count": 3,
  "total_rows": 247,
  "file_size_bytes": 89234,
  "message": "Spreadsheet created and uploaded successfully"
}
```

### 6.4 Tool: `list_onedrive_folders`

**Description:** List available folders in user's OneDrive (for path selection).

**Parameters:**
```json
{
  "parent_path": {
    "type": "string",
    "description": "Parent folder path to list (empty for root)",
    "default": "/"
  },
  "max_depth": {
    "type": "integer",
    "description": "Maximum folder depth to traverse",
    "default": 2
  }
}
```

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
  "message": "Retrieved 5 folders"
}
```

---

## 7. Development Phases

### Phase 1: Foundation (MVP)
**Goal:** Basic document generation and local testing

**Prerequisites:**
- Review [AGENTS.md](AGENTS.md) for FastMCP development workflow
- Set up development environment: `uv sync`
- Understand testing patterns (in-memory transport)

**Deliverables:**
- FastMCP server skeleton (Streamable HTTP transport)
- Word document generation from markdown
- Basic MCP tool implementations
- Docker containerization
- Local testing without OneDrive
- Tests passing: `uv run pytest`

**Timeline:** 1-2 weeks

### Phase 2: OneDrive Integration
**Goal:** Add Microsoft authentication and upload

**Prerequisites:**
- Review [LIBRECHAT_MCP.md](LIBRECHAT_MCP.md) OAuth sections thoroughly
- Understand LibreChat's user-specific connection patterns
- Prepare Microsoft Azure App Registration

**Deliverables:**
- MSAL OAuth implementation following LibreChat patterns
- OneDrive upload functionality via Microsoft Graph API
- Token storage and refresh logic (encrypted at rest)
- LibreChat OAuth integration with Client Discovery
- Multi-user session handling with `{{LIBRECHAT_USER_ID}}` placeholders
- `customUserVars` configuration for optional user credentials
- Pre-commit hooks passing: `uv run pre-commit run --all-files`

**Timeline:** 1-2 weeks

### Phase 3: Full Office Suite Support
**Goal:** Complete PowerPoint and Excel support

**Deliverables:**
- PowerPoint generation from structured data
- Excel generation with formulas
- Enhanced formatting options
- Comprehensive error handling

**Timeline:** 1-2 weeks

### Phase 4: Production Hardening
**Goal:** Deploy to production environment

**Deliverables:**
- Performance optimization
- Comprehensive testing (unit + integration)
- Security audit
- Monitoring and logging
- Cloudflare tunnel configuration
- Documentation (user + technical)

**Timeline:** 1 week

---

## 8. Deployment & Operations

### 8.1 Docker Configuration

**Base Image:** `python:3.11-slim`

**Environment Variables:**
```bash
# Microsoft App Registration
MICROSOFT_CLIENT_ID=<azure_app_client_id>
MICROSOFT_CLIENT_SECRET=<azure_app_secret>
MICROSOFT_TENANT_ID=<tenant_id_or_common>
MICROSOFT_REDIRECT_URI=<librechat_callback_url>

# MCP Server Configuration
MCP_SERVER_PORT=3000
MCP_SERVER_HOST=0.0.0.0

# Storage
TOKEN_ENCRYPTION_KEY=<generated_encryption_key>
TOKEN_STORAGE_PATH=/data/tokens

# Logging
LOG_LEVEL=INFO
LOG_FILE=/logs/mcp_server.log

# OneDrive Defaults
DEFAULT_ONEDRIVE_PATH=/Documents/LibreChat
```

**Volume Mounts:**
- `/data` - Persistent token storage
- `/logs` - Application logs

### 8.2 Cloudflare Tunnel Configuration

**Expose:** `http://mcp-document-server:3000`
**Access Policy:** Require authentication (if needed)

### 8.3 Monitoring

**Health Check Endpoint:** `GET /health`
```json
{
  "status": "healthy",
  "uptime_seconds": 345678,
  "active_sessions": 23,
  "version": "1.0.0"
}
```

**Metrics to Track:**
- Request rate (requests/minute)
- Document generation time (p50, p95, p99)
- OneDrive upload success rate
- Token refresh failures
- Error rate by type

---

## 9. Security Considerations

### 9.1 Threat Model

**Threats:**
1. Unauthorized access to user OneDrive accounts
2. Token theft or leakage
3. Cross-user data exposure
4. API abuse/DoS
5. Malicious document content injection

**Mitigations:**
1. OAuth 2.0 with minimal scopes
2. Encrypted token storage, no tokens in logs
3. Strict session isolation, user ID validation
4. Rate limiting per user/IP
5. Input sanitization and validation

### 9.2 Compliance

- **GDPR:** User tokens are encrypted, deletable on request
- **Microsoft API Terms:** Respect rate limits, proper attribution
- **Data Retention:** Tokens stored only while user session active (with refresh capability)

---

## 10. Testing Strategy

### 10.1 Unit Tests
- Document generation functions (each format)
- Input parsing and validation
- Error handling paths
- Token encryption/decryption

### 10.2 Integration Tests
- End-to-end MCP tool invocations
- OneDrive API interactions (with mock API)
- OAuth flow simulation
- Multi-user scenarios

### 10.3 Load Testing
- 50 concurrent document generations
- Token refresh under load
- Memory usage over time

### 10.4 Security Testing
- Token isolation between users
- Input injection attempts
- Authentication bypass attempts

---

## 11. Success Metrics

### 11.1 Launch Criteria
- [ ] All P0 functional requirements implemented
- [ ] Unit test coverage >70%
- [ ] Successfully handles 50 concurrent users
- [ ] OAuth flow working with LibreChat
- [ ] All three document types generating correctly
- [ ] OneDrive uploads succeeding >95% of the time
- [ ] Documentation complete (README, API docs)

### 11.2 Post-Launch KPIs
- **Usage:** Daily active users, documents generated per day
- **Performance:** Average generation time, upload success rate
- **Reliability:** Error rate, uptime percentage
- **User Satisfaction:** Feedback from LibreChat users

---

## 12. Future Enhancements (Out of Scope for V1)

### 12.1 P2 Features (Nice to Have)
- PDF export option
- Document templates library
- Advanced Excel features (charts, pivot tables)
- PowerPoint animations and transitions
- Batch document generation
- Document version history in OneDrive

### 12.2 P3 Features (Future Consideration)
- Support for Google Drive integration
- Real-time collaborative editing
- AI-powered document suggestions
- Custom branding/themes
- Export to other formats (Markdown, HTML, LaTeX)
- Integration with other MCP servers

---

## 13. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Microsoft API rate limits hit | High | Medium | Implement caching, request queuing, user quotas |
| Token refresh failures | High | Low | Robust retry logic, clear user messaging |
| LibreChat OAuth integration issues | High | Medium | Early testing with LibreChat team, fallback auth |
| Document generation performance | Medium | Low | Async processing, progress indicators |
| Storage costs for tokens | Low | Low | Regular cleanup, token expiration policies |

---

## 14. Dependencies & Assumptions

### 14.1 External Dependencies
- LibreChat MCP OAuth implementation (must be working)
- Microsoft Azure App Registration (client ID/secret)
- Microsoft Graph API availability
- Python libraries: fastmcp, python-docx, python-pptx, openpyxl, msal

### 14.2 Assumptions
- Users have Microsoft accounts with OneDrive
- LibreChat provides OAuth tokens in MCP requests
- Network connectivity to Microsoft Graph API
- Docker host has sufficient resources (2GB RAM, 2 CPU cores minimum)
- Users accept automatic file uploads to OneDrive

---

## 15. Glossary

- **MCP:** Model Context Protocol - standard for AI-to-tool communication
- **FastMCP:** Python framework for building MCP servers
- **LibreChat:** Open-source ChatGPT clone with MCP support
- **MSAL:** Microsoft Authentication Library
- **OAuth 2.0:** Industry-standard authorization protocol
- **Microsoft Graph API:** RESTful API for Microsoft 365 services
- **OneDrive:** Microsoft's cloud storage service

---

## 16. Appendices

### 16.1 Microsoft App Registration Requirements

**Required API Permissions:**
- `Files.ReadWrite` (Delegated)
- `User.Read` (Delegated)

**Redirect URIs:**
- Add LibreChat's OAuth callback URL

**Authentication:**
- Enable public client flows: No (use authorization code flow)
- Supported account types: Multitenant or single tenant

### 16.2 Sample Input/Output Formats

**Example Markdown Input (Word):**
```markdown
# Quarterly Report

## Executive Summary
This quarter showed strong growth...

## Key Metrics
- Revenue: $1.2M
- Growth: 25%

## Next Steps
1. Expand team
2. Launch new product
```

**Example JSON Input (PowerPoint):**
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
    }
  ]
}
```

**Example JSON Input (Excel):**
```json
{
  "sheets": [
    {
      "name": "Budget",
      "headers": ["Category", "Q1", "Q2", "Q3", "Q4", "Total"],
      "data": [
        ["Marketing", 10000, 12000, 15000, 18000, "=SUM(B2:E2)"],
        ["Engineering", 50000, 52000, 54000, 56000, "=SUM(B3:E3)"]
      ]
    }
  ]
}
```

---

## 17. Approval & Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| Technical Lead | | | |
| Security Review | | | |

---

---

## 18. Development References

This project includes comprehensive development guidelines and integration documentation:

### FastMCP Development Guidelines ([AGENTS.md](AGENTS.md))
- **Required workflow:** `uv sync → pre-commit → pytest` before commits
- **Repository structure:** Understanding of `src/fastmcp/` organization
- **Testing standards:** In-memory transport patterns, inline snapshots
- **Code standards:** Python ≥3.10 with full type annotations
- **Key for LLM agents:** Comprehensive patterns for building MCP servers

### LibreChat MCP Integration ([LIBRECHAT_MCP.md](LIBRECHAT_MCP.md))
- **Native MCP support:** How LibreChat exposes MCP servers in chat and agents
- **OAuth authentication:** Required reading for implementing user authentication
- **User-specific connections:** Multi-user patterns and isolation
- **Dynamic user context:** Available placeholders (`{{LIBRECHAT_USER_ID}}`, etc.)
- **Configuration patterns:** `librechat.yaml` structure for MCP servers
- **Transport requirements:** Streamable HTTP transport for production (critical!)

**IMPORTANT:** All developers and LLM agents working on this project should:
1. Review [AGENTS.md](AGENTS.md) before writing any FastMCP code
2. Reference [LIBRECHAT_MCP.md](LIBRECHAT_MCP.md) when implementing OAuth and multi-user features
3. Follow the development workflow: `uv sync`, `uv run pre-commit run --all-files`, `uv run pytest`

---

## Quick Start for Developers

**Before writing any code:**

1. **Read the development guidelines:**
   ```bash
   # FastMCP patterns and workflow
   cat AGENTS.md

   # LibreChat MCP integration requirements
   cat LIBRECHAT_MCP.md
   ```

2. **Set up your environment:**
   ```bash
   uv sync
   uv run pre-commit install
   ```

3. **Key takeaways:**
   - Use **Streamable HTTP transport** (not STDIO or SSE for production)
   - Follow **FastMCP testing patterns** (in-memory transport for tests)
   - Implement **LibreChat OAuth flow** with Client Discovery
   - Support **multi-user isolation** with user context placeholders
   - Run **validation workflow** before every commit: `uv sync → pre-commit → pytest`

4. **Start coding:**
   - Begin with Phase 1 (basic document generation)
   - Reference example servers in fastmcp repo
   - Write tests alongside implementation (atomic, self-contained)
   - Keep commits focused and messages brief

---

**Document Control**
- **Last Updated:** 2025-10-13
- **Next Review:** After Phase 1 completion
- **Change Log:**
  - V1.0 - Initial draft
  - V1.1 - Added references to AGENTS.md and LIBRECHAT_MCP.md throughout document
