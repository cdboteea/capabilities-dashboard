import json
from typing import Any, Dict, List
from uuid import UUID, uuid4

import asyncpg

from ..config import settings
from ..models.sentiment_models import SentimentResult


class Database:
    """AsyncPG helper for sentiment_scores table interactions."""

    def __init__(self):
        self._pool: asyncpg.Pool | None = None

    async def connect(self):
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=settings.pool_min_size,
                max_size=settings.pool_max_size,
            )

    async def close(self):
        if self._pool:
            await self._pool.close()

    async def save_sentiment(self, event_id: str, sentiment: SentimentResult) -> UUID:
        if self._pool is None:
            raise RuntimeError("Database pool not initialized")
        sentiment_id = uuid4()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sentiment_scores (id, event_id, overall_sentiment, confidence_score, sentiments_json)
                VALUES ($1, $2, $3, $4, $5)
                """,
                sentiment_id,
                event_id,
                sentiment.overall.score,
                sentiment.overall.confidence,
                json.dumps(sentiment.model_dump(mode="json")),
            )
        return sentiment_id

    async def get_sentiment(self, event_id: str) -> List[Dict[str, Any]]:
        if self._pool is None:
            raise RuntimeError("Database pool not initialized")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM sentiment_scores WHERE event_id=$1 ORDER BY analyzed_at DESC LIMIT 10",
                event_id,
            )
            return [dict(r) for r in rows]


db = Database() 