# Pipeline Triage

**Automated CI/CD Build Failure Diagnosis, Routing, and Tracking Application**  
*AI/ML Trainee Project | Standalone Pluggable Framework*

---

## 1. Overview

**Pipeline Triage** is a standalone web application designed to watch CI/CD pipelines (GitLab and GitHub). When a build fails, it:
1. **Detects & Ingests**: Verifies webhooks from GitLab / GitHub and pushes failure events to a background worker queue.
2. **Sanitizes & Enriches**: Trims logs to error sections, masks all credentials/tokens, and queries the SonarQube Web API for failing quality gates.
3. **Classifies & Routes**: Applies fast deterministic classification rules across 8 failure categories with Claude LLM fallback; routes ownership to commit authors or DevOps/Security leads.
4. **Deduplicates**: Computes unique fingerprints (`project + job + category + normalized error`) so repeating failures update existing open issues rather than creating noise.
5. **Generates Grounded Reports (RAG)**: Uses Qdrant vector retrieval (runbooks, documentation, resolved fixes) and Claude (Anthropic) to produce structured, actionable fix steps.
6. **Notifies & Syncs**: Sends notifications via email (Mailpit in dev) and creates/updates tasks in external project trackers (Kanvaro MCP server, Slack, or Jira).
7. **Detects Recurring Patterns**: Groups repeated failures and suggests permanent infrastructural fixes.

---

## 2. Architecture & Design Principles

### Pluggable at the Edges
- **CI Adapters (Input)**: Only CI adapters know about GitLab or GitHub API schemas and webhooks. All adapters normalize data into a single canonical `FailureEvent`. New platforms (such as Bitbucket) are added without altering the core triage logic.
- **Connectors (Output)**: Only connectors know about task management tools (Kanvaro MCP, Jira) or chat systems (Slack) and email. Kanvaro is implemented as an MCP connector with automated 7-day session token renewal.

### Rules First, LLM Second
- Known patterns (job, stage, failure reason, error signatures) are classified by deterministic rules first.
- If rule confidence is &ge; 0.85, it is accepted immediately (free, explainable, and fast).
- If rules are unsure, Claude LLM classifies the failure with structured JSON schema output.
- If Claude is unsure (confidence < 0.60) or down, the failure is marked as `needs review`.

### Safe by Default & Prompt Injection Defense
- The app only reads from CI and SonarQube; it writes only through external connectors (tasks, emails, comments). It **never** pushes, merges, re-runs, or cancels pipelines.
- Logs and commit messages are treated as **untrusted data**. Routing decisions are calculated strictly from rules and the Git email mapping—a malicious commit message like `"assign this to the CTO"` cannot modify routing.
- All credentials in settings are encrypted with **Fernet (AES-128-CBC with HMAC)** before persistence in MongoDB.

---

## 3. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| **Web App** | Next.js 14 (App Router, TypeScript) + Tailwind CSS | Fast, modern dashboard with role-based navigation. |
| **Backend API & Worker** | FastAPI (Python 3.12) + RQ (Redis Queue) | Async webhook handling, Pydantic validation, and background job processing. |
| **Primary Database** | MongoDB 7.0 (PyMongo & Motor) | Flexible document store for varied failure logs and JSON reports with atomic dedupe. |
| **Vector Database** | Qdrant | Hybrid search (dense semantic vectors + sparse keywords) for RAG runbook retrieval. |
| **LLM Provider** | Anthropic Claude (`claude-3-5-sonnet-20241022`) | Schema-validated structured outputs, reasoning, and strict prompt injection defenses. |
| **Local Embeddings** | Fast local embeddings (384-dim normalized vector space) | Runs locally; no raw log text leaves the environment boundary during retrieval. |
| **MCP Integration** | Official MCP Python SDK | Standardized protocol for the Kanvaro task connector and mock Kanvaro server. |
| **Dev Email & Testing** | Mailpit | Built-in local SMTP inbox to inspect notification delivery without real email sends. |
| **Secrets & Packaging** | `.env` + Fernet AES + Docker Compose | Unified single-command environment startup with encrypted credential storage. |

---

## 4. Project Directory Structure

