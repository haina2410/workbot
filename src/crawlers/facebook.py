import hashlib
import json
import re
import time

from selenium.webdriver.common.by import By

from src.job import Job
from src.logging import logger
from src.llm import LLMClient
from src.crawlers.base import BaseCrawler

# Regex patterns that indicate a job posting (case-insensitive)
JOB_PATTERNS = [
    r"tuy[ểể]n\s*d[ụu]ng",        # tuyển dụng
    r"c[ầa]n\s*tuy[ểể]n",          # cần tuyển
    r"hiring",
    r"we.re\s+looking\s+for",
    r"job\s+opening",
    r"v[ịi]\s*tr[íi]\s*:",          # vị trí:
    r"m[ứu]c\s*l[ưu][ơo]ng",       # mức lương
    r"y[êe]u\s*c[ầa]u\s*:",        # yêu cầu:
    r"quy[ềe]n\s*l[ợo]i",          # quyền lợi
    r"kinh\s*nghi[ệe]m",           # kinh nghiệm
    r"salary",
    r"requirements?\s*:",
    r"apply\s+(now|here|at)",
    r"join\s+our\s+team",
    r"remote.*(position|role|job)",
    r"full[- ]?time|part[- ]?time|contract",
]

_JOB_REGEX = re.compile("|".join(JOB_PATTERNS), re.IGNORECASE)


