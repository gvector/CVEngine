"""Simple read-only web viewer for the Chroma collections.

Served under ``/viewer`` by the FastAPI app when ``viewer_enabled`` is on. No
writes are exposed: only collection listing, chunk browsing and a query box
(embedded client-side with the configured embedding provider).
"""

from __future__ import annotations

from typing import Any

import chromadb
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from cvengine.embeddings.provider import EmbeddingProvider

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CVEngine - Chroma Viewer</title>
<style>
  body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 24px; color: #222; background: #f7f8fa; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 14px 0; }
  select, input, button { padding: 6px 10px; font-size: 13px; border: 1px solid #ccc; border-radius: 6px; }
  button { background: #2563eb; color: #fff; border: none; cursor: pointer; }
  button.secondary { background: #64748b; }
  table { border-collapse: collapse; width: 100%; background: #fff; font-size: 12px; }
  th, td { border: 1px solid #e2e8f0; padding: 6px 8px; text-align: left; vertical-align: top; }
  th { background: #f1f5f9; position: sticky; top: 0; }
  td.id { font-family: ui-monospace, monospace; font-size: 11px; }
  td.doc { max-width: 420px; white-space: pre-wrap; }
  pre.meta { margin: 0; font-size: 10px; color: #475569; }
  .chip { background: #eef2ff; color: #3730a3; border-radius: 10px; padding: 1px 7px; font-size: 11px; margin-right: 4px; }
  .status { color: #6b7280; font-size: 12px; margin: 8px 0; }
  .err { color: #b91c1c; }
  #counts { font-size: 12px; color: #475569; margin-left: 8px; }
</style>
</head>
<body>
<h1>CVEngine — Chroma Viewer</h1>
<div class="controls">
  <label>Collection <select id="collection"></select></label>
  <label>Limit <input id="limit" type="number" value="20" min="1" max="500" style="width:70px"></label>
  <label>Resource <input id="resource" placeholder="optional resource_id" style="width:200px"></label>
  <button id="browse">Browse</button>
  <label>Query <input id="query" placeholder="embedding query" style="width:220px"></label>
  <label>n <input id="n" type="number" value="10" min="1" max="100" style="width:60px"></label>
  <button id="runQuery" class="secondary">Search</button>
  <button id="reload">Reload</button>
</div>
<div id="counts"></div>
<div id="status" class="status"></div>
<table id="table">
  <thead><tr><th>#</th><th>id</th><th>resource</th><th>section</th><th>keywords</th><th>score</th><th>document</th><th>metadata</th></tr></thead>
  <tbody></tbody>
</table>
<script>
const $ = (id) => document.getElementById(id);
const status = (msg, err) => { $("status").textContent = msg; $("status").className = "status" + (err ? " err" : ""); };
async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error((await res.text()).slice(0, 200));
  return res.json();
}
async function loadCollections() {
  const cols = await api("/viewer/api/collections");
  const sel = $("collection");
  sel.innerHTML = cols.map(c => `<option value="${c.name}">${c.name} (${c.count})</option>`).join("");
  $("counts").textContent = `${cols.length} collection(s)`;
}
function renderChunks(items) {
  const tb = $("table").querySelector("tbody");
  tb.innerHTML = items.map((it, i) => `
    <tr>
      <td>${i + 1}</td>
      <td class="id">${it.id}</td>
      <td>${it.resource_id ?? ""}</td>
      <td>${it.section ?? ""}</td>
      <td>${(it.keywords ?? []).map(k => `<span class="chip">${k}</span>`).join("")}</td>
      <td>${it.score ?? ""}</td>
      <td class="doc">${escapeHtml((it.document ?? "").slice(0, 600))}</td>
      <td><pre class="meta">${escapeHtml(JSON.stringify(it.metadata ?? {}, null, 1).slice(0, 400))}</pre></td>
    </tr>`).join("");
}
function escapeHtml(s) { return s.replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
$("browse").addEventListener("click", async () => {
  try {
    status("Loading...");
    const q = new URLSearchParams({ collection: $("collection").value, limit: $("limit").value });
    if ($("resource").value.trim()) q.set("resource_id", $("resource").value.trim());
    const data = await api("/viewer/api/chunks?" + q);
    renderChunks(data);
    status(`${data.length} chunk(s)`);
  } catch (e) { status("Error: " + e.message, true); }
});
$("runQuery").addEventListener("click", async () => {
  try {
    status("Searching...");
    const data = await api("/viewer/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collection: $("collection").value, query_text: $("query").value, n_results: parseInt($("n").value) }),
    });
    renderChunks(data);
    status(`${data.length} result(s)`);
  } catch (e) { status("Error: " + e.message, true); }
});
$("reload").addEventListener("click", loadCollections);
loadCollections().catch(e => status("Error: " + e.message, true));
</script>
</body>
</html>
"""


class QueryRequest(BaseModel):
    collection: str
    query_text: str = Field(min_length=1)
    n_results: int = Field(default=10, ge=1, le=100)


class ChromaBrowser:
    """Read-only access to Chroma collections (browse + client-side embedding query)."""

    def __init__(self, host: str, port: int, provider: EmbeddingProvider) -> None:
        self._client = chromadb.HttpClient(host=host, port=port)
        self._provider = provider

    def list_collections(self) -> list[dict[str, Any]]:
        return [{"name": col.name, "count": col.count()} for col in self._client.list_collections()]

    def get_chunks(self, collection: str, limit: int = 20, resource_id: str | None = None) -> list[dict[str, Any]]:
        col = self._client.get_collection(collection)
        where = {"resource_id": resource_id} if resource_id else None
        data = col.get(limit=limit, where=where, include=["documents", "metadatas"])
        return [
            {
                "id": chunk_id,
                "resource_id": meta.get("resource_id") if meta else None,
                "section": meta.get("section") if meta else None,
                "keywords": _load_keywords(meta),
                "document": doc,
                "metadata": meta,
            }
            for chunk_id, doc, meta in zip(data["ids"], data["documents"], data["metadatas"], strict=True)
        ]

    def query(self, collection: str, query_text: str, n_results: int) -> list[dict[str, Any]]:
        col = self._client.get_collection(collection)
        embedding = self._provider.embed_query(query_text)
        data = col.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "id": chunk_id,
                "score": round(1.0 - float(distance), 4),
                "resource_id": meta.get("resource_id") if meta else None,
                "section": meta.get("section") if meta else None,
                "keywords": _load_keywords(meta),
                "document": doc,
                "metadata": meta,
            }
            for chunk_id, doc, meta, distance in zip(
                data["ids"][0], data["documents"][0], data["metadatas"][0], data["distances"][0], strict=True
            )
        ]


def _load_keywords(meta: dict[str, Any] | None) -> list[str]:
    import json

    if not meta:
        return []
    raw = meta.get("keywords", "[]")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []
    return raw


def build_viewer_router(browser: ChromaBrowser) -> APIRouter:
    """Build the /viewer router bound to a ChromaBrowser instance."""
    router = APIRouter(prefix="/viewer")

    @router.get("", response_class=HTMLResponse)
    def index() -> str:
        return _HTML

    @router.get("/api/collections")
    def collections() -> list[dict[str, Any]]:
        return browser.list_collections()

    @router.get("/api/chunks")
    def chunks(collection: str, limit: int = 20, resource_id: str | None = None) -> list[dict[str, Any]]:
        try:
            return browser.get_chunks(collection, limit=min(limit, 500), resource_id=resource_id)
        except Exception as exc:  # noqa: BLE001 - surface as HTTP error
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/api/query")
    def query(request: QueryRequest) -> list[dict[str, Any]]:
        try:
            return browser.query(request.collection, request.query_text, request.n_results)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return router
