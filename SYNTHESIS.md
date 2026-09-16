# SYNTHESIS — Dataset sintetico "società di consulenza"

Documento di piano d'azione per la generazione di un dataset sintetico realistico e
**verificabile**, utile a validare la qualità del ranking di CVEngine senza attendere
i dati reali. Aggiornato man mano che l'implementazione procede.

---

## 1. Obiettivo

Costruire un database sintetico di una società di consulenza con **400 CV**, organizzato
per rami, ruoli e **4 livelli di competenza**, con un **ground truth** noto. Serve a
rispondere alla domanda: *il sistema pesca davvero i candidati migliori?*

---

## 2. Decisioni concordate

| Tema | Scelta |
|---|---|
| Tassonomia | 6 rami (5 linee di servizio + funzioni corporate) |
| Scala | 400 CV |
| Lingua | CV in **inglese**, anagrafiche Faker `it_IT`/`en_US` |
| Testo CV | **Template ricchi deterministici** (no LLM), arricchibili in futuro |
| Specialità | **1 cluster primario** (con livello) + skill secondarie |
| Comando | Estensione di `cvengine synth`, collection dedicata **`...__synth`** |

---

## 3. Prerequisiti (verificati)

| Requisito | Stato |
|---|---|
| Python 3.14 + uv | ✅ |
| Chroma server (docker) | ✅ attivo su `localhost:8000` |
| `faker` | ⚠️ da aggiungere (`uv add faker`) |
| Ollama | ❌ non presente su questa macchina (non serve per i template) |

> Nota: l'assenza di Ollama non blocca nulla, perché la generazione è a template.
> Serve solo se in futuro si vorrà arricchire il testo con un LLM.

---

## 4. Ontologia di dominio (`src/cvengine/synthetic/domain.py`)

### 4.1 Rami e ruoli (3 per ramo = 18)

| Ramo (business_line) | Ruoli |
|---|---|
| `STRATEGY` — Strategy & Management | Business Analyst, Strategy Consultant, Engagement Manager |
| `FINANCE` — Finance & Accounting | Accountant, Financial Controller, Tax Consultant |
| `TECH` — Technology & Digital | Software Engineer, Data Scientist, Cloud Engineer |
| `COMPLIANCE` — Compliance & Quality | Quality Consultant, Regulatory Affairs Specialist, Validation Engineer |
| `HR` — Human Resources | HR Specialist, Talent Acquisition Specialist, HR Business Partner |
| `OPS` — Internal Services | Legal Counsel, Marketing Specialist, IT Support Specialist |

### 4.2 Cluster di skill primarie per ruolo (esempi)

- **Business Analyst**: market analysis, requirements gathering, process mapping, business planning
- **Strategy Consultant**: business strategy, M&A due diligence, competitive analysis, change management
- **Engagement Manager**: PMO, project management, stakeholder management, budgeting
- **Accountant**: bookkeeping, IFRS/GAAP, tax compliance, reconciliation
- **Financial Controller**: controlling, budgeting, forecasting, financial reporting, ERP (SAP)
- **Tax Consultant**: corporate tax, VAT, transfer pricing, tax compliance
- **Software Engineer**: Python, Java, REST APIs, unit testing, software design, Git
- **Data Scientist**: Python, Machine Learning, statistics, SQL, data visualization
- **Cloud Engineer**: AWS, Azure, Docker, Kubernetes, Terraform, CI/CD
- **Quality Consultant**: QMS, GMP, ISO 9001, CAPA, internal audit
- **Regulatory Affairs Specialist**: regulatory submissions, MDR/IVDR, EMA/FDA, technical dossier
- **Validation Engineer**: CSV, GAMP 5, IQ/OQ/PQ, GxP, data integrity
- **HR Specialist**: recruiting, onboarding, HRIS, labor law
- **Talent Acquisition Specialist**: sourcing, interviewing, employer branding, ATS
- **HR Business Partner**: performance management, employee relations, organizational design
- **Legal Counsel**: contract law, corporate law, GDPR, compliance
- **Marketing Specialist**: digital marketing, SEO, CRM, content strategy
- **IT Support Specialist**: helpdesk, networking, Windows/Linux, ticketing

### 4.3 I 4 livelli di competenza

