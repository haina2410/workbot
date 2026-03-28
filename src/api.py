from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

from src.logging import logger
from src.runner import crawl_jobs, _jobs_to_dict, _write_run_output
from pathlib import Path

app = FastAPI(title="Jobs Applier Crawler API")


class CrawlRequest(BaseModel):
    sources: list[str] = []


class JobOut(BaseModel):
    job_id: str
    role: str
    company: str
    location: str
    link: str
    description: str
    source: str


class CrawlResponse(BaseModel):
    crawled_at: str
    total_jobs: int
    jobs: list[JobOut]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/crawl", response_model=CrawlResponse)
def crawl(request: CrawlRequest = CrawlRequest()):
    logger.info(f"API /crawl called with sources={request.sources}")
    sources = request.sources if request.sources else None

    jobs = crawl_jobs(sources=sources)
    now = datetime.now(timezone.utc)

    # Write local backup
    _write_run_output(jobs, Path("data/output"))

    result = _jobs_to_dict(jobs, now)
    logger.info(f"API /crawl returning {len(jobs)} jobs")
    return result
