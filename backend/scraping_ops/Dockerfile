FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates curl unzip \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libc6 libgtk-3-0 libnss3 libx11-6 libx11-xcb1 libxcomposite1 \
    libxcursor1 libxdamage1 libxi6 libxext6 libxfixes3 libxrandr2 \
    libxrender1 libxss1 libxtst6 libu2f-udev xvfb && \
    rm -rf /var/lib/apt/lists/*

RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-linux-keyring.gpg \
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
 && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
 && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/google-chrome

RUN useradd -m appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . . 

USER appuser

ENV START_URL="https://www.daveasprey.com/podcast/" \
    DB_NAME="biohack_agent" \
    COLLECTION="episodes" \
    LOG_LEVEL="INFO"

ENTRYPOINT ["python", "-u", "ep_update_selenium.py"]
