"""Simple X API client (manual fetch, quota-aware)"""
from __future__ import annotations

import os
import aiohttp
from datetime import datetime
from typing import Any, Dict, Optional

from .database import DatabaseManager

class QuotaExceededError(Exception):
    pass

class SimpleXAPIClient:
    """Minimal async client for X (Twitter) API v2."""

    BASE_URL = "https://api.twitter.com/2"

    def __init__(self, bearer_token: str, db: DatabaseManager):
        if not bearer_token:
            raise ValueError("X_BEARER_TOKEN not provided")
        self._token = bearer_token
        self._db = db
        self._session: Optional[aiohttp.ClientSession] = None

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    async def get_usage(self) -> Dict[str, Any]:
        """Return dict with calls_used, calls_limit, month (YYYY-MM)."""
        month = datetime.utcnow().strftime("%Y-%m")
        query = "SELECT calls_used, calls_limit FROM idea_database.x_api_usage WHERE month = $1"
        async with self._db.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, month)
            if row:
                return {"month": month, "calls_used": row[0], "calls_limit": row[1]}
            # first time this month -> insert
            await conn.execute(
                "INSERT INTO idea_database.x_api_usage (month, calls_used) VALUES ($1, 0)",
                month,
            )
            return {"month": month, "calls_used": 0, "calls_limit": 100}

    # ------------------------------------------------------------------
    async def fetch_tweet(self, tweet_id: str) -> Dict[str, Any]:
        """Fetch a single tweet with author & media expansions."""
        await self._ensure_quota()
        params = {
            "expansions": "author_id,attachments.media_keys",
            "tweet.fields": "created_at,lang,conversation_id,public_metrics,attachments",
            "user.fields": "username,name,profile_image_url,verified",
            "media.fields": "url,preview_image_url,width,height,duration_ms,type,variants"
        }
        url = f"{self.BASE_URL}/tweets/{tweet_id}"
        headers = {"Authorization": f"Bearer {self._token}"}
        if not self._session:
            self._session = aiohttp.ClientSession()
        async with self._session.get(url, headers=headers, params=params, timeout=15) as resp:
            if resp.status == 429:
                raise QuotaExceededError("X API rate limit hit (per-15min)")
            if resp.status == 404:
                raise ValueError("Tweet not found or not public")
            resp.raise_for_status()
            data = await resp.json()
        await self._increment_usage()
        return data

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _ensure_quota(self):
        usage = await self.get_usage()
        if usage["calls_used"] >= usage["calls_limit"]:
            raise QuotaExceededError("Monthly X API quota exhausted")

    async def _increment_usage(self):
        month = datetime.utcnow().strftime("%Y-%m")
        query = "UPDATE idea_database.x_api_usage SET calls_used = calls_used + 1, updated_at = now() WHERE month = $1"
        async with self._db.connection_pool.acquire() as conn:
            await conn.execute(query, month) 