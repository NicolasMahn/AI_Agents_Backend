# Run command (needs access to host docker system): docker run -v /var/run/docker.sock:/var/run/docker.sock -p 5000:5000 image-name

FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app


COPY . /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


RUN pip install --no-cache-dir playwright && playwright install

ARG HUGGING_FACE_KEY
ENV HUGGING_FACE_KEY=${HUGGING_FACE_KEY}
RUN pip install --no-cache-dir huggingface_hub
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

# Ändere den CMD-Befehl
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "main:app"]