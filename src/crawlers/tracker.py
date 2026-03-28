from datetime import datetime, timezone

import redis

from src.logging import logger

SEEN_SET_KEY = "seen_jobs"


class Tracker:
    """Tracks seen jobs in Redis to avoid reprocessing across runs."""

    def __init__(self, client: redis.Redis):
        self.r = client
        # Verify connection
        self.r.ping()
        logger.debug("Redis tracker connected")

    def filter_unseen(self, results: list[dict]) -> list[dict]:
        if not results:
            return []
        pipe = self.r.pipeline()
        for result in results:
            pipe.sismember(SEEN_SET_KEY, result["id"])
        seen_flags = pipe.execute()
        return [r for r, seen in zip(results, seen_flags) if not seen]

    def mark_seen(self, job_id: str, url: str, role: str = "", company: str = "",
                  location: str = "", description: str = "", source: str = ""):
        pipe = self.r.pipeline()
        pipe.sadd(SEEN_SET_KEY, job_id)
        pipe.hset(f"job:{job_id}", mapping={
            "url": url,
            "role": role,
            "company": company,
            "location": location,
            "description": description[:500] if description else "",
            "source": source,
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        })
        pipe.execute()
