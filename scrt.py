import os

CHROMADB_HOST = os.getenv("CHROMADB_HOST")
REDIS_HOST = os.getenv("REDIS_HOST")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT"))
OPENAI_KEY = os.getenv("OPENAI_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_KEY")
LAMBDA_KEY = os.getenv("LAMBDA_KEY")
HUGGING_FACE_KEY = os.getenv("HUGGING_FACE_KEY")
