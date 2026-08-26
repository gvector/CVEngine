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
from cvengine.search.reranker import CrossEncoderReranker
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
    collection: str = typer.Option(None, "--collection", "-c", help="Target collection name"),
) -> None:
    """Ingest a single CV file or every CV file in a folder."""
    engine = _engine(collection)
    with console.status("Ingesting..."):
        if path.is_dir():
            summary = engine.ingestion.ingest_batch(path)
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
def search(
    skills: list[str] = typer.Argument(..., help="Skills to search for"),
    weights: str = typer.Option(None, "--weights", help="Comma separated weights"),
    job_description: str = typer.Option(None, "--job-description", help="Raw job description"),
    business_line: str = typer.Option(None, "--business-line", help="Filter on business line"),
    top_k: int = typer.Option(20, "--top-k", help="Number of results"),
    synthesize: bool = typer.Option(False, "--synthesize", help="Generate an LLM explanation"),
    with_rerank: bool = typer.Option(False, "--with-rerank", help="Enable the cross-encoder reranker"),
    collection: str = typer.Option(None, "--collection", "-c", help="Collection name"),
) -> None:
    """Run the agentic search and render results as a table."""
    engine = _engine(collection)
    weight_list: list[float] | None = None
    if weights:
        weight_list = [float(w) for w in weights.split(",")]

    graph = SearchGraph(
        repo=engine.repo,
        enricher=engine.enricher,
        reranker=CrossEncoderReranker() if with_rerank else None,
        llm=engine.llm,
        top_k_per_query=engine.settings.scoring.top_k_per_query,
        rerank_top_n=engine.settings.scoring.rerank_top_n,
    )
    filters = {"business_line": business_line} if business_line else None

    with console.status("Searching..."):
        start = time.perf_counter()
        state = graph.invoke(
            {
                "skills": skills,
                "weights": weight_list,
                "job_description": job_description,
                "filters": filters,
                "top_k": top_k,
                "synthesize": synthesize,
            }
        )
        elapsed = (time.perf_counter() - start) * 1000

    table = Table(title=f"Top {len(state['results'])} results ({elapsed:.0f} ms)")
    table.add_column("Rank")
    table.add_column("Resource")
    table.add_column("Score")
    table.add_column("Skills hit")
    table.add_column("Best section snippet")
    for rank, result in enumerate(state["results"], start=1):
        hits = ", ".join(f"{k}={v:.3f}" for k, v in result.skills_hit.items())
        snippet = " ".join(result.best_chunk.split())[:80]
        table.add_row(str(rank), result.resource_id, f"{result.score:.4f}", hits, snippet)
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
            engine.ingestion.ingest_text(text=text, resource_id=profile.resource_id)
    console.print(f"Ingested {count} synthetic CVs into '{engine.repo.collection_name}'")


@app.command()
def eval(
    count: int = typer.Option(50, "--count", help="Number of synthetic CVs"),
    seed: int = typer.Option(42, "--seed", help="Random seed"),
    top_k: int = typer.Option(10, "--top-k", help="Number of results per query"),
    with_rerank: bool = typer.Option(False, "--with-rerank", help="Enable the reranker"),
) -> None:
    """Evaluate ranking quality on the synthetic dataset (precision@k / MRR)."""
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
            engine.ingestion.ingest_text(text=text, resource_id=profile.resource_id)

    graph = SearchGraph(
        repo=engine.repo,
        enricher=QueryEnricher(engine.llm),
        reranker=CrossEncoderReranker() if with_rerank else None,
        top_k_per_query=settings.scoring.top_k_per_query,
        rerank_top_n=settings.scoring.rerank_top_n,
    )

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
            }
        )
        ids = [result.resource_id for result in state["results"]]
        if profile.resource_id in ids:
            precision_total += 1.0
            mrr_total += 1.0 / (ids.index(profile.resource_id) + 1)
        queries += 1

    precision = precision_total / queries
    mrr = mrr_total / queries
    console.print(f"Queries: {queries}")
    console.print(f"precision@{top_k}: {precision:.4f}")
    console.print(f"MRR: {mrr:.4f}")


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
