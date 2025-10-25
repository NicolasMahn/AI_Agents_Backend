# Run command (needs access to host docker system): docker run -v /var/run/docker.sock:/var/run/docker.sock -p 5000:5000 image-name

FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY . /app

# 1️⃣ Upgrade pip & install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 2️⃣ Install system dependencies required for Playwright / Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    fonts-unifont \
    fonts-dejavu-core \
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
    xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# 3️⃣ Install Playwright (pinned) and its managed Chromium
RUN pip install --no-cache-dir "playwright==1.48.0" && \
    playwright install chromium

# 4️⃣ Hugging Face authentication
ARG HUGGING_FACE_KEY
ENV HUGGING_FACE_KEY=${HUGGING_FACE_KEY}
RUN pip install --no-cache-dir huggingface_hub && \
    huggingface-cli login --token ${HUGGING_FACE_KEY} || echo "Hugging Face token not provided"

# 5️⃣ Runtime configuration
EXPOSE 5000

ARG CHROMADB_HOST
ARG CHROMADB_PORT
ARG GOOGLE_KEY
ARG OPENAI_KEY
ARG LAMBDA_KEY

ENV CHROMADB_HOST=${CHROMADB_HOST} \
    CHROMADB_PORT=${CHROMADB_PORT} \
    GOOGLE_KEY=${GOOGLE_KEY} \
    OPENAI_KEY=${OPENAI_KEY} \
    LAMBDA_KEY=${LAMBDA_KEY}

CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "main:app"]
