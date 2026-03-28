import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import undetected_chromedriver as uc
import yaml

from src.logging import logger
from src.llm import LLMClient
from src.crawlers.config import CrawlerConfig
from src.crawlers.linkedin import LinkedInCrawler
from src.crawlers.facebook import FacebookCrawler


def init_crawler_browser(headless: bool = True) -> uc.Chrome:
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1200,800")
    options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    try:
        driver = uc.Chrome(options=options, headless=headless, version_main=146)
        logger.debug("Undetected Chrome browser initialized for crawling.")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize crawler browser: {e}")
        raise RuntimeError(f"Failed to initialize crawler browser: {e}")


def _load_secrets(secrets_path: Path) -> dict:
    with open(secrets_path, "r") as f:
        return yaml.safe_load(f)


def _write_run_output(jobs: list, output_dir: Path) -> Path:
    """Write per-run JSON output file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    filename = f"jobs_{now.strftime('%Y-%m-%d_%H%M%S')}.json"
    output_path = output_dir / filename

    output_data = _jobs_to_dict(jobs, now)
    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
    logger.info(f"Wrote {len(jobs)} jobs to {output_path}")
    return output_path


def _jobs_to_dict(jobs: list, crawled_at: datetime | None = None) -> dict:
    """Convert jobs list to serializable dict."""
    if crawled_at is None:
        crawled_at = datetime.now(timezone.utc)
    return {
        "crawled_at": crawled_at.isoformat(),
        "total_jobs": len(jobs),
        "jobs": [
            {
                "job_id": _generate_job_id(j),
                "role": j.role,
                "company": j.company,
                "location": j.location,
                "link": j.link,
                "description": j.description,
                "source": j.source,
            }
            for j in jobs
        ],
    }


def _generate_job_id(job) -> str:
    """Generate a stable ID for a job."""
    import hashlib
    key = f"{job.source}_{job.role}_{job.company}_{job.description[:100]}"
    return f"{job.source}_{hashlib.md5(key.encode()).hexdigest()[:16]}"


def crawl_jobs(data_folder: str = "data", sources: list[str] | None = None) -> list:
    """Run crawlers and return list of Job objects.

    Args:
        data_folder: Path to data directory with config.yaml and secrets.yaml.
        sources: List of crawler names to run (e.g. ["facebook", "linkedin"]).
                 None or empty = use enabled_crawlers from config.
    """
    from src.job import Job

    data_path = Path(data_folder)

    config = CrawlerConfig.load(data_path / "config.yaml")
    secrets = _load_secrets(data_path / "secrets.yaml")
    llm_api_key = secrets.get("llm_api_key", "")

    crawlers_to_run = sources if sources else config.enabled_crawlers

    crawl_driver = init_crawler_browser(headless=False)

    all_jobs: list[Job] = []
    try:
        for crawler_name in crawlers_to_run:
            if crawler_name == "linkedin":
                li_cookies = secrets.get("linkedin_cookies", {})
                if not li_cookies.get("li_at"):
                    logger.error("Missing linkedin_cookies.li_at in secrets.yaml, skipping LinkedIn")
                    continue

                crawler_config = {
                    **config.linkedin,
                    "min_delay": config.rate_limiting.get("min_delay", 2),
                    "max_delay": config.rate_limiting.get("max_delay", 5),
                }
                crawler = LinkedInCrawler(crawl_driver, crawler_config, cookies=li_cookies)

                try:
                    crawler.login()
                    jobs = crawler.crawl(config.linkedin.get("filters", {}))
                    all_jobs.extend(jobs)
                    logger.info(f"LinkedIn: found {len(jobs)} jobs")
                except Exception as e:
                    logger.error(f"LinkedIn crawler failed: {e}")

            elif crawler_name == "facebook":
                fb_config = config.facebook
                cookies_file = secrets.get("facebook_cookies_file", "facebook_cookies.json")
                cookies_path = data_path / cookies_file
                if not cookies_path.exists():
                    logger.error(f"Facebook cookies file not found: {cookies_path}, skipping")
                    continue
                try:
                    fb_cookies = json.loads(cookies_path.read_text())
                    if isinstance(fb_cookies, dict) and "cookies" in fb_cookies:
                        fb_cookies = fb_cookies["cookies"]
                except (json.JSONDecodeError, OSError) as e:
                    logger.error(f"Failed to load Facebook cookies: {e}, skipping")
                    continue

                crawler_config = {
                    **fb_config,
                    "min_delay": config.rate_limiting.get("min_delay", 2),
                    "max_delay": config.rate_limiting.get("max_delay", 5),
                }

                llm = LLMClient(
                    api_key=llm_api_key,
                    model=config.llm.get("model", "gpt-4o-mini"),
                    base_url=config.llm.get("base_url"),
                )

                fb_driver = init_crawler_browser(headless=False)
                try:
                    crawler = FacebookCrawler(
                        fb_driver, crawler_config,
                        cookies=fb_cookies, llm=llm,
                    )
                    crawler.login()
                    jobs = crawler.crawl(fb_config)
                    all_jobs.extend(jobs)
                    logger.info(f"Facebook: found {len(jobs)} jobs")
                except Exception as e:
                    logger.error(f"Facebook crawler failed: {e}")
                finally:
                    fb_driver.quit()
            else:
                logger.warning(f"Unknown crawler: {crawler_name}, skipping")
    finally:
        crawl_driver.quit()

    return all_jobs


def run(data_folder: str = "data"):
    """CLI entry point: crawl and write per-run JSON output."""
    jobs = crawl_jobs(data_folder)

    if not jobs:
        logger.info("No jobs found. Done.")
        return

    output_path = _write_run_output(jobs, Path(data_folder) / "output")
    logger.info(f"Done. {len(jobs)} jobs crawled and saved to {output_path}")


if __name__ == "__main__":
    run()
