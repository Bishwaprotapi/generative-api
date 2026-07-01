"""
Text embedding endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_llm_service
from app.schemas.chat import EmbeddingRequest, EmbeddingResponse
from app.services.llm_service import LLMService

router = APIRouter(tags=["Embeddings"])


@router.post("/embeddings", response_model=EmbeddingResponse, summary="Generate embeddings")
async def embeddings(
    body: EmbeddingRequest,
    llm: LLMService = Depends(get_llm_service),
) -> EmbeddingResponse:
    return await llm.embeddings(
        input_text=body.input,
        provider=body.provider,
        model=body.model,
    )
