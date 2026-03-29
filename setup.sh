#!/bin/bash
# Create data files from .env and templates if they don't exist

set -e

# Load .env if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
  echo "Loaded .env"
else
  cat > .env << 'EOF'
LLM_API_KEY=YOUR_API_KEY_HERE
LLM_MODEL=GLM-4.7
LLM_BASE_URL=https://mkp-api.fptcloud.com/v1

LINKEDIN_LI_AT=
LINKEDIN_LI_RM=

SELENIUM_URL=http://chrome:4444
EOF
  echo "Created .env — edit it with your credentials, then re-run ./setup.sh"
  exit 1
fi

mkdir -p data/output

# Generate secrets.yaml from env vars
cat > data/secrets.yaml << EOF
llm_api_key: "${LLM_API_KEY}"

linkedin_cookies:
  li_at: "${LINKEDIN_LI_AT}"
  li_rm: "${LINKEDIN_LI_RM}"

facebook_cookies_file: "facebook_cookies.json"
EOF
echo "Generated data/secrets.yaml from .env"

# Generate config.yaml from env vars (with defaults)
if [ ! -f data/config.yaml ]; then
  cat > data/config.yaml << EOF
llm:
  model: "${LLM_MODEL:-GLM-4.7}"
  base_url: "${LLM_BASE_URL:-https://mkp-api.fptcloud.com/v1}"

enabled_crawlers: ["facebook"]

linkedin:
  filters:
    keywords: "Software Engineer"
    location: "Vietnam"
    date_posted: "past_week"
  max_jobs_per_run: 20
  max_pages: 3

facebook:
  group_urls: []
  target_posts: 25
  max_pages: 10
  filter_remote_only: false
  max_jobs_per_run: 20
  use_llm: true

rate_limiting:
  min_delay: 2
  max_delay: 5
EOF
  echo "Created data/config.yaml — edit crawler settings"
else
  echo "data/config.yaml already exists"
fi

if [ ! -f data/facebook_cookies.json ]; then
  echo "[]" > data/facebook_cookies.json
  echo "Created data/facebook_cookies.json — replace with exported cookies"
else
  echo "data/facebook_cookies.json already exists"
fi

echo "Done. Run: docker compose up -d"
