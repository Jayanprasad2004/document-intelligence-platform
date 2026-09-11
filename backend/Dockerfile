# Tesseract is a system binary, not a pip package -- Render's (and most
# platforms') native Python buildpack does NOT install it, which is why
# this needs a Dockerfile rather than a plain "detect and run" deploy.
# libgl1/libglib2.0-0 are runtime deps of opencv-python-headless on a
# minimal base image (missing them causes an import-time crash, not a
# helpful error message, so they're easy to miss until deploy fails).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render (and most PaaS platforms) inject the port to bind via $PORT
# at runtime -- it is NOT always 8000, so this must not be hardcoded.
# Shell form is required here so $PORT actually gets expanded.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
