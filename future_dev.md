# CVEngine — Future Development Log

Questo documento traccia le implementazioni fatte, le scelte che le hanno motivate,
i pro/contro e le idee per le evoluzioni future. Viene aggiornato a ogni sessione.

---

## 1. Stato attuale (implementato)

### 1.1 Toolchain e layout
- **Fatto**: migrazione a Python 3.14 + `uv` (pyproject.toml + uv.lock), ruff e pytest,
  package green-field `src/cvengine/` (src-layout), rimozione della legacy
  (`components/`, `main.py`, `api_cv.py`, frontend Streamlit, `requirements.txt`).
- **Decisione**: toolchain moderna, lock riproducibile, struttura modulare pulita.
- **Pro**: build riproducibili, lint/format automatici, layout scalabile.
- **Contro**: richiede che gli agenti/utenti usino `uv` (mai pip).

### 1.2 Configurazione (`config.py`)
- **Fatto**: `pydantic-settings` con env prefix `CVENGINE_`, modelli annidati
  (LLM, embedding, Chroma, scoring), override da `.env`. Fix del partial-update
  dei modelli annidati (`default_factory` + `nested_model_default_partial_update`).
- **Pro**: configurabile 100% via env; safe default; tipizzato.
- **Contro**: i moltiplicatori di sezione vivono in `constants.py`, non ancora
  configurabili via env (TODO).

### 1.3 Osservabilità (`observability.py`)
- **Fatto**: log strutturati JSON (formatter custom), `log_event` per campi extra,
  decorator `timeit` per il tracing dei tempi di esecuzione per stadio.
- **Decisione**: niente dipendenze pesanti (no OTel) in v1; Grafana/Prometheus rimandati.
- **Pro**: zero dipendenze, timing su ogni nodo, pronto per essere risucchiato da Prometheus.
- **Contro**: niente tracing distribuito né metriche esposte (v2).

### 1.4 Embedding (`embeddings/`)
- **Fatto**: `SentenceTransformerProvider` con `nomic-ai/nomic-embed-text-v1.5`
  (768 dim, matryoshka), prefissi `search_document:`/`search_query:`, normalize L2,
  `quiet_model_logging()` per silenziare il noise HF/transformers.
- **Decisione**: in-process, no servizio embedding separato (compliance/privacy).
- **Pro**: semplice, locale, no costi API.
- **Contro**: ~270MB in memoria per processo; cambio modello = re-index + bump collection.

### 1.5 LLM (`llm/`)
- **Fatto**: astrazione `LLMProvider` con `OllamaProvider` (default `llama3.1:8b`) e
  `OpenAIProvider`, factory da config, output JSON-schema, temperature 0, token counting.
- **Pro**: provider swappabile a runtime via env; grounding anti-allucinazione.
- **Contro**: la qualità dipende dal modello Ollama scelto (da validare).

### 1.6 Vector store (`db/`)
- **Fatto**: `ChromaRepository` su server docker (porta 8000), collection **versionate
  nel nome** (`cvs__nomic-embed-text-v1.5__v1`), embedding sempre passati esplicitamente,
  metadata ricchi per chunk (campi Person, `section`, `keywords`, `content_hash`,
  `chunk_order`), idempotenza via content-hash, binding lazy della collection
  (status funziona senza server).