| Livello | Seniority | Anni | Skill elencate | Progetti | Certificazioni | Segnale testuale |
|---|---|---|---|---|---|---|
| `low` | Junior | 1–3 | 2–3 | 1 | 0 | "assisted", "supported" |
| `medium` | Mid | 3–6 | 4–6 | 2–3 | 0–1 | "contributed", "implemented" |
| `high` | Senior | 6–10 | 6–8 | 3–4 | 1–2 | "led", "designed" |
| `professional` | Lead/Principal | 10+ | 8–12 | 4–6 | 2–3 | "architected", "directed", team leadership |

Il livello è codificato **sia nei metadata** sia **nel testo** (densità di skill, numero
e profondità dei progetti, certificazioni, verbi), così il ranking ha segnali coerenti.

---

## 5. Generatore (`src/cvengine/synthetic/generator.py`)

- `SyntheticProfile` arricchito: `resource_id`, `name`, `email`, `city`, `country`,
  `branch`, `role`, `seniority`, `level`, `years_experience`, `primary_skills`,
  `secondary_skills`, `languages`, `certifications`.
- `build_cv_text(profile)` → CV inglese deterministico a sezioni:
  `PROFESSIONAL SUMMARY`, `SKILLS`, `PROFESSIONAL EXPERIENCE`, `EDUCATION`,
  `CERTIFICATIONS`, `LANGUAGES` (heading compatibili con `HeadingSectioner`).
- Distribuzione **400 = 6 rami × 3 ruoli × 4 livelli = 72 celle** (~5–6 per cella),
  deterministica per `seed`.
- Anagrafiche con **Faker** (`it_IT` + `en_US`).
- **Manifest ground-truth** → `cvengine_data/synth_manifest.json`.

### 5.1 Sectioner e keyword
`HeadingSectioner` estrae **keyword euristiche dalla sezione SKILLS** (split su virgola,
vocabolario controllato) così il path del **keyword-boost** viene esercitato senza LLM.

---

## 6. CLI

### 6.1 `cvengine synth` (esteso)
```
cvengine synth --count 400 --seed 42 --collection cvs__nomic-embed-text-v1.5__v1__synth
```
- Ingesta con `HeadingSectioner` (no LLM), inietta i metadata (ramo/ruolo/seniority/
  livello/nome/anni), scrive il manifest.
- Collection di default via `CVENGINE_CHROMA_SYNTH_COLLECTION`.

### 6.2 `cvengine eval-rank` (nuovo)
- Carica il manifest ed esegue query mirate a *(skill, livello)*.
- Verifica l'ordinamento atteso: `professional > high > medium > low`.
- Metriche: **NDCG@k** (relevance = rank del livello), **MRR**, **precision@k**;
  report JSON.

---

## 7. Test

- **Unit**: coerenza ontologia (ogni ramo ha 3 ruoli, ogni ruolo un cluster ≥ 4 skill,
  4 livelli definiti); determinismo per seed; `build_cv_text` include le skill primarie
  e i segnali di livello; `NDCG` con caso noto.
- **Integration**: synth (piccolo) → search per una skill → la risorsa `professional`
  in cima; filtro per ramo funziona.
- Aggiornamento di `tests/unit/test_generator.py` alla nuova struttura.

---

## 8. Config & documentazione

- `.env.example`: aggiunta `CVENGINE_CHROMA_SYNTH_COLLECTION`.
- `README.md`: comandi `synth`/`eval-rank` aggiornati.
- `future_dev.md`: decisioni, pro/contro, risultati.

---

## 9. Scelta template vs LLM (approfondimento)

**Decisione: template deterministici.** Motivo: l'obiettivo è *verificare il ranking*,
quindi il ground truth deve essere **esatto** (skill e livello garantiti). Un LLM, anche
grande, può omettere una skill o alterare il segnale di livello → valutazione rumorosa.

