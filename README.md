# CVEngine

An intelligent CV processing and employee matching system. CVs are structured into
sections by an LLM, embedded with a local sentence-transformer model, stored in a
Chroma vector database and ranked through an agentic search pipeline built with
LangGraph.

## Highlights

- **LLM-based CV structuring**: each CV is split into canonical sections
  (summary, skills, experience, projects, certifications, education, languages, other)
  with per-section keyword extraction used as search metadata.
- **Vector search**: chunks are embedded with `nomic-ai/nomic-embed-text-v1.5`
  (768 dims, in-process) and stored in a versioned Chroma collection.
- **Agentic ranking**: LangGraph pipeline `enrich -> retrieve -> rerank -> score -> synthesize`
  with query expansion, cross-encoder reranking (`bge-reranker-base`), section-weighted
  hybrid scoring (semantic + keyword metadata) and optional LLM synthesis.
- **Multiple ingestion sources**: single file (`docx`/`txt`/`pdf`), folder batch, raw text,
  and legacy `.pkl` archive migration — all sharing the same pipeline.
- **Interfaces**: FastAPI `/v1` REST API, Typer CLI/TUI (`rich` tables), structured JSON
  logs with execution-time tracing.

## Requirements

- **Python 3.14+** (managed with [uv](https://docs.astral.sh/uv/))
- **Docker** for the Chroma server
- **Ollama** (default LLM provider, e.g. `llama3.1:8b`) or an OpenAI API key

## Installation

```bash
git clone https://github.com/gvector/CVEngine.git
cd CVEngine
uv sync                     # install dependencies (dev group included)
docker compose up -d        # start the Chroma server (port 8000)
cp .env.example .env        # optional: tweak configuration
```

## Usage

```bash
# Status: collections, models, counts
uv run cvengine status

# Inspect the vector store content (no models required)
uv run cvengine peek

# Ingest a CV file or a whole folder
uv run cvengine ingest path/to/cv.docx
uv run cvengine ingest path/to/folder

# Agentic search (degrades to base skills when Ollama is unavailable)
uv run cvengine search "Python" "Machine Learning" --business-line PV --top-k 20

# Generate synthetic CVs into the TEST collection and evaluate ranking quality
uv run cvengine synth --count 100
uv run cvengine eval --count 100

# Migrate a legacy pkl archive into Chroma
uv run cvengine migrate-pkl path/to/archive.pkl

# Run the FastAPI server (OpenAPI docs at http://localhost:8000/docs)
uv run uvicorn cvengine.api.app:create_app --factory --reload
```

Programmatic example:

```python
from cvengine.services import CVEngine

engine = CVEngine()
state = engine.graph.invoke({"skills": ["Python", "Machine Learning"], "top_k": 10})
for result in state["results"]:
    print(result.resource_id, result.score)
```

## Project Structure

```
CVEngine/
├─ src/cvengine/
│  ├─ config.py          # pydantic-settings configuration (env / .env)
│  ├─ constants.py       # section taxonomy and scoring defaults
│  ├─ observability.py   # structured JSON logging + timing
│  ├─ services.py        # application container (CVEngine)
│  ├─ db/                # Chroma repository + data models
│  ├─ embeddings/        # nomic provider with task prefixes
│  ├─ llm/               # OpenAI / Ollama providers (configurable)
│  ├─ ingestion/         # extraction, LLM sectioning, pipeline, pkl migrator
│  ├─ search/            # LangGraph agent, reranker, hybrid scoring
│  ├─ api/               # FastAPI /v1 application
│  ├─ cli/               # Typer CLI / TUI
│  └─ synthetic/         # synthetic CV generator (tests / eval)
├─ tests/                # unit, integration and parity tests
├─ docker-compose.yml    # Chroma server
├─ pyproject.toml        # uv project definition + ruff/pytest config
└─ .env.example          # configuration template
```

## Testing

```bash
uv run pytest            # unit tests run without Chroma/models;
                         # integration tests auto-skip if Chroma is down
uv run ruff check src tests
```

## Configuration

All settings are driven by `CVENGINE_*` environment variables (see `.env.example`):
LLM provider/model, embedding model, Chroma host/collections, scoring weights and
section multipliers.

## Roadmap

- Grafana + Prometheus/Loki monitoring on top of the structured logs and metrics
- Backend and frontend containerization
- New frontend (replacing the removed Streamlit app)
- Additional search modes (logic / matrix / ontology)