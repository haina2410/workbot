FROM python:3.12-slim

# Chrome dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg2 unzip \
    libnss3 libxss1 libasound2 libatk-bridge2.0-0 libgtk-3-0 libdrm2 libgbm1 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

EXPOSE 8000

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
