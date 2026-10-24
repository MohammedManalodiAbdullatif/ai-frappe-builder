# AI Frappe App Builder

An end-to-end AI-powered system that turns client business requirements into installable Frappe/ERPNext applications with real DocTypes, Workflows, Server/Client Scripts, Reports, Dashboards, and Live Desk Previews.

---

## Architecture Overview

```
Client Description / Chat
         ↓
FastAPI AI Frappe Engine (ai_frappe_builder/)
  ├── planner.py            ← LLM reasoning, schema design & discovery questions
  ├── validator.py          ← 12 deterministic validation rules
  ├── script_generator.py   ← Generates Frappe server/client scripts from 7 battle-tested snippet patterns
  ├── report_builder.py     ← Builds Reports, Number Cards & Dashboards
  ├── frappe_client.py      ← Async Frappe REST API client (Token Auth)
  ├── applier.py            ← Materializes DocTypes, Workflows, Scripts, Reports & sample data
  ├── run_tests.py          ← Automated verification tests on created DocTypes
  └── exporter.py           ← Exports standalone installable Frappe app to disk & git
         ↓
Frappe / ERPNext Remote Server (Live Desk forms rendered in iframe)
         ↓
Modern Web UI (frontend/)
  ├── Chat Pane with interactive discovery questions
  ├── Real-time Frappe desk form preview
  ├── App Spec JSON inspector
  ├── Live build checklist
  └── One-click export to Git repo
```

---

## Quick Start

### 1. Configure Backend Environment
```bash
cd ai_frappe_builder
cp .env.example .env
```
Edit `.env` and fill in:
```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
FRAPPE_URL=https://your-site.frappe.cloud
FRAPPE_API_KEY=your_frappe_api_key
FRAPPE_API_SECRET=your_frappe_api_secret
DATABASE_URL=sqlite+aiosqlite:///./ai_frappe.db
```

### 2. Start Backend Service
```bash
cd ai_frappe_builder
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API documentation: `http://localhost:8000/docs`

### 3. Start Frontend UI
```bash
cd frontend
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/build` | **One-shot endpoint**: Describe → Plan → Validate → Apply → Preview URLs |
| `POST` | `/chat/start` | Start discovery chat session |
| `POST` | `/chat/message` | Send answer / follow-up instructions |
| `GET` | `/plan/{session_id}` | Retrieve generated App Spec JSON and validation result |
| `POST` | `/apply/{session_id}` | Re-trigger apply for failed/partial sessions |
| `POST` | `/export/{session_id}` | Export app as real Frappe repository with git commit |
| `GET` | `/sessions` | List all build sessions |
| `GET` | `/sessions/{session_id}` | Get session details & chat history |
