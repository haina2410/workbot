from datetime import datetime, timezone

from fastapi import FastAPI, Header
from pydantic import BaseModel

from src.logging import logger
from src.runner import crawl_jobs, _jobs_to_dict, _write_run_output
from pathlib import Path

app = FastAPI(title="Jobs Applier Crawler API")

# Sample data for test mode
_MOCK_JOBS = [
    {
        "job_id": "facebook_test_001",
        "role": "Software Engineer",
        "company": "Test Corp",
        "location": "Ho Chi Minh",
        "link": "",
        "description": "This is a test job posting for validating the n8n workflow.",
        "source": "facebook",
        "raw_post": "Tuyển dụng Software Engineer tại Test Corp, HCM. Yêu cầu: 3 năm kinh nghiệm Python.",
    },
    {
        "job_id": "linkedin_test_002",
        "role": "Backend Developer",
        "company": "Demo Inc",
        "location": "Remote",
        "link": "https://linkedin.com/jobs/view/test",
        "description": "Backend role, Python/FastAPI, remote friendly.",
        "source": "linkedin",
        "raw_post": "",
    },
]


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
    raw_post: str


class CrawlResponse(BaseModel):
    crawled_at: str
    total_jobs: int
    jobs: list[JobOut]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/crawl")
def crawl(request: CrawlRequest = CrawlRequest(), x_test: str | None = Header(None)):
    if x_test:
        logger.info("API /crawl called in TEST mode — returning mock data")
        return {
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "total_jobs": len(_MOCK_JOBS),
            "jobs": _MOCK_JOBS,
        }

    logger.info(f"API /crawl called with sources={request.sources}")
    sources = request.sources if request.sources else None

    jobs = crawl_jobs(sources=sources)
    now = datetime.now(timezone.utc)

    # Write local backup
    _write_run_output(jobs, Path("data/output"))

    result = _jobs_to_dict(jobs, now)
    logger.info(f"API /crawl returning {len(jobs)} jobs")
    return result