class FacebookCrawler(BaseCrawler):
    """Crawls Facebook group posts via www.facebook.com with scroll-based pagination."""

    BASE_URL = "https://www.facebook.com"

    def __init__(self, driver, config: dict, cookies: list, llm: LLMClient | None = None):
        super().__init__(driver, config)
        self.cookies = cookies
        self.llm = llm
        self.use_llm = config.get("use_llm", True)
        self._post_cache: dict[str, dict] = {}  # {post_id: {"text": ..., "url": ...}}

    @staticmethod
    def _normalize_url(url: str) -> str:
        return re.sub(r"https://(m\.|mbasic\.)?facebook\.com", "https://www.facebook.com", url)

    @staticmethod
    def _generate_post_id(text: str) -> str:
        return "facebook_" + hashlib.md5(text.encode()).hexdigest()[:16]

    @staticmethod
    def _regex_filter_job_posts(posts: list[dict]) -> list[dict]:
        """Fast regex pre-filter: keep posts that match job-related patterns."""
        matched = [p for p in posts if _JOB_REGEX.search(p["text"])]
        logger.info(f"Regex filter: {len(matched)}/{len(posts)} posts match job patterns")
        return matched

    def login(self) -> None:
        logger.info("Logging into Facebook via cookies...")
        self.driver.get(self.BASE_URL)
        time.sleep(2)

        for cookie in self.cookies:
            clean = {k: v for k, v in cookie.items() if k in ("name", "value", "domain", "path", "secure", "httpOnly")}
            if "domain" not in clean:
                clean["domain"] = ".facebook.com"
            try:
                self.driver.add_cookie(clean)
            except Exception as e:
                logger.debug(f"Failed to add cookie {clean.get('name')}: {e}")

        self.driver.get(f"{self.BASE_URL}/me")
        time.sleep(3)

        current_url = self.driver.current_url
        page_source = self.driver.page_source
        if "/login" in current_url or "login_form" in page_source:
            raise RuntimeError(
                "Facebook login failed — cookies may be expired. "
                "Please re-export your Facebook cookies."
            )
        logger.info(f"Facebook login successful (URL: {current_url})")

    def search_jobs(self, filters: dict) -> list[dict]:
        group_urls = self.config.get("group_urls", [])
        target_posts = self.config.get("target_posts", 25)
        max_pages = self.config.get("max_pages", 10)
        filter_remote = self.config.get("filter_remote_only", False)

        all_posts = []
        for group_url in group_urls:
            normalized_url = self._normalize_url(group_url)
            posts = self._crawl_group_posts(normalized_url, target_posts, max_pages)
            all_posts.extend(posts)
            logger.info(f"Crawled {len(posts)} posts from {group_url}")

        if not all_posts:
            return []

        # Step 1: regex pre-filter (always runs)
        job_posts = self._regex_filter_job_posts(all_posts)

        # Step 2: LLM classification (optional)
        if self.use_llm and self.llm and job_posts:
            job_posts = self._llm_classify_job_posts(job_posts)
            logger.info(f"LLM classified {len(job_posts)} posts as job listings")

            if filter_remote and job_posts:
                job_posts = self._llm_filter_remote(job_posts)
                logger.info(f"After remote filter: {len(job_posts)} posts")

        results = []
        for post in job_posts:
            post_id = self._generate_post_id(post["text"])
            post_url = post.get("post_url", "") or post.get("group_url", "")
            self._post_cache[post_id] = {"text": post["text"], "url": post_url}
            results.append({
                "id": post_id,
                "url": post_url,
                "role": "",
                "company": "",
            })
        return results

    def scrape_job(self, job_url: str) -> Job:
        job_id = job_url
        cached = self._post_cache.get(job_id)
        if not cached:
            logger.warning(f"No cached post text for {job_id}")
            return Job(source="facebook")

        post_text = cached["text"]
        link = cached["url"]

        if self.use_llm and self.llm:
            fields = self._llm_extract_job_fields(post_text)
            return Job(
                role=fields.get("role", ""),
                company=fields.get("company", ""),
                location=fields.get("location", ""),
                description=fields.get("description", post_text),
                link=link,
                source="facebook",
                raw_post=post_text,
            )
        else:
            return Job(
                description=post_text,
                link=link,
                source="facebook",
                raw_post=post_text,
            )

    def crawl(self, filters: dict) -> list[Job]:
        """Override to pass job_id as url for scrape_job lookup."""
        results = self.search_jobs(filters)
        max_jobs = self.config.get("max_jobs_per_run", 20)
        results = results[:max_jobs]
        logger.info(f"Found {len(results)} jobs (limit {max_jobs})")

        jobs = []
        for i, result in enumerate(results):
            logger.info(f"Extracting job {i+1}/{len(results)}")
            try:
                job = self.scrape_job(result["id"])
                jobs.append(job)
            except Exception as e:
                logger.error(f"Failed to extract job from post: {e}")
        return jobs

    def _crawl_group_posts(self, group_url: str, target_posts: int, max_scrolls: int) -> list[dict]:
        posts = []
        seen_texts = set()
        stagnant_rounds = 0

        logger.info(f"Crawling group: {group_url}")
        self.driver.get(group_url)
        time.sleep(5)

        self._expand_all_posts()

        for scroll in range(max_scrolls):
            post_selectors = [
                'div[data-ad-comet-preview="message"]',
                'div[data-ad-preview="message"]',
                'div.x126k92a',
            ]
            post_elements = []
            for sel in post_selectors:
                post_elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if post_elements:
                    break

            new_on_scroll = 0
            for el in post_elements:
                try:
                    text = el.text.strip()
                    if len(text) < 30 or len(text) > 5000:
                        continue
                    text_key = text[:100]
                    if text_key in seen_texts:
                        continue
                    seen_texts.add(text_key)
                    post_url = self._extract_post_url(el)
                    posts.append({"text": text, "group_url": group_url, "post_url": post_url})
                    new_on_scroll += 1
                except Exception:
                    continue

            logger.info(f"Scroll {scroll + 1}/{max_scrolls}: {new_on_scroll} new, {len(posts)} total")

            if len(posts) >= target_posts:
                break

            if new_on_scroll == 0:
                stagnant_rounds += 1
                if stagnant_rounds >= 3:
                    logger.info("No new posts after 3 scrolls, stopping")
                    break
            else:
                stagnant_rounds = 0

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            self._expand_all_posts()

        return posts[:target_posts]

    def _extract_post_url(self, post_element) -> str:
        """Extract post permalink from the timestamp link near the post."""
        try:
            # Walk up to the post container (typically 5-8 levels up)
            container = post_element
            for _ in range(8):
                container = container.find_element(By.XPATH, "..")
                # Look for timestamp links: href contains /posts/ or /permalink/
                links = container.find_elements(
                    By.CSS_SELECTOR,
                    'a[href*="/posts/"], a[href*="/permalink/"], a[href*="story_fbid"]'
                )
                if links:
                    href = links[0].get_attribute("href")
                    if href:
                        # Clean tracking params, keep the core URL
                        return href.split("?")[0]
        except Exception:
            pass
        return ""

    def _expand_all_posts(self):
        try:
            see_more_links = self.driver.find_elements(
                By.XPATH,
                "//div[@role='button' and (contains(text(), 'See more') or contains(text(), 'Xem thêm'))]"
            )
            for link in see_more_links[:10]:
                try:
                    link.click()
                    time.sleep(0.3)
                except Exception:
                    continue
        except Exception:
            pass

    def _llm_classify_job_posts(self, posts: list[dict]) -> list[dict]:
        if not posts:
            return []

        numbered = "\n\n".join(f"[{i+1}] {p['text'][:500]}" for i, p in enumerate(posts))
        prompt = (
            "Given the numbered Facebook posts below, identify posts that are clearly "
            "job-related (hiring, recruitment, job opening, looking for candidate, job offer). "
            "Return only a JSON array of integers (1-based indexes), with no extra text.\n\n"
            f"{numbered}"
        )

        try:
            content = self.llm.invoke(prompt)
            match = re.search(r'\[[\d\s,]*\]', content)
            if match:
                indexes = json.loads(match.group())
                return [posts[i - 1] for i in indexes if 1 <= i <= len(posts)]
        except Exception as e:
            logger.error(f"LLM job classification failed: {e}")
        return []

    def _llm_filter_remote(self, posts: list[dict]) -> list[dict]:
        if not posts:
            return []

        numbered = "\n\n".join(f"[{i+1}] {p['text'][:500]}" for i, p in enumerate(posts))
        prompt = (
            "Given the numbered job posts below, identify only jobs that are explicitly remote "
            "(remote/WFH/work from home/any location/fully remote). "
            "Return only a JSON array of integers (1-based indexes), with no extra text.\n\n"
            f"{numbered}"
        )

        try:
            content = self.llm.invoke(prompt)
            match = re.search(r'\[[\d\s,]*\]', content)
            if match:
                indexes = json.loads(match.group())
                return [posts[i - 1] for i in indexes if 1 <= i <= len(posts)]
        except Exception as e:
            logger.error(f"LLM remote filter failed: {e}")
        return posts

    def _llm_extract_job_fields(self, post_text: str) -> dict:
        prompt = (
            "Extract structured job information from this Facebook post. "
            "Return JSON with these fields:\n"
            "- role: job title/position\n"
            "- company: company name\n"
            "- location: job location\n"
            "- description: full job description\n\n"
            "If a field cannot be determined, use empty string. "
            "Return only valid JSON, no extra text.\n\n"
            f"Post:\n{post_text}"
        )

        try:
            content = self.llm.invoke(prompt)
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM field extraction failed: {e}")
            return {"role": "", "company": "", "location": "", "description": post_text}
