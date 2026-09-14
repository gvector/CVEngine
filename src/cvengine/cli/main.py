"""CVEngine CLI (TUI) built with Typer and Rich."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from cvengine.config import Settings
from cvengine.db.chroma import ChromaRepository
from cvengine.ingestion.pipeline import IngestionPipeline
from cvengine.ingestion.sectioner import HeadingSectioner
from cvengine.observability import setup_logging
from cvengine.search.enrich import QueryEnricher
from cvengine.search.graph import SearchGraph
from cvengine.services import CVEngine
from cvengine.synthetic.generator import generate_batch, generate_profiles

app = typer.Typer(help="CVEngine - CV processing and agentic search")
console = Console()
logger = logging.getLogger("cvengine")


def _engine(collection: str | None = None) -> CVEngine:
    engine = CVEngine()
    if collection is not None:
        engine.repo = ChromaRepository(
            host=engine.settings.chroma.host,
            port=engine.settings.chroma.port,
            collection_name=collection,
            provider=engine.embedding,
        )
        engine._graph = None
    return engine


@app.command()
def status() -> None:
    """Show runtime status: collections, models and counts."""
    engine = _engine()
    info = engine.status()
    console.print(Table(title="Status", show_header=False))
    _print_dict(info)


@app.command()
def peek(
    collection: str = typer.Option(None, "--collection", "-c", help="Filter by collection name"),
    limit: int = typer.Option(10, "--limit", help="Number of chunks to show"),
) -> None:
    """List Chroma collections and inspect their chunks (no models required)."""
    import chromadb

    settings = Settings()
    client = chromadb.HttpClient(host=settings.chroma.host, port=settings.chroma.port)
    collections = [col for col in client.list_collections() if collection is None or col.name == collection]
    if not collections:
        console.print("[yellow]No collections found. Ingest some CVs first.[/yellow]")
        return
    for col in collections:
        console.print(f"[bold]{col.name}[/bold] ({col.count()} chunks)")
        data = col.get(limit=limit, include=["documents", "metadatas"])
        for chunk_id, doc, meta in zip(data["ids"], data["documents"], data["metadatas"], strict=True):
            section = meta.get("section", "?") if meta else "?"
            resource = meta.get("resource_id", "?") if meta else "?"
            console.print(f"  [dim]{chunk_id}[/dim] {resource} [{section}] {doc[:100]}")
        console.print()


def _print_dict(data: dict, indent: int = 0) -> None:
    for key, value in data.items():
        if isinstance(value, dict):
            console.print(f"{'  ' * indent}{key}:")
            _print_dict(value, indent + 1)
        else:
            console.print(f"{'  ' * indent}{key}: {value}")


@app.command()
def ingest(
    path: Path = typer.Argument(..., help="CV file (.docx/.txt/.pdf) or a folder"),
    workers: int = typer.Option(None, "--workers", help="Concurrent workers for folder batch"),
    collection: str = typer.Option(None, "--collection", "-c", help="Target collection name"),
) -> None:
    """Ingest a single CV file or every CV file in a folder."""
    engine = _engine(collection)
    workers = workers or engine.settings.ingestion_workers
    with console.status("Ingesting..."):
        if path.is_dir():
            summary = engine.ingestion.ingest_batch(path, workers=workers)
            console.print(
                f"Batch done: {summary.indexed} indexed, {summary.skipped} skipped, "
                f"{summary.failed} failed (of {summary.total})"
            )
        else:
            result = engine.ingestion.ingest_file(path)
            console.print(f"{result.resource_id}: {result.status} ({result.chunks} chunks)")
            if result.error:
                console.print(f"[red]{result.error}[/red]")


@app.command()
def inspect(
    resource_id: str = typer.Argument(..., help="Resource id to inspect"),
    collection: str = typer.Option(None, "--collection", "-c", help="Collection name"),
) -> None:
    """Show the sections, keywords and metadata of a single resource (no models)."""
    engine = _engine(collection)
    chunks = engine.repo.get_resource_chunks(resource_id)
    if not chunks:
        console.print(f"[yellow]Resource {resource_id!r} not found.[/yellow]")
        return
    metadata = chunks[0][2]
    console.print(f"[bold]{resource_id}[/bold] — chunks: {len(chunks)}")
    for key, value in metadata.items():
        if key in ("section", "chunk_order", "content_hash"):
            continue
        console.print(f"  [dim]{key}:[/dim] {value}")
    console.print()
    for order, text, meta in chunks:
        keywords = meta.get("keywords", "[]")
        console.print(f"  [cyan]{meta.get('section')} [/cyan](order {order})")
        console.print(f"    {text[:200]}")
        if keywords:
            console.print(f"    [dim]keywords: {keywords}[/dim]")


@app.command()
def search(
    skills: list[str] = typer.Argument(..., help="Skills to search for"),
    weights: str = typer.Option(None, "--weights", help="Comma separated weights"),
    job_description: str = typer.Option(None, "--job-description", help="Raw job description"),
    business_line: str = typer.Option(None, "--business-line", help="Filter on business line"),
    role: str = typer.Option(None, "--role", help="Filter on role"),
    seniority: str = typer.Option(None, "--seniority", help="Filter on seniority"),
    company: str = typer.Option(None, "--company", help="Filter on company"),
    city: str = typer.Option(None, "--city", help="Filter on city of residence"),
    country: str = typer.Option(None, "--country", help="Filter on country of residence"),
    top_k: int = typer.Option(20, "--top-k", help="Number of results"),
    synthesize: bool = typer.Option(False, "--synthesize", help="Generate an LLM explanation"),
    with_rerank: bool = typer.Option(
        None, "--with-rerank/--no-rerank", help="Enable the cross-encoder reranker (default: from config)"
    ),
    top_k_per_query: int = typer.Option(None, "--top-k-per-query", help="Chunks retrieved per query"),
    rerank_top_n: int = typer.Option(None, "--rerank-top-n", help="Chunks considered for reranking"),
    collection: str = typer.Option(None, "--collection", "-c", help="Collection name"),
) -> None:
    """Run the agentic search and render results as a table."""
    engine = _engine(collection)
    weight_list: list[float] | None = None
    if weights:
        weight_list = [float(w) for w in weights.split(",")]

    rerank = engine.settings.scoring.rerank if with_rerank is None else with_rerank
    graph = SearchGraph(
        repo=engine.repo,
        enricher=engine.enricher,
        reranker=engine.reranker if rerank else None,
        llm=engine.llm,
        section_multipliers=engine.settings.scoring.section_multipliers,
        alpha=engine.settings.scoring.alpha,
        beta=engine.settings.scoring.beta,
        top_k_per_query=engine.settings.scoring.top_k_per_query,
        rerank_top_n=engine.settings.scoring.rerank_top_n,
    )
    filters = {
        "business_line": business_line,
        "role": role,
        "seniority": seniority,
        "company": company,
        "city_residenza": city,
        "country_residenza": country,
    }

    with console.status("Searching..."):
        start = time.perf_counter()
        state = graph.invoke(
            {
                "skills": skills,
                "weights": weight_list,
                "job_description": job_description,
                "filters": {k: v for k, v in filters.items() if v},
                "top_k": top_k,
                "synthesize": synthesize,
                "rerank": rerank,
                "top_k_per_query": top_k_per_query,
                "rerank_top_n": rerank_top_n,
            }
        )
        elapsed = (time.perf_counter() - start) * 1000

    table = Table(title=f"Top {len(state['results'])} results ({elapsed:.0f} ms)")
    table.add_column("Rank")
    table.add_column("Resource")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("CoE")
    table.add_column("Score")
    table.add_column("Best section snippet")
    for rank, result in enumerate(state["results"], start=1):
        person = result.person
        name = person.get("resource_name") or "-"
        role_value = person.get("role") or "-"
        coe = person.get("business_line") or "-"
        snippet = " ".join(result.best_chunk.split())[:60]
        table.add_row(str(rank), result.resource_id, name, role_value, coe, f"{result.score:.4f}", snippet)
    console.print(table)

    if state.get("query_terms"):
        console.print("[dim]Query terms: " + ", ".join(state["query_terms"]) + "[/dim]")
    if state.get("explanation"):
        console.print(f"[green]{state['explanation']}[/green]")


@app.command()
def synth(
    count: int = typer.Option(50, "--count", help="Number of synthetic CVs"),
    seed: int = typer.Option(42, "--seed", help="Random seed"),
) -> None:
    """Generate synthetic CVs and ingest them into the TEST collection."""
    settings = Settings()
    engine = _engine(settings.chroma.test_collection)
    engine.ingestion = IngestionPipeline(
        repo=engine.repo,
        sectioner=HeadingSectioner(),
    )
    profiles = generate_batch(count, seed=seed)
    with console.status(f"Ingesting {count} synthetic CVs..."):
        for profile, text in profiles:
            engine.ingestion.ingest_text(
                text=text,
                resource_id=profile.resource_id,
                extra_metadata=_profile_metadata(profile),
            )
    console.print(f"Ingested {count} synthetic CVs into '{engine.repo.collection_name}'")


def _profile_metadata(profile) -> dict:
    """Map a SyntheticProfile onto the chunk metadata schema."""
    return {
        "resource_name": profile.name,
        "role": profile.role,
        "business_line": profile.business_line,
        "seniority": profile.seniority,
        "years_experience": profile.years_experience,
        "languages": profile.languages,
        "certifications": profile.certifications,
        "source": "synthetic",
    }


@app.command()
def eval(
    count: int = typer.Option(50, "--count", help="Number of synthetic CVs"),
    seed: int = typer.Option(42, "--seed", help="Random seed"),
    top_k: int = typer.Option(10, "--top-k", help="Number of results per query"),
    with_rerank: bool = typer.Option(False, "--with-rerank", help="Enable the reranker"),
    report: Path = typer.Option(None, "--report", help="Write a JSON report to this path"),
) -> None:
    """Evaluate ranking quality on the synthetic dataset (precision@k / MRR)."""
    import json

    settings = Settings()
    engine = _engine(settings.chroma.test_collection)
    engine.ingestion = IngestionPipeline(
        repo=engine.repo,
        sectioner=HeadingSectioner(),
    )

    profiles = generate_profiles(count, seed=seed)
    profiles_with_text = generate_batch(count, seed=seed)
    with console.status(f"Ingesting {count} synthetic CVs..."):
        for profile, text in profiles_with_text:
            engine.ingestion.ingest_text(
                text=text,
                resource_id=profile.resource_id,
                extra_metadata=_profile_metadata(profile),
            )

    graph = SearchGraph(
        repo=engine.repo,
        enricher=QueryEnricher(engine.llm),
        reranker=engine.reranker if with_rerank else None,
        section_multipliers=settings.scoring.section_multipliers,
        alpha=settings.scoring.alpha,
        beta=settings.scoring.beta,
        top_k_per_query=settings.scoring.top_k_per_query,
        rerank_top_n=settings.scoring.rerank_top_n,
    )

    details: dict[str, dict] = {}
    precision_total = 0.0
    mrr_total = 0.0
    queries = 0
    for profile in profiles:
        primary_skill = profile.skills[0]
        state = graph.invoke(
            {
                "skills": [primary_skill],
                "top_k": top_k,
                "synthesize": False,
                "rerank": with_rerank,
            }
        )
        ids = [result.resource_id for result in state["results"]]
        hit = profile.resource_id in ids
        rank = ids.index(profile.resource_id) + 1 if hit else None
        if hit:
            precision_total += 1.0
            mrr_total += 1.0 / rank
        queries += 1
        details[profile.resource_id] = {
            "skill": primary_skill,
            "business_line": profile.business_line,
            "hit": hit,
            "rank": rank,
        }

    precision = round(precision_total / queries, 4)
    mrr = round(mrr_total / queries, 4)
    console.print(f"Queries: {queries}")
    console.print(f"precision@{top_k}: {precision}")
    console.print(f"MRR: {mrr}")

    if report is not None:
        payload = {
            "count": count,
            "seed": seed,
            "top_k": top_k,
            "rerank": with_rerank,
            "alpha": settings.scoring.alpha,
            "beta": settings.scoring.beta,
            "section_multipliers": settings.scoring.section_multipliers,
            "precision_at_k": precision,
            "mrr": mrr,
            "details": details,
        }
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"Report written to {report}")


@app.command("migrate-pkl")
def migrate_pkl(path: Path = typer.Argument(..., help="Path to the legacy .pkl archive")) -> None:
    """Re-index a legacy pkl archive through the ingestion pipeline."""
    from cvengine.ingestion.migrator import migrate_pkl as run_migration

    engine = _engine()
    with console.status(f"Migrating {path}..."):
        summary = run_migration(path=path, pipeline=engine.ingestion)
    console.print(
        f"Migration done: {summary.indexed} indexed, {summary.skipped} skipped, "
        f"{summary.failed} failed (of {summary.total})"
    )


if __name__ == "__main__":
    setup_logging()
    app()
