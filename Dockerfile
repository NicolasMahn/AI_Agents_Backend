# Use official Docker in docker image as a parent image
FROM ubuntu:latest


# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Ensures Python output is sent straight to terminal without being buffered
ENV PYTHONUNBUFFERED 1


# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Set non-interactive frontend and configure timezone
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata


# Install prerequisites and Python 3.9 from PPA
RUN apt-get install -y --no-install-recommends \
    software-properties-common \
    gnupg \
    curl && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get install -y --no-install-recommends \
    python3.9 \
    python3.9-distutils \
    python3-pip \
    python3.9-venv && \
    # Clean up apt cache
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# RUN python3 -m pip install pip --upgrade

# Install requirements
RUN pip install -r requirements.txt

# Install Playwright
RUN pip install --no-cache-dir playwright && playwright install

# Set up Hugging Face authentication
ARG HUGGING_FACE_KEY
ENV HUGGING_FACE_KEY=${HUGGING_FACE_KEY}
RUN pip install --no-cache-dir huggingface_hub
RUN huggingface-cli login --token ${HUGGING_FACE_KEY} || echo "Hugging Face token not provided"

# Install docker
RUN apt-get install -y docker.io

# Start the Docker daemon and build the custom-python image
RUN dockerd & sleep 5 && docker build -f CustomPythonDockerfile -t custom-python .


# Make port 80 available to the world outside this container
EXPOSE 5000

# Set build arguments for secrets
ARG CHROMA_HOST
ARG CHROMA_PORT
ARG GOOGLE_KEY
ARG OPENAI_KEY
ARG LAMBDA_KEY

# Set environment variables for secrets
ENV CHROMA_HOST=${CHROMA_HOST}
ENV CHROMA_PORT=${CHROMA_PORT}
ENV GOOGLE_KEY=${GOOGLE_KEY}
ENV OPENAI_KEY=${OPENAI_KEY}
ENV LAMBDA_KEY=${LAMBDA_KEY}


# Run the application using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "main:app"]