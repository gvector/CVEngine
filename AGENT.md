# CVEngine - AI Agent Guidelines

## 1. Project Context
CVEngine is an intelligent CV processing and employee matching system. It ingests CVs
from multiple sources (docx/txt/pdf files, raw text, legacy pkl archives), structures
them into sections via an LLM, embeds them with a local sentence-transformer model,
stores the chunks in a Chroma vector database, and ranks resources through an agentic
search pipeline built with LangGraph.

The old `components/`, `main.py`, `api_cv.py`, `pages/`, `Welcome.py` and related legacy
files have been **removed**. All development lives in the green-field `src/cvengine/`
package. The frontend (Streamlit) is out of scope; the current interface is the CLI/TUI
and the FastAPI `/v1` endpoints.

## 2. Tech Stack & Tools
- **Language:** Python 3.14+ (`.python-version` is 3.14)
- **Dependency Management:** uv (never use pip). Run `uv sync`; add deps with `uv add`.
- **Project layout:** src-layout. Package `src/cvengine/` with submodules
  `db/`, `ingestion/`, `embeddings/`, `llm/`, `search/`, `api/`, `cli/`, `synthetic/`.
- **Linting & Formatting:** Ruff (config in `pyproject.toml`). Run `uv run ruff check src tests`
  and `uv run ruff format src tests`. Do not commit code that fails the checks.
- **Testing:** Pytest. Run `uv run pytest`. Unit tests must not require Chroma or models.

## 3. Architecture Decisions (2026-08)

### Vector store
- **ChromaDB server** via `docker-compose.yml` (service `chroma`, port 8000). Start with
  `docker compose up -d`.
- Collections are **versioned by name**: `cvs__nomic-embed-text-v1.5__v1` (prod) and
  `...__v1__test` (synthetic). Bump the name when the embedding model or chunking changes.
- The repository (`cvengine/db/chroma.py`) always passes embeddings explicitly and stores
  rich metadata per chunk; Chroma never embeds server-side.

### Embeddings
- Model: `nomic-ai/nomic-embed-text-v1.5` (768 dims), sentence-transformers, **in-process**.
- Task prefixes are applied (`search_document: ` / `search_query: `) — see
  `cvengine/embeddings/provider.py`. Do not change the prefix scheme without bumping the collection.

### LLM
- Provider is **configurable** (default `ollama`/`llama3.1:8b`, optional `openai`), driven by
  `CVENGINE_LLM_*` env vars (see `.env.example`). Implementations in `cvengine/llm/`.
- Use JSON-schema-constrained output and temperature 0 for extraction tasks to reduce hallucination.

### Ingestion pipeline (`cvengine/ingestion/`)
- Sources: single file, folder batch, raw text string, and legacy pkl migration — all funnel
  into the same `IngestionPipeline.ingest_text()` core.
- The **LLM structures each CV into canonical sections** (summary, skills, experience, projects,
  certifications, education, languages, other) and extracts **keywords per section**.
- Metadata stored per chunk: person fields (from pkl or extracted), `section`, `keywords`,
  `content_hash`, `chunk_order`.
- Idempotency via content-hash; already-indexed CVs are skipped.
- `HeadingSectioner` is a deterministic (non-LLM) sectioner used only for tests/eval.

### Search (`cvengine/search/`)
- Agentic graph (`SearchGraph`, LangGraph): `enrich -> retrieve -> rerank -> score -> synthesize`.
- `enrich`: extract skills from a job description (if given) and expand them into multiple queries.
- `retrieve`: multi-query top-k retrieval on Chroma with optional `business_line` metadata filter.
- `rerank`: cross-encoder `BAAI/bge-reranker-base` (optional, lazy-loaded).
- `score`: hybrid scoring
  `chunk = section_multiplier * (alpha * base + beta * keyword_overlap)` with
  per-skill weighted aggregation. Defaults alpha=0.8, beta=0.2; section multipliers in
  `cvengine/constants.py`.
- `synthesize`: optional LLM explanation (default off).

### API / CLI
- FastAPI app (`cvengine/api/app.py`) exposes `/v1/*`: search, ingest, batch ingest,
  get resource, summary, status. Build with `create_app(engine)`.
- Typer CLI (`cvengine ...`): `status`, `ingest`, `search`, `synth`, `eval`, `migrate-pkl`.
  Rich tables for output.

### Monitoring
- Structured JSON logs via `cvengine/observability.py` (`log_event`, `timeit` for timing).
- Grafana/Prometheus is a future milestone; do not add heavy telemetry dependencies now.

## 4. Coding Standards
- **Type Hinting:** Strictly use modern Python type hints (`list[str]`, `dict`, etc.) for all
  function signatures and class attributes.
- **Docstrings:** Use Google-style docstrings for all modules, classes, and public functions.
- **Error Handling:** Catch specific exceptions. Never use a bare `except:`. Always log errors
  via `logging` (structured helpers in `cvengine/observability.py`).
- **Data Structures:** Prefer `dataclasses` or `pydantic` models over raw dictionaries.
- **Secrets:** Never commit secrets. Config comes from env / `.env` (see `.env.example`).

## 5. Common Workflows
```bash
uv sync                                # install deps (incl. dev group)
docker compose up -d                   # start Chroma server
uv run pytest                          # run tests (integration tests skip if Chroma is down)
uv run ruff check src tests            # lint
uv run ruff format src tests           # format
uv run cvengine --help                 # CLI/TUI entry point
uv run uvicorn cvengine.api.app:create_app --factory --reload   # run the API
```

## 6. Testing Strategy
- Unit tests (`tests/unit/`): no Chroma, no model downloads — use `tests/fakes.py`
  (FakeEmbeddingProvider, FakeLLM).
- Integration tests (`tests/integration/`): require a running Chroma server; they auto-skip
  when it is unreachable.
- Parity test: synthetic CVs with known skills must rank in the top-k; also available as
  `cvengine eval` for a precision@k / MRR report.