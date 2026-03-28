from abc import ABC, abstractmethod
from random import uniform
from time import sleep

from src.job import Job
from src.logging import logger


class BaseCrawler(ABC):
    """Abstract base class for job crawlers."""

    def __init__(self, driver, config: dict):
        self.driver = driver
        self.config = config

    @abstractmethod
    def login(self) -> None:
        """Authenticate with the platform using cookies."""

    @abstractmethod
    def search_jobs(self, filters: dict) -> list[dict]:
        """Search for jobs. Return list of {id, url, role, company}."""

    @abstractmethod
    def scrape_job(self, job_url: str) -> Job:
        """Scrape full job details from a URL. Return populated Job."""

    def crawl(self, filters: dict) -> list[Job]:
        """Template method: search -> scrape all with rate limiting."""
        results = self.search_jobs(filters)
        max_jobs = self.config.get("max_jobs_per_run", 20)
        results = results[:max_jobs]
        logger.info(f"Found {len(results)} jobs (limit {max_jobs})")

        min_delay = self.config.get("min_delay", 2)
        max_delay = self.config.get("max_delay", 5)
        jobs = []
        for i, result in enumerate(results):
            logger.info(f"Scraping job {i+1}/{len(results)}: {result.get('role', 'unknown')}")
            try:
                job = self.scrape_job(result["url"])
                jobs.append(job)
            except Exception as e:
                logger.error(f"Failed to scrape {result['url']}: {e}")
            if i < len(results) - 1:
                delay = uniform(min_delay, max_delay)
                logger.debug(f"Waiting {delay:.1f}s before next request")
                sleep(delay)
        return jobs
