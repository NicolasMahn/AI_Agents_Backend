# Use the official Docker-in-Docker image as the base
FROM docker:24.0.5

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app


# Install Python and other dependencies
RUN apk add --no-cache \
    python3=3.9.18-r0 \
    py3-pip

# Install Playwright and its browsers
RUN pip install --no-cache-dir playwright && playwright install

# Install Hugging Face CLI
RUN pip install --no-cache-dir huggingface_hub

# Set up Hugging Face authentication (optional)
ARG HUGGING_FACE_KEY
ENV HUGGING_FACE_KEY=${HUGGING_FACE_KEY}
RUN huggingface-cli login --token ${HUGGING_FACE_KEY} || echo "Hugging Face token not provided"


# Start the Docker daemon and build the custom-python image
RUN dockerd & sleep 5 && docker build -f CustomPythonDockerfile -t custom-python .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

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