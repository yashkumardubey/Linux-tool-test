"""Notifications API — manage alert channels and send notifications."""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user, require_role
from models.db_models import NotificationChannel, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# --- Schemas ---
class ChannelCreate(BaseModel):
    name: str
    channel_type: str  # email, slack, webhook, telegram
    config: dict  # type-specific: {"url": ...} or {"email": ..., "smtp_host": ...}
    events: list[str] = ["job_failed", "cve_critical"]  # events to subscribe
    is_enabled: bool = True


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    events: Optional[list[str]] = None
    is_enabled: Optional[bool] = None


# --- CRUD ---
@router.get("/channels")
async def list_channels(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(NotificationChannel).order_by(NotificationChannel.name))
    channels = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "channel_type": c.channel_type,
            "config": c.config,
            "events": c.events,
            "is_enabled": c.is_enabled,
            "created_at": c.created_at.isoformat(),
        }
        for c in channels
    ]


@router.post("/channels", status_code=201)
async def create_channel(
    data: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    valid_types = {"email", "slack", "webhook", "telegram"}
    if data.channel_type not in valid_types:
        raise HTTPException(400, f"channel_type must be one of {valid_types}")
    ch = NotificationChannel(
        name=data.name,
        channel_type=data.channel_type,
        config=data.config,
        events=data.events,
        is_enabled=data.is_enabled,
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return {"id": ch.id, "name": ch.name}


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: int,
    data: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    ch = await db.get(NotificationChannel, channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(ch, field, val)
    await db.commit()
    return {"status": "updated"}


@router.delete("/channels/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    ch = await db.get(NotificationChannel, channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    await db.delete(ch)
    await db.commit()


@router.post("/test/{channel_id}")
async def test_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """Send a test notification through the channel."""
    ch = await db.get(NotificationChannel, channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    try:
        await _send_notification(ch, "Test Notification", "This is a test from PatchMaster.")
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(500, f"Send failed: {str(e)}")


# --- Notification dispatch helper (called from other modules) ---
async def send_event_notification(db: AsyncSession, event: str, title: str, message: str):
    """Send notification to all channels subscribed to this event."""
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.is_enabled == True)
    )
    channels = result.scalars().all()
    for ch in channels:
        if event in (ch.events or []):
            try:
                await _send_notification(ch, title, message)
            except Exception:
                logger.exception(f"Failed to send notification via {ch.name}")


async def _send_notification(channel: NotificationChannel, title: str, message: str):
    """Dispatch notification based on channel type."""
    import httpx

    if channel.channel_type == "webhook":
        url = channel.config.get("url", "")
        if not url:
            raise ValueError("Webhook URL not configured")
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"title": title, "message": message})

    elif channel.channel_type == "slack":
        webhook_url = channel.config.get("webhook_url", "")
        if not webhook_url:
            raise ValueError("Slack webhook URL not configured")
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(webhook_url, json={"text": f"*{title}*\n{message}"})

    elif channel.channel_type == "telegram":
        bot_token = channel.config.get("bot_token", "")
        chat_id = channel.config.get("chat_id", "")
        if not bot_token or not chat_id:
            raise ValueError("Telegram bot_token and chat_id required")
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"chat_id": chat_id, "text": f"{title}\n{message}", "parse_mode": "HTML"})

    elif channel.channel_type == "email":
        # Email requires SMTP — log for now, implement with aiosmtplib if needed
        logger.info(f"EMAIL notification to {channel.config.get('to')}: {title} — {message}")

    else:
        raise ValueError(f"Unknown channel type: {channel.channel_type}")