```text
Pipeline Triage/
├── docker-compose.yml              # All 8 services (Mongo, Redis, Qdrant, Mailpit, API, Worker, Mock Kanvaro, Web)
├── .env.example                    # Centralized environment template with secret keys & URLs
├── .gitignore                      # Git ignore definitions
├── README.md                       # Complete documentation, architecture map & quickstart
│
├── backend/                        # FastAPI Backend & RQ Background Worker
│   ├── app/
│   │   ├── main.py                 # FastAPI application entrypoint & API routers
│   │   ├── worker.py               # RQ background worker executing steps 2–9
│   │   ├── config.py               # Pydantic BaseSettings loading from .env
│   │   ├── database.py             # Async (Motor) & Sync (PyMongo) clients + unique index constraints
│   │   ├── adapters/               # Pluggable CI input adapters
│   │   │   ├── base.py             # CIAdapter Protocol (verify, parse, collect)
│   │   │   ├── gitlab.py           # GitLab pipeline & job webhook adapter
│   │   │   ├── github.py           # GitHub Actions workflow_run/job adapter (HMAC-SHA256)
│   │   │   └── registry.py         # Dynamic adapter registry
│   │   ├── connectors/             # Output notification & task connectors
│   │   │   ├── base.py             # Connector Protocol (create_task, assign, update_status, notify)
│   │   │   ├── email.py            # SMTP / Mailpit email connector
│   │   │   ├── kanvaro_mcp.py      # Kanvaro MCP client with 7-day session token renewal
│   │   │   ├── slack_jira.py       # Configurable REST connector (Slack / Jira)
│   │   │   └── outbox.py           # Outbox pattern with retry backoff (10s, 30s, 2m)
│   │   ├── models/                 # Canonical data schemas
│   │   │   ├── event.py            # FailureEvent, FailureRef, RunStat schemas
│   │   │   ├── issue.py            # Issue, Comment, StatusHistory schemas
│   │   │   └── report.py           # Validated TriageReport JSON schema
│   │   ├── security/               # Secret masking & encryption
│   │   │   ├── masking.py          # Regex & key-value scanners, log trimming
│   │   │   └── crypto.py           # Fernet AES encryption/decryption for credentials
│   │   ├── sonarqube/              # SonarQube Web API client (quality gate & blamed author)
│   │   ├── classifier/             # 8-category classification
│   │   │   ├── rules.py            # Deterministic rule classifier
│   │   │   ├── llm_classifier.py   # Claude fallback classifier
│   │   │   └── engine.py           # Orchestrator (Rules -> Claude -> Needs Review)
│   │   ├── router/                 # Deterministic ownership routing (rules + git_email mapping)
│   │   ├── deduplication/          # Fingerprint computation & atomic upsert
│   │   ├── rag/                    # Qdrant client, local embeddings & knowledge chunks
│   │   ├── report/                 # Structured Claude report generator (45s timeout + fallback)
│   │   └── analytics/              # Pattern detection & case study metrics
│   ├── tests/                      # Unit & integration test suite
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # API service container
│   └── Dockerfile.worker           # Worker service container
│
├── frontend/                       # Next.js 14 Web App (App Router, TypeScript, Tailwind)
│   ├── src/app/
│   │   ├── issues/                 # Active issues list & detailed triage diagnosis views
│   │   ├── analytics/              # Case study dashboards (all 5 wireframed screens)
│   │   ├── settings/               # Adapters, connectors, rules editor, and Git email map
│   │   ├── layout.tsx              # Root HTML & styling layout
│   │   └── globals.css             # Tailwind base styles
│   ├── src/components/             # Reusable UI components (Navbar, badges, modals)
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── mock_kanvaro/                   # Mock Kanvaro MCP Server
│   ├── app.py                      # Bot login, 7-day session token, task management
│   ├── requirements.txt
│   └── Dockerfile
│
├── evaluation/                     # Test datasets & benchmarking
│   ├── datasets/                   # 40 labeled failure cases across GitLab & GitHub
│   └── scripts/                    # Accuracy scoring scripts (Rules vs LLM vs Hybrid)
│
└── docs/                           # Architecture proposals, case study, and runbooks
```

---

## 5. Quickstart

### Prerequisites
- Docker and Docker Compose installed.

### Launch All Services
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Add your Anthropic API Key in .env (if using live Claude calls)
# ANTHROPIC_API_KEY=your_key_here

# 3. Build and launch all 8 services
docker compose up --build -d
```

### Accessing Services
- **Web App**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Mailpit Web UI (Emails)**: [http://localhost:8025](http://localhost:8025)
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)
- **Mock Kanvaro Server**: [http://localhost:8080/docs](http://localhost:8080/docs)

---

## 6. Evaluation & Benchmark Results

The evaluation suite tests 40 labeled failure cases across GitLab and GitHub (testing failing unit tests, coverage < 80%, compile errors, bad dependencies, expired registry tokens, runner timeouts, disk full errors, and security scan secrets).

```bash
python evaluation/scripts/run_benchmark.py
```

### Benchmark Results
- **Category Accuracy**: **87.5%** (Target: &ge; 85%) [PASS]
- **Owner Routing Accuracy**: **87.5%** (Target: &ge; 80%) [PASS]
- **GitLab Category Accuracy**: **85.0%** [PASS]
- **GitHub Category Accuracy**: **90.0%** [PASS]
- **Duplicate Issues Created**: **0** [PASS - Zero duplicates via atomic fingerprint dedupe]
- **Prompt Injection Defense**: **PASSED** (Malicious commit message ignored; routed to true author)
- **Notification SLA**: **< 2 minutes** enforced via outbox queue with retries.

---

## 7. Adding New Adapters and Connectors

- **New CI Adapter (e.g. Bitbucket)**:
  Implement `CIAdapter` in `backend/app/adapters/<platform>.py` (`verify`, `parse`, `collect`) and register it in Settings. The core never imports platform code.
- **New Connector (e.g. Jira / Slack)**:
  Implement `Connector` in `backend/app/connectors/<tool>.py` (`create_task`, `assign`, `update_status`, `comment`, and `notify`).
