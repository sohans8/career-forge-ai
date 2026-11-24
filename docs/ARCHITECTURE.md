# Career Forge AI: Architecture

## Overview

Career Forge AI is a React single-page app (Netlify, with a GitHub Pages mirror on the `gh-pages` branch) talking to a FastAPI service (Render). The backend keeps all reference data as files in `backend/data/` and loads them into memory on first use. There is no database. A weekly GitHub Actions job keeps the education data current through reviewed pull requests.

Live: frontend https://career-forge-ai-yprq.netlify.app/ (mirror: https://sohans8.github.io/career-forge-ai/), API https://career-copilot-api-lw76.onrender.com (docs at `/docs`, health at `/api/v1/health`).

```
┌──────────────────────────── Browser (React 18 + Vite + Tailwind) ────────────────────────────┐
│  OnboardingWizard → StudentDashboard   RoadmapPage (React Flow)   MentorPage / MentorWidget  │
│  ResumePage   v1 views (assessment, streams, careers)                                        │
│  ProfileContext (localStorage: profile, guidance, resume score, checklist, explored nodes)   │
│  MentorContext  (chat history, widget state, pending roadmap node)                           │
│                                   services/api.js (Axios, 60 s timeout)                      │
└───────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                │ HTTPS / JSON, multipart for resume upload
┌───────────────────────────────────────────────▼──────────────────────────────────────────────┐
│ FastAPI (backend/app/main.py): CORS from CORS_ORIGINS, ValueError → 400, unhandled → 500     │
│                                                                                              │
│  routes/platform.py                                        routes/recommendation.py (v1)     │
│   /api/roadmaps   → roadmap_service ──┐                     /api/v1/recommend                │
│   /api/colleges   → college_service   │                       → recommendation_service       │
│   /api/guidance   → guidance_service ─┤ (O*NET careers,         (rule engine + LogReg)       │
│   /api/mentor     → mentor_service ───┤  roadmap nodes)          → data_service (v1 CSVs)    │
│                       ├─ rag_service  (TF-IDF over rag_policies/)                            │
│                       └─ llm_service  (Gemini | Groq | OpenAI, optional)                     │
│   /api/resume     → resume_service ─── llm_service (optional enrichment)                     │
│   /api/status     → counts from all services                                                 │
└───────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                │ file reads
┌───────────────────────────────────────────────▼──────────────────────────────────────────────┐
│ backend/data/                                                                                │
│  roadmaps_india.json   aicte_colleges.json   onet_skills.json   job_skills_ats.csv           │
│  rag_policies/*.md|pdf   schemas/roadmaps.schema.json   rag_index/ (generated, git-ignored)  │
│  staged_patches/ and watcher_state.json (written by the watcher)   raw/ (v1 CSV catalogue)   │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Data layer

The platform uses five datasets. `backend/scripts/fetch_datasets.py` builds each one, trying local raw source files first, then a remote source, then a built-in seed. The app therefore starts even on a fresh clone with no network. The raw sources (O*NET CSVs, AICTE dumps, job posts, AISHE files) are large and git-ignored. Only the compact derived files are committed.

| Dataset | Shape | Used by |
|---|---|---|
| `roadmaps_india.json` | `{schema_version, last_updated, stages, nodes[]}`. 37 nodes. Each node has `id`, `stage`, `kind`, `title`, `summary`, `duration`, `eligibility`, `entrance_exams`, `top_branches_or_roles`, `next_nodes`, `avg_salary_range`, `streams`, `college_type`, `branch_keywords`, `official_links`, `last_updated` | roadmap, guidance, mentor |
| `aicte_colleges.json` | about 7,900 institutions: name, state, district, ownership, kinds (engineering 2,959, diploma 3,585, management 3,465), branches per kind, intake. No pharmacy entries, because PCI rather than AICTE approves pharmacy colleges | college |
| `onet_skills.json` | 923 occupations with a 6-value RIASEC vector, top-3 code, top skills, hot technologies | guidance |
| `job_skills_ats.csv` | `role, skill, weight, source` rows for 16 roles | resume |
| `rag_policies/` | Markdown and PDF policy documents | rag |

`backend/scripts/validate_data.py` checks the roadmap against `schemas/roadmaps.schema.json` plus integrity rules that a JSON schema cannot express (unique IDs, `next_nodes` pointing at existing nodes, one root per stage), and checks that the college, O*NET and job-skill files exist, are non-empty and have the expected fields or header. It exits with code 1 on any problem and runs in CI before and after every sync.

## Services

- **roadmap_service.** Loads the graph and returns `{root, nodes, edges, last_updated}` for a stage. Edges come from `next_nodes`. A target that belongs to another stage is returned with `external: true`, so the UI can draw it dashed and jump to that stage on click. The `stream` filter keeps the root and the nodes whose `streams` tags match the selected stream. Invalid stages raise `ValueError`, which the app returns as 400.
- **college_service.** In-memory filtering over the compact AICTE list by state, kind, branch substring, district, ownership and name, with `limit` and `offset` paging.
- **guidance_service.** Serves the onboarding quiz and turns answers into a dashboard: the top 6 O*NET careers by a weighted score (45% fit with the student's top three RIASEC letters, 20% overlap with chosen strengths, 20% career-goal keyword match in the title, 15% fit with the stream), the most common skill gaps across those careers, a mapped resume target role, and the first three roadmap steps for the stage and stream.
- **rag_service.** Reads `.md`, `.txt` and `.pdf` files from `rag_policies/`, splits them into overlapping chunks and fits a scikit-learn TF-IDF index. The index is cached with joblib in `rag_index/` and rebuilt automatically when the file list, sizes or modification times change.
- **llm_service.** One `chat` / `chat_json` interface over the Gemini API and the OpenAI-compatible APIs of Groq and OpenAI. `chat_json` asks for a JSON object and parses the reply defensively. `LLM_PROVIDER=auto` picks the first provider with a key. When no key is set, `available` is false and callers use their offline path.
- **mentor_service.** Builds the prompt from the student profile, the selected roadmap node (if any), the last 8 turns of history and the top 4 RAG chunks, then calls the LLM. If the provider fails, it returns the offline answer with a note. Without an LLM it composes an answer from the node details and the retrieved chunks, says that it is in offline mode, and lists sources. The response is always `{reply, sources, llm_used, provider}`.
- **resume_service.** Extracts text from PDF (pypdf) or DOCX (python-docx), detects sections, matches role skills with word-boundary regexes and synonyms, and scores four parts: keywords, impact (action verbs and metrics in bullets), formatting and completeness. It returns per-section feedback, rule-based bullet rewrites and a learning checklist of missing skills with free resources and mini projects. With an LLM it replaces the rewrites and adds a summary, keeping the rule-based score.
- **recommendation_service (v1).** The original Class 10 stream recommender: rule score (40% skills, 40% interests, 20% subjects) blended with a calibrated Logistic Regression over 240 binary features. The blend weights move toward the rules when input is sparse, and each result carries a confidence status. Training and evaluation code is in `backend/ml/`.

## Request flows

**Roadmap node to mentor.**

1. `RoadmapPage` calls `GET /api/roadmaps?stage=&stream=` and lays the graph out left to right by breadth-first depth from the stage root.
2. Clicking a node opens the drawer. The drawer calls `GET /api/colleges` using the node's `college_type` and first `branch_keywords` entry for the chosen state.
3. "Ask AI Mentor about this path" calls `MentorContext.askAboutNode`. This pre-fills the question, remembers the node ID and opens the widget.
4. Sending posts `{message, history, profile, node_id}` to `/api/mentor/chat`. `mentor_service` loads the node, retrieves RAG chunks and answers with an LLM or offline.

**Resume analysis.** `ResumePage` posts multipart `file` and `target_role` to `/api/resume/analyze`. The route rejects anything other than `.pdf` or `.docx` (400), files over `MAX_UPLOAD_MB` (413) and unreadable files or unknown roles (422). The score and checklist are stored in `ProfileContext` and shown on the dashboard.

**Onboarding.** `OnboardingWizard` loads `/api/guidance/quiz` and falls back to `data/quizFallback.js` when the API is waking up. It then posts the answers to `/api/guidance/recommend` and stores the result in `ProfileContext`.

## Auto-sync pipeline

`.github/workflows/auto_sync_education.yml` runs every Monday at 03:30 UTC and on manual dispatch:

```
validate_data ─► update_education_data ─► validate_data ─► pytest ─► pull request (bot/education-sync)
```

`backend/scripts/update_education_data.py`:

1. **Watch.** Fetch AICTE, UGC, NTA, Maharashtra CET Cell and MoE notice pages and the latest roadmap.sh commit. Compare content hashes against `watcher_state.json` and continue only with pages that changed.
2. **Collect.** Download up to 5 new PDFs per run, 25 MB each at most, and only over HTTPS from an allow-list of official domains (`aicte-india.org`, `ugc.gov.in`, `nta.ac.in`, `education.gov.in`, `mahacet.org`, `gov.in`, `nic.in` and others). Files go into `rag_policies/`.
3. **Extract.** With an LLM configured, ask for JSON patches against `roadmaps_india.json`. Fetched text is untrusted input. Patches must be `update` operations on existing nodes, may only change the fields in `EDITABLE_FIELDS`, and must keep a trial copy of the graph valid. Anything else is dropped.
4. **Stage.** Write surviving patches to `staged_patches/` with status `pending`.
5. **Reindex.** Rebuild the RAG index.
6. **Apply (manual).** After review, a maintainer sets `"status": "approved"` and runs `--apply <file>`. Apply refuses unapproved patches, re-validates each patch and the full graph, writes a dated `.bak` backup, updates `last_updated` on the graph and the changed nodes, and marks the file `applied`.

No change reaches `roadmaps_india.json` without a human approving it in a pull request.

## Configuration and security

- Settings are read from environment variables, `backend/.env` or a root `.env` (`backend/app/config.py`). `.env.example` lists them. `.env` files are git-ignored.
- `/api/status` reports which LLM provider is configured but never returns keys.
- Request bodies are bounded with Pydantic: message length, history length, profile field lengths and college `limit` from 1 to 100. Stage values are a fixed `Literal`.
- Uploads are capped at `MAX_UPLOAD_MB` by reading at most limit + 1 bytes.
- `CORS_ORIGINS` defaults to `*` without credentials. To restrict it, set it to `https://sohans8.github.io`.

