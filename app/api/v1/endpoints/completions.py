"""
Text completion endpoints (non-chat, single-prompt interface).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_cache_service, get_llm_service
from app.core.config import settings
from app.schemas.chat import CompletionRequest, CompletionResponse
from app.services.cache_service import CacheService
from app.services.llm_service import LLMService

router = APIRouter(tags=["Completions"])


@router.post("/completion", response_model=CompletionResponse, summary="Text completion")
async def completion(
    body: CompletionRequest,
    llm: LLMService = Depends(get_llm_service),
    cache: CacheService = Depends(get_cache_service),
) -> CompletionResponse:
    cached = await cache.get_llm(
        provider=body.provider or settings.DEFAULT_PROVIDER,
        model=body.model or "",
        prompt=body.prompt,
    )
    if cached:
        return CompletionResponse(
            id="cached",
            provider=body.provider or settings.DEFAULT_PROVIDER,
            model=body.model or "",
            text=cached,
        )

    result = await llm.completion(
        prompt=body.prompt,
        provider=body.provider,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )

    await cache.set_llm(
        provider=result.provider,
        model=result.model,
        prompt=body.prompt,
        value=result.text,
    )

    return result


@router.post("/completion/stream", summary="Streaming text completion")
async def completion_stream(
    body: CompletionRequest,
    llm: LLMService = Depends(get_llm_service),
) -> StreamingResponse:
    if not settings.ENABLE_STREAMING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming is disabled on this server.",
        )

    async def event_generator():
        async for chunk in llm.completion_stream(
            prompt=body.prompt,
            provider=body.provider,
            model=body.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