- **Decisione**: Chroma su docker (voluto dall'utente), collection lazy.
- **Pro**: robusto a server down, schema metadata auto-documentato.
- **Contro**: filtro metadata solo su `business_line` oggi (ampliabile).

### 1.7 Ingestion (`ingestion/`)
- **Fatto**: estrazione `docx|txt|pdf|text`, **sezionamento LLM** in sezioni canoniche
  con **keyword per sezione**, `CVSectioner` (JSON schema + retry + fallback),
  `HeadingSectioner` deterministico (test/eval), pipeline unica
  (file/cartella/testo/migrazione pkl), merge metadata autoritativi (pkl/SQL) + LLM.
- **Decisione**: sezioni create dal modello (i CV reali non hanno sezioni native).
- **Pro**: pipeline unica per tutte le sorgenti; fallback se l'LLM fallisce.
- **Contro**: ingestion sequenziale (lento su ~2000 CV con Ollama); niente resume esplicito.

### 1.8 Ricerca (`search/`)
- **Fatto**: grafo LangGraph `enrich → retrieve → rerank → score → synthesize`.
  - `enrich`: estrazione skill da JD + espansione query (fallback a skill base se LLM giù).
  - `retrieve`: multi-query top-k, filtro metadata business_line.
  - `rerank`: cross-encoder `BAAI/bge-reranker-base` (lazy, sigmoid).
  - `score`: `sezione · (α·base + β·keyword_overlap)` con pesi per skill (α=0.8, β=0.2).
  - `synthesize`: spiegazione LLM opzionale.
- **Decisione**: scoring ibrido con boost da keyword-metadata e moltiplicatori per sezione.
- **Pro**: qualità migliorata rispetto alla sola cosine; degradazione graziosa.
- **Contro**: α/β e moltiplicatori da calibrare su dati reali; niente loop di refine
  né ricerca lessicale (BM25).

### 1.9 API e CLI
- **Fatto**: FastAPI `/v1/*` (search, ingest, batch, resource, summary, status);
  CLI Typer/rich (`status`, `peek`, `ingest`, `search`, `synth`, `eval`, `migrate-pkl`).
- **Pro**: interfacce complete e testabili.
- **Contro**: search non restituisce i metadati Person (solo id/score/snippet);
  niente paginazione/auth; `rerank` non esposto nell'API.

### 1.10 Test e qualità
- **Fatto**: 55 test verdi (unit senza dipendenze, integration su Chroma reale, parity
  su sintetici), ruff pulito, `eval` CLI (precision@k / MRR).
- **Pro**: piramide solida, test di parità con skill note.
- **Contro**: nessun e2e con embeddings reali + Ollama; nessuna CI.

### 1.11 Dati sintetici (`synthetic/`)
- **Fatto**: generatore deterministico di profili CV con skill controllate.
- **Pro**: fixture per test e baseline di qualità.
- **Contro**: non rappresenta la varietà dei CV reali (valutare tuning su veri).

---

## 2. Piano sessione corrente (implementato)

Obiettivo: rendere il sistema **completo, controllabile e customizzabile**.

Decisioni confermate dall'utente: **P1+P2+P3+P4**, retrieval ibrido e monitoring v2
rimandati al futuro, configurazione **solo env**, dedup **solo content-hash**.

### P1 — Search arricchita e filtri ✅
- I risultati di ricerca ora includono i **metadati Person** (resource_name, role,
  company, business_line, seniority, email, city/country, ecc.) presi dal chunk
  migliore (`ChunkHit.metadata` → `RankedResource.person`).
- **Filtri multipli** via `build_where` (Chroma `$and`): business_line, role,
  seniority, company, city_residenza, country_residenza, status. Chiavi sconosciute
  ignorate.
- Override **per-request** nel grafo: `rerank`, `rerank_top_n`, `top_k_per_query`,
  `section_multipliers` (stato LangGraph).
- API `SearchRequest` estesa con i nuovi campi; CLI `search` con colonne Name/Role/CoE
  e flag `--business-line/--role/--seniority/--company/--city/--country`,
  `--with-rerank/--no-rerank`, `--top-k-per-query`, `--rerank-top-n`.
- Config: `CVENGINE_SCORING_SECTION_MULTIPLIERS` (JSON), `CVENGINE_SCORING_RERANK`,
  `CVENGINE_INGESTION_WORKERS`.
- **Decisione**: il reranker si carica (lazy) solo se `scoring.rerank=true`; il grafo
  rispetta il flag anche per-request.
- **Pro**: API pronta per il futuro frontend, tuning esposto, filtrabilità reale.
- **Contro**: superficie API maggiore (coperta dai test).

### P2 — Ingestion robusta ✅
- `ingest_batch(workers=N)` con `ThreadPoolExecutor` (default 1 = sequenziale),
  isolamento errori per file già presente, `--workers` nella CLI e nel batch API.
- **Pro**: ~2000 CV gestibili con concorrenza su Ollama.
- **Contro**: concorrenza su Ollama da calibrare (rate limit) — default 1 sicuro.

### P3 — Tooling di qualità ✅
- `cvengine inspect <resource_id>`: sezioni + keyword + metadata di un CV (senza
  caricare modelli) → utile per validare la strutturazione LLM.
- `cvengine eval` esteso: `--report <path>` scrive `cvengine_data/eval_report.json`
  con precision@k, MRR e dettagli per risorsa; parametri (alpha, beta, moltiplicatori,
  rerank) salvati nel report per riproducibilità.
- **Pro**: validazione rapida e riproducibile.
- **Contro**: nessuno rilevante.

### P4 — CI ✅
- `.github/workflows/ci.yml`: uv sync, ruff check, ruff format --check, pytest con
  servizio Chroma (container `chromadb/chroma`) sui branch dev/feat.
- **Pro**: qualità garantita a ogni push; i test integration girano perché Chroma è
  disponibile come service.
- **Contro**: dipende dal pull dell'immagine Chroma nei runner.

### Fix di stabilità (bonus)
- **Flakiness dei test integration**: il fixture ora usa una **collection a nome fisso
  ricreata pulita** a ogni test invece di nome univoco + delete → server Chroma stabile
  (suite verde 5/5 run consecutive).
- **Metadata sintetici**: `synth`/`eval` ora iniettano i metadati del profilo
  (business_line, role, seniority, ecc.) nei chunk → i filtri funzionano sui dati
  di test.

---

## 3. Decisioni aperte (da chiarire con l'utente)

- **Retrieval ibrido (BM25 + vector)**: rimandato al futuro (nessuna dipendenza nuova
  ora). Implementazione prevista con RRF e pesi configurabili.
- **Monitoring v2 (Prometheus/Grafana)**: rimandato. Log JSON + timing attuali bastano.

---

## 4. Idee per implementazioni future

- **Competence boost** ✅ *implementato* (vedi SYNTHESIS.md): `CVENGINE_SCORING_COMPETENCE_WEIGHT`
  (default 0) aggiunge `peso × seniorità` allo score. Su 400 CV sintetici porta NDCG@10
  da 0.83 a 0.98 e il top-1 `professional` da 13/97 a 85/97. Da **calibrare sui dati reali**.
- **Visualizzatore Chroma** ✅ *implementato*: pagina read-only `/viewer` (browse + query
  client-side) nell'API FastAPI, attivabile con `CVENGINE_VIEWER_ENABLED` o `cvengine serve --viewer`.
- **Retrieval ibrido**: fusione vettoriale + lessicale (BM25/TF-IDF) con RRF
  (Reciprocal Rank Fusion) e pesi configurabili.
- **Loop di refine nell'agente**: retrieve → critica → raffina query → re-retrieve
  (multi-step LangGraph).
- **Monitoring v2**: endpoint `/metrics` Prometheus + dashboard Grafana + OTel traces
  sui nodi LangGraph.
- **Containerizzazione backend**: Dockerfile + compose con API e Chroma insieme;
  poi nuovo frontend.
- **Paginazione e auth** API quando esposta oltre il perimetro interno.
- **Ottimizzazioni vettoriali**: riduzione matryoshka (512 dim) per velocità, o
  passaggio a modelli più nuovi con re-index versionato.
- **Summary/rag sui CV**: interrogare i chunk del singolo CV (RAG) per Q&A su una risorsa.
- **Feedback loop**: integrare i feedback degli utenti (dal vecchio sistema) per
  aggiustare pesi/moltoliplicatori.
- **Embedding distribuiti**: servizio embedding separato (Ollama embedding) quando il
  backend sarà containerizzato e multi-replica.