Se in futuro si vorrà un dataset **più realistico** (demo), un modello piccolo di Ollama
può bastare **a patto di usarlo come "riscrittura vincolata"**, non come generazione
libera: gli si passa lo scheletro esatto (nome, lista skill, anni, livello) e gli si
chiede di produrre prosa **preservando tutte le skill elencate**, con output JSON,
validazione e retry (meccanismo già presente nel provider LLM). Modelli candidati:
`qwen2.5:3b`, `llama3.2:3b`, `gemma3:4b`, `phi4-mini`. Suggerimento: **`qwen2.5:3b`**
o **`llama3.2:3b`** (inglese, veloci, buon instruction-following). Resta comunque il
dataset a template come **fonte di verità** per l'eval.

---

## 10. Ordine di esecuzione

1. `uv add faker`.
2. `synthetic/domain.py` (ontologia).
3. `synthetic/generator.py` (profili, testo, distribuzione, manifest).
4. `HeadingSectioner` con keyword euristiche.
5. Config `synth_collection` + `.env.example`.
6. CLI `synth` esteso + `eval-rank` (+ helper NDCG).
7. Test unit + integration.
8. Docs (`future_dev.md`, `README.md`).
9. Verifica finale: ruff, pytest, smoke `synth` + `eval-rank` su Chroma.

---

## 11. Stato implementazione (✅ completato)

Tutti i punti 1–9 eseguiti. File toccati:
- `src/cvengine/synthetic/domain.py` (nuovo) — ontologia rami/ruoli/skill/livelli.
- `src/cvengine/synthetic/generator.py` — profili, `build_cv_text`, manifest.
- `src/cvengine/ingestion/sectioner.py` — keyword euristiche nel `HeadingSectioner`.
- `src/cvengine/config.py` — `synth_collection`.
- `src/cvengine/cli/main.py` — `synth` esteso (`--reset`, `--manifest`), nuovo `eval-rank`,
  rimosso il vecchio `eval`.
- Test: `test_domain.py`, `test_generator.py` (riscritto), `test_ndcg.py`, aggiornati
  `test_sectioner.py`, `test_parity.py`.

### 11.1 Verifica sul dataset da 400 CV (nomic embeddings, Chroma)

`cvengine synth --count 400 --reset && cvengine eval-rank --top-k 10`

| Metrica | Valore |
|---|---|
| query | 97 (skill primarie) |
| **NDCG@10** | **0.83** |
| **MRR** | **0.99** |
| **precision@10** | **0.96** |

> Il ranking trova quasi sempre risorse rilevanti in cima (MRR/precision alti), ma
> **non sempre le più competenti**: il top-1 è `low` in 55/97 query.

### 11.2 Scoperta chiave (vale il gioco di aver costruito il dataset)

**La similarità coseno favorisce i CV "corti".** Un junior elenca 2–3 skill, quindi il
termine della query pesa di più nel suo embedding; un professionista elenca 8–12 skill
→ il termine è "diluito" → coseno più basso. Risultato: per una singola skill la risorsa
`low` batte spesso la `professional`.

### 11.3 Soluzione implementata: competence boost ✅

Aggiunto **`CVENGINE_SCORING_COMPETENCE_WEIGHT`** (default **0 = off**): nello score
viene sommato `competence_weight × competence`, dove `competence ∈ [0,1]` deriva da
`seniority` (Junior=0.25 … Lead/Principal=1.0) o da `years_experience/20` nei metadata.

Formula: `score = sezione·(α·base + β·keyword_overlap) + competence_weight·competence`.

**Impatto su `eval-rank` (400 CV, top-1 per livello):**

| competence_weight | NDCG@10 | MRR | precision@10 | top-1 professional |
|---|---|---|---|---|
| 0.0 (default) | 0.83 | 0.99 | 0.96 | 13/97 |
| **0.15** | **0.98** | 0.99 | 0.97 | **85/97** |
| 0.3 | 0.98 | 0.99 | 0.97 | ~87/97 |

Con un peso piccolo (0.15) il sistema pesca **in modo quasi perfetto i più competenti**,
mantenendo la rilevanza. Config: `--competence-weight` nella CLI (search ed eval-rank) e
`competence_weight` nel body dell'API `/v1/search`.

### 11.4 Uso comandi

```bash
uv run cvengine synth --count 400 --reset          # dataset completo + manifest
uv run cvengine eval-rank --report cvengine_data/eval_rank.json
uv run cvengine search "Machine Learning" --business-line TECH --collection cvs__nomic-embed-text-v1.5__v1__synth
```
