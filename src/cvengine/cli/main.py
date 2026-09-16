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
from cvengine.search.graph import SearchGraph
from cvengine.services import CVEngine
from cvengine.synthetic import build_cv_text, build_manifest, generate_profiles, profile_metadata

app = typer.Typer(help="CVEngine - CV processing and agentic search")
console = Console()
logger = logging.getLogger("cvengine")


def ndcg_at_k(gains: list[int], k: int) -> float:
    """Compute NDCG@k for a list of relevance gains (higher is better).

    :param gains: relevance of each ranked result, best-first
    :param k: cutoff
    :return: the NDCG@k in [0, 1]
    """
    import math

    def dcg(values: list[int]) -> float:
        return sum(gain / math.log2(index + 2) for index, gain in enumerate(values[:k]))

    ideal = sorted(gains, reverse=True)
    ideal_dcg = dcg(ideal)
    return dcg(gains) / ideal_dcg if ideal_dcg else 0.0


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
    competence_weight: float = typer.Option(None, "--competence-weight", help="Seniority boost weight (0=off)"),
    collection: str = typer.Option(None, "--collection", "-c", help="Collection name"),
) -> None:
    """Run the agentic search and render results as a table."""
    engine = _engine(collection)
    weight_list: list[float] | None = None
    if weights:
        weight_list = [float(w) for w in weights.split(",")]

    rerank = engine.settings.scoring.rerank if with_rerank is None else with_rerank
    comp_weight = engine.settings.scoring.competence_weight if competence_weight is None else competence_weight
    graph = SearchGraph(
        repo=engine.repo,
        enricher=engine.enricher,
        reranker=engine.reranker if rerank else None,
        llm=engine.llm,
        section_multipliers=engine.settings.scoring.section_multipliers,
        alpha=engine.settings.scoring.alpha,
        beta=engine.settings.scoring.beta,
        competence_weight=comp_weight,
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
                "competence_weight": comp_weight,
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
    count: int = typer.Option(400, "--count", help="Number of synthetic CVs"),
    seed: int = typer.Option(42, "--seed", help="Random seed"),
    collection: str = typer.Option(None, "--collection", "-c", help="Target collection name"),
    manifest: Path = typer.Option(None, "--manifest", help="Where to write the ground-truth manifest"),
    reset: bool = typer.Option(False, "--reset", help="Drop the collection before ingesting"),
) -> None:
    """Generate consulting-firm synthetic CVs and ingest them into the __synth collection."""
    import json

    settings = Settings()
    target = collection or settings.chroma.synth_collection
    engine = _engine(target)
    if reset:
        engine.repo.reset()
        engine.repo = ChromaRepository(
            host=engine.settings.chroma.host,
            port=engine.settings.chroma.port,
            collection_name=target,
            provider=engine.embedding,
        )
    engine.ingestion = IngestionPipeline(repo=engine.repo, sectioner=HeadingSectioner())

    profiles = generate_profiles(count, seed=seed)
    with console.status(f"Ingesting {count} synthetic CVs..."):
        for profile in profiles:
            engine.ingestion.ingest_text(
                text=build_cv_text(profile),
                resource_id=profile.resource_id,
                extra_metadata=profile_metadata(profile),
            )

    manifest_path = manifest or Path(settings.data_dir) / "synth_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(build_manifest(profiles, seed=seed), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    console.print(f"Ingested {count} synthetic CVs into '{engine.repo.collection_name}'")
    console.print(f"Ground-truth manifest written to {manifest_path}")


@app.command("eval-rank")
def eval_rank(
    manifest: Path = typer.Option(None, "--manifest", help="Ground-truth manifest path"),
    collection: str = typer.Option(None, "--collection", "-c", help="Collection name"),
    top_k: int = typer.Option(10, "--top-k", help="Results per query"),
    with_rerank: bool = typer.Option(False, "--with-rerank", help="Enable the reranker"),
    competence_weight: float = typer.Option(None, "--competence-weight", help="Seniority boost weight (0=off)"),
    report: Path = typer.Option(None, "--report", help="Write a JSON report to this path"),
) -> None:
    """Verify that the ranking surfaces the most competent resources (NDCG@k / MRR)."""
    import json

    settings = Settings()
    comp_weight = settings.scoring.competence_weight if competence_weight is None else competence_weight
    manifest_path = manifest or Path(settings.data_dir) / "synth_manifest.json"
    if not manifest_path.exists():
        console.print(f"[red]Manifest not found: {manifest_path}. Run `cvengine synth` first.[/red]")
        raise typer.Exit(code=1)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    resources = data["resources"]
    level_rank = data["levels"]

    engine = _engine(collection or settings.chroma.synth_collection)
    graph = SearchGraph(
        repo=engine.repo,
        enricher=None,
        reranker=engine.reranker if with_rerank else None,
        section_multipliers=settings.scoring.section_multipliers,
        alpha=settings.scoring.alpha,
        beta=settings.scoring.beta,
        competence_weight=comp_weight,
        top_k_per_query=settings.scoring.top_k_per_query,
        rerank_top_n=settings.scoring.rerank_top_n,
    )

    # Group resources by their primary skill so we can build targeted queries.
    by_skill: dict[str, list[dict]] = {}
    for resource in resources:
        for skill in resource["primary_skills"]:
            by_skill.setdefault(skill, []).append(resource)

    ndcg_total = 0.0
    mrr_total = 0.0
    precision_total = 0.0
    queries = 0
    details: dict[str, dict] = {}

    for skill, candidates in by_skill.items():
        expected = sorted(candidates, key=lambda r: level_rank[r["level"]], reverse=True)
        relevant = {r["resource_id"] for r in candidates}
        state = graph.invoke({"skills": [skill], "top_k": top_k, "rerank": with_rerank})
        ranked_ids = [result.resource_id for result in state["results"]]

        gains = [
            level_rank[next((r["level"] for r in candidates if r["resource_id"] == rid), "low")] for rid in ranked_ids
        ]
        ndcg = ndcg_at_k(gains, k=top_k)
        ndcg_total += ndcg

        hit_rank = next((i + 1 for i, rid in enumerate(ranked_ids) if rid in relevant), None)
        if hit_rank:
            mrr_total += 1.0 / hit_rank
            precision_total += len([rid for rid in ranked_ids if rid in relevant]) / top_k
        queries += 1
        details[skill] = {
            "expected_top": expected[0]["resource_id"] if expected else None,
            "top_result": ranked_ids[0] if ranked_ids else None,
            "ndcg": round(ndcg, 4),
            "hit_rank": hit_rank,
        }

    summary = {
        "queries": queries,
        "ndcg_at_k": round(ndcg_total / queries, 4) if queries else 0.0,
        "mrr": round(mrr_total / queries, 4) if queries else 0.0,
        "precision_at_k": round(precision_total / queries, 4) if queries else 0.0,
        "top_k": top_k,
        "rerank": with_rerank,
        "competence_weight": comp_weight,
        "details": details,
    }
    console.print(f"Queries: {summary['queries']}")
    console.print(f"NDCG@{top_k}: {summary['ndcg_at_k']}")
    console.print(f"MRR: {summary['mrr']}")
    console.print(f"precision@{top_k}: {summary['precision_at_k']}")

    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
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
