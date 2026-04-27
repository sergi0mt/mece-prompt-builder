# MECE Prompt Builder

A focused mini-app derived from McKinsey Deck Builder. It guides you through:

1. **Stage 1 — Define Problem**: central question, audience, decision context
2. **Stage 2 — MECE Structure**: 3 testable branches with evidence + so-what

…then formats everything as a markdown research brief ready to drop into [deepresearch](https://github.com/sergi0mt/deepresearch).

## Stack

- **Backend**: FastAPI + SQLite (async via `aiosqlite`)
- **Frontend**: Next.js 16 (App Router, React 19) + Tailwind v4 + shadcn/ui
- **LLM routing**: 2-tier via OpenRouter (DeepSeek v3.2 for fast, Gemini 2.5 Flash for balanced)
- **Web search**: Brave + Tavily with auto-fallback
- **PDF uploads**: PyMuPDF text extraction → fed into prompts as XML chunks

## Local development

```bash
# 1. Copy env template, fill in keys
cp .env.example .env
# edit .env: at minimum set OPENROUTER_API_KEY

# 2. Backend deps
pip install -r backend/requirements.txt

# 3. Frontend deps
cd frontend && npm install && cd ..

# 4. Run both servers (Windows)
start.bat
```

Backend: http://localhost:8000  ·  Frontend: http://localhost:3000

## Workflow

1. From `/v2`, click **New engagement** → pick a template (Strategic Assessment, Due Diligence, etc.)
2. Chat through Stage 1 (the AI asks for central question + decision)
3. AI auto-generates the MECE structure in Stage 2 (toggle Web Search for live evidence)
4. Click **Research Prompt** → review the markdown, copy, paste into deepresearch

## Deployment

See `railway.toml` and `frontend/railway.toml` for Railway. Two services, one shared Volume on the backend at `/data`.

## Differences vs McKinsey Deck Builder

- No Stage 3 (Storyline) or Stage 4 (Deck generation)
- No PowerPoint / DOCX / PDF export
- No `mckinsey_pptx` library
- Adds: `/v2/engagements/[id]/research-handoff` page + `GET /api/v1/projects/{id}/handoff`
