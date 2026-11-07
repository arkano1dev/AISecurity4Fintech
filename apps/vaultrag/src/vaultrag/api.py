import hashlib
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from vaultrag.auth import TokenVerifier, require_auth
from vaultrag.chunker import chunk_text
from vaultrag.clients import AuditClient, Auditor, Masker, PiiClient
from vaultrag.embeddings import embed_texts
from vaultrag.llm import answer
from vaultrag.retriever import retrieve
from vaultrag.settings import settings
from vaultrag.store import Chunk, VectorStore


class DocumentRequest(BaseModel):
    doc_id: str
    title: str
    content: str = Field(..., min_length=1)


class IngestResponse(BaseModel):
    doc_id: str
    chunks: int


class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    text: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]


EmbedFn = Callable[[list[str]], list[list[float]]]
LlmFn = Callable[[str, list[str]], str]


def _default_embed(texts: list[str]) -> list[list[float]]:
    return embed_texts(texts)


def _default_llm(question: str, context: list[str]) -> str:
    return answer(question, context)


def make_app(
    *,
    store: VectorStore | None = None,
    pii_client: Masker | None = None,
    audit_client: Auditor | None = None,
    embed_fn: EmbedFn | None = None,
    llm_fn: LlmFn | None = None,
    verify_token_fn: TokenVerifier | None = None,
) -> FastAPI:
    """Build the VaultRAG app with injectable dependencies for testing.

    The flow is: chunk -> mask PII -> embed -> store on ingest; embed -> retrieve
    -> generate -> audit on query. Ingest requires the ``vaultrag:ingest`` scope,
    query requires ``vaultrag:query``; both are enforced on a verified JWT.
    """
    app = FastAPI(title="VaultRAG")
    store_obj = store if store is not None else VectorStore()
    pii = pii_client if pii_client is not None else PiiClient(settings.pii_proxy_url)
    audit = audit_client if audit_client is not None else AuditClient(settings.audit_log_url)
    embed = embed_fn if embed_fn is not None else _default_embed
    generate = llm_fn if llm_fn is not None else _default_llm

    @app.post("/vaultrag/documents", response_model=IngestResponse, status_code=201)
    def ingest(
        payload: DocumentRequest,
        _auth: Annotated[
            dict[str, Any],
            Depends(require_auth(["vaultrag:ingest"], verify_token_fn)),
        ],
    ) -> IngestResponse:
        chunks = chunk_text(payload.content, settings.chunk_size, settings.chunk_overlap)
        redacted = [pii.mask(chunk) for chunk in chunks]
        embeddings = embed(redacted)
        store_obj.add_document(payload.doc_id, payload.title)
        for index, (text, embedding) in enumerate(zip(redacted, embeddings, strict=True)):
            store_obj.add_chunk(
                Chunk(
                    chunk_id=f"{payload.doc_id}:{index}",
                    doc_id=payload.doc_id,
                    text=text,
                    embedding=embedding,
                    metadata={"title": payload.title, "index": index},
                )
            )
        return IngestResponse(doc_id=payload.doc_id, chunks=len(chunks))

    @app.post("/vaultrag/query", response_model=QueryResponse)
    def query(
        payload: QueryRequest,
        _auth: Annotated[
            dict[str, Any],
            Depends(require_auth(["vaultrag:query"], verify_token_fn)),
        ],
    ) -> QueryResponse:
        if not store_obj.chunks():
            raise HTTPException(status_code=409, detail="no documents indexed")
        masked_question = pii.mask(payload.question)
        question_embedding = embed([masked_question])[0]
        hits = retrieve(store_obj.chunks(), question_embedding, settings.top_k)
        context = [chunk.text for _, chunk in hits]
        answer_text = generate(masked_question, context)
        citations = [
            Citation(doc_id=chunk.doc_id, chunk_id=chunk.chunk_id, text=chunk.text)
            for _, chunk in hits
        ]
        audit.append(
            actor_sub="analyst",
            action="vaultrag.query",
            payload={
                "question_hash": _sha256(masked_question),
                "retrieved_ids": [chunk.chunk_id for _, chunk in hits],
                "answer_hash": _sha256(answer_text),
            },
        )
        return QueryResponse(answer=answer_text, citations=citations)

    return app


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
