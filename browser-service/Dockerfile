# 1. Use your proven Python 3.12 base (instead of the broken Selenium base)
FROM python:3.12-slim

# 2. Switch to root to install Chrome/Selenium
USER root

# 3. Install system dependencies (same as your Backend) + Chrome dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev \
    curl \
    g++ \
    make \
    wget \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 4. Install Google Chrome (Selenium requires this to run)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 5. Install your Python requirements (no --break-system-packages needed now)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your agent code
COPY . .

# 7. Selenium standalone uses port 4444
EXPOSE 8080

# 8. Copy and run your updated entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
CMD ["sh", "entrypoint.sh"]