## Testing

`python -m pytest backend/tests -q` runs 44 tests with FastAPI's `TestClient`. LLM calls are monkeypatched, so the tests need no network or keys. One test queries colleges for every roadmap node that has a `college_type`, the same way the drawer does, so a node pointing at an empty or wrong college category fails CI.

`.github/workflows/ci.yml` runs on every push and pull request. The backend job validates the datasets, runs the tests, starts uvicorn and calls `/api/v1/health`, `/api/roadmaps` and `/api/status`. The frontend job runs `npm ci` and `npm run build`. The same backend suite also runs inside the auto-sync workflow after each data refresh.

## Deployment

| Part | Host | Build | Run |
|---|---|---|---|
| Frontend | Netlify (`netlify.toml`, Node 20), redeploys on push | `npm run build` in `frontend/` | static `dist/`, SPA redirect to `index.html` |
| Frontend mirror | GitHub Pages (`gh-pages` branch) | `npx vite build --base=/career-forge-ai/` in `frontend/` | static files, `404.html` copy of `index.html` |
| Backend | Render free tier (`render.yaml`, Python 3.11.9 from `.python-version`) | `pip install -r backend/requirements.txt` | `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`, health check `/api/v1/health` |

The derived datasets are committed, so no data fetch happens at deploy time. The RAG index is built on the first mentor request after a deploy. Render's free tier sleeps when idle, so the first request can take 30 to 60 seconds.
