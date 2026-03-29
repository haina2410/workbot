#!/bin/bash
# Create data files from templates if they don't exist

mkdir -p data/output

if [ ! -f data/secrets.yaml ]; then
  cat > data/secrets.yaml << 'EOF'
llm_api_key: "YOUR_API_KEY_HERE"

linkedin_cookies:
  li_at: ""
  li_rm: ""

facebook_cookies_file: "facebook_cookies.json"
EOF
  echo "Created data/secrets.yaml — edit it with your credentials"
else
  echo "data/secrets.yaml already exists"
fi

if [ ! -f data/facebook_cookies.json ]; then
  echo "[]" > data/facebook_cookies.json
  echo "Created data/facebook_cookies.json — replace with exported cookies"
else
  echo "data/facebook_cookies.json already exists"
fi

if [ ! -f data/config.yaml ]; then
  cat > data/config.yaml << 'EOF'
llm:
  model: "GLM-4.7"
  base_url: "https://mkp-api.fptcloud.com/v1"

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
