# Jobs Applier

Crawl job listings from LinkedIn and Facebook groups. Returns structured JSON.

## Setup

```bash
uv venv && uv pip install -r requirements.txt
```

Copy your credentials into `data/`:
- `data/secrets.yaml` — API keys, LinkedIn cookies
- `data/facebook_cookies.json` — Facebook cookies (exported from browser)

Edit `data/config.yaml` for search filters, LLM endpoint, and which crawlers to enable.

## Usage

### CLI

```bash
uv run python -m src
```

Crawls and writes JSON to `data/output/jobs_YYYY-MM-DD_HHMMSS.json`.

### HTTP API

```bash
uv run python -m src --serve
uv run python -m src --serve --port 9000
```

Endpoints:

```bash
# Health check
curl localhost:8000/health

# Crawl both sources
curl -X POST localhost:8000/crawl

# Crawl specific source
curl -X POST localhost:8000/crawl -H 'Content-Type: application/json' -d '{"sources": ["facebook"]}'
```

### n8n Integration

Import workflows from `n8n/` into your n8n instance:
- `discord-crawl-trigger.json` — trigger crawls from Discord
- `scheduled-crawl.json` — auto-crawl every 6 hours

Set up a Data Tables table for dedup and configure your Discord webhook URL in each workflow.

## Config

`data/config.yaml`:
```yaml
llm:
  model: "GLM-4.7"
  base_url: "https://mkp-api.fptcloud.com/v1"

enabled_crawlers: ["linkedin", "facebook"]

linkedin:
  filters:
    keywords: "Software Engineer"
    location: "Vietnam"
    date_posted: "past_week"
  max_jobs_per_run: 20
  max_pages: 3

facebook:
  group_urls:
    - "https://www.facebook.com/groups/your-group-here"
  target_posts: 25
  max_pages: 10
  filter_remote_only: false
  max_jobs_per_run: 20
```

`data/secrets.yaml`:
```yaml
llm_api_key: "your-key"

linkedin_cookies:
  li_at: ""
  li_rm: ""

facebook_cookies_file: "facebook_cookies.json"
```

## Project Structure

```
src/
  api.py          — FastAPI server
  runner.py       — Crawl logic + CLI entry point
  llm.py          — OpenAI SDK wrapper
  job.py          — Job dataclass
  crawlers/
    base.py       — Abstract crawler
    linkedin.py   — LinkedIn crawler
    facebook.py   — Facebook crawler (uses LLM for post classification)
    config.py     — Config loader
workspace/        — Per-person CV pipeline
n8n/              — n8n workflow exports
data/             — Config, secrets, output
```
