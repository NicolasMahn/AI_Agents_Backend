# Run command (needs access to host docker system): docker run -v /var/run/docker.sock:/var/run/docker.sock -p 5000:5000 image-name

FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app


COPY . /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils

RUN pip install --no-cache-dir "playwright==1.48.0" && \
    playwright install --with-deps chromium && \
    playwright install-deps chromium

ARG HUGGING_FACE_KEY
ENV HUGGING_FACE_KEY=${HUGGING_FACE_KEY}
# Install Playwright (pinned)
RUN pip install --no-cache-dir "playwright==1.48.0"

# Install Chromium manually
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-unifont \
    fonts-ubuntu \
    libnss3 \
    libatk-bridge2.0-0 \
    libxss1 \
    libasound2 \
    libxshmfence1 \
    libgbm1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxfixes3 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Tell Playwright to use system Chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/bin/chromium
RUN huggingface-cli login --token ${HUGGING_FACE_KEY} || echo "Hugging Face token not provided"


EXPOSE 5000

ARG CHROMADB_HOST
ARG CHROMADB_PORT
ARG GOOGLE_KEY
ARG OPENAI_KEY
ARG LAMBDA_KEY

ENV CHROMADB_HOST=${CHROMADB_HOST}
ENV CHROMADB_PORT=${CHROMADB_PORT}
ENV GOOGLE_KEY=${GOOGLE_KEY}
ENV OPENAI_KEY=${OPENAI_KEY}
ENV LAMBDA_KEY=${LAMBDA_KEY}

CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "main:app"]