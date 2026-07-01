"""
Item CRUD endpoints (template — wire up a real DB session in production).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_active_user
from app.schemas.auth import MeResponse
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate

router = APIRouter(tags=["Items"])

# ── In-memory store ───────────────────────────────────────────────────────────
_items: dict[int, dict] = {}
_next_id = 1


def _get_or_404(item_id: int) -> dict:
    item = _items.get(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.get(
    "/items",
    response_model=PaginatedResponse[ItemResponse],
    summary="List all items",
)
async def list_items(
    page: int = 1,
    size: int = 20,
    _: MeResponse = Depends(get_active_user),
) -> PaginatedResponse[ItemResponse]:
    all_items = list(_items.values())
    total = len(all_items)
    start = (page - 1) * size
    end = start + size
    items = [ItemResponse(**i) for i in all_items[start:end]]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=max(1, -(-total // size)),
    )


@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item",
)
async def create_item(
    body: ItemCreate,
    current_user: MeResponse = Depends(get_active_user),
) -> ItemResponse:
    global _next_id
    item = {
        "id": _next_id,
        **body.model_dump(),
        "owner_id": current_user.id,
    }
    _items[_next_id] = item
    _next_id += 1
    return ItemResponse(**item)


@router.get("/items/{item_id}", response_model=ItemResponse, summary="Get item by ID")
async def get_item(
    item_id: int,
    _: MeResponse = Depends(get_active_user),
) -> ItemResponse:
    return ItemResponse(**_get_or_404(item_id))


@router.put("/items/{item_id}", response_model=ItemResponse, summary="Update an item")
async def update_item(
    item_id: int,
    body: ItemUpdate,
    _: MeResponse = Depends(get_active_user),
) -> ItemResponse:
    item = _get_or_404(item_id)
    item.update(body.model_dump(exclude_none=True))
    return ItemResponse(**item)


@router.delete("/items/{item_id}", response_model=MessageResponse, summary="Delete an item")
async def delete_item(
    item_id: int,
    _: MeResponse = Depends(get_active_user),
) -> MessageResponse:
    _get_or_404(item_id)
    del _items[item_id]
    return MessageResponse(message=f"Item {item_id} deleted.")
