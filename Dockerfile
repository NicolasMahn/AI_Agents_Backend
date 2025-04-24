# Use official Docker in docker image as a parent image
FROM ubuntu:20.04

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install python3.9, tools to manage its environment, and ensure pip is present for it
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tzdata \
        python3.9 \
        python3.9-venv \
        python3.9-dev \
        # build-essential contains tools like gcc needed to compile some pip packages
        build-essential && \
    # Use the installed python3.9 to ensure pip is installed for it
    python3.9 -m ensurepip --upgrade && \
    # Optionally make python3.9 the default python3 (use with caution)
    # update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1 && \
    # Clean up apt cache
    rm -rf /var/lib/apt/lists/* && \
    # Configure timezone
    ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata

# Now you can install packages using pip for python3.9
RUN python3.9 -m pip install --no-cache-dir requirements.txt

# Install Playwright and its browsers
RUN pip install --no-cache-dir playwright && playwright install

# Install Hugging Face CLI
RUN pip install --no-cache-dir huggingface_hub

# Set up Hugging Face authentication (optional)
ARG HUGGING_FACE_KEY
ENV HUGGING_FACE_KEY=${HUGGING_FACE_KEY}
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