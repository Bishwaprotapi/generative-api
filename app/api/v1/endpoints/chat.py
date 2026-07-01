"""
Chat and streaming chat endpoints.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_cache_service, get_llm_service, get_prompt_service
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage
from app.services.cache_service import CacheService
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse, summary="Single-shot chat completion")
async def chat(
    body: ChatRequest,
    llm: LLMService = Depends(get_llm_service),
    prompts: PromptService = Depends(get_prompt_service),
    cache: CacheService = Depends(get_cache_service),
) -> ChatResponse:
    messages = list(body.messages)

    # Optionally prepend a YAML prompt template as system message
    if body.prompt_name:
        try:
            system_text, rendered = prompts.render(
                body.prompt_name, body.prompt_vars or {}
            )
            if system_text:
                messages.insert(0, ChatMessage(role="system", content=system_text))
            messages.append(ChatMessage(role="user", content=rendered))
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Cache read
    cache_prompt = json.dumps([m.model_dump() for m in messages], sort_keys=True)
    cached = await cache.get_llm(
        provider=body.provider or settings.DEFAULT_PROVIDER,
        model=body.model or "",
        prompt=cache_prompt,
    )
    if cached:
        return ChatResponse(
            id="cached",
            provider=body.provider or settings.DEFAULT_PROVIDER,
            model=body.model or "",
            content=cached,
        )

    result = await llm.chat(
        messages=messages,
        provider=body.provider,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )

    # Cache write
    await cache.set_llm(
        provider=result.provider,
        model=result.model,
        prompt=cache_prompt,
        value=result.content,
    )

    return result


@router.post("/chat/stream", summary="Streaming chat completion")
async def chat_stream(
    body: ChatRequest,
    llm: LLMService = Depends(get_llm_service),
    prompts: PromptService = Depends(get_prompt_service),
) -> StreamingResponse:
    if not settings.ENABLE_STREAMING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming is disabled on this server.",
        )

    messages = list(body.messages)

    if body.prompt_name:
        try:
            system_text, rendered = prompts.render(
                body.prompt_name, body.prompt_vars or {}
            )
            if system_text:
                messages.insert(0, ChatMessage(role="system", content=system_text))
            messages.append(ChatMessage(role="user", content=rendered))
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    async def event_generator():
        async for chunk in llm.chat_stream(
            messages=messages,
            provider=body.provider,
            model=body.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
