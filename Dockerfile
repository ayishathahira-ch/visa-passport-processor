FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY visa_processor ./visa_processor
COPY samples ./samples
RUN useradd --create-home --uid 1000 appuser
USER appuser
ENV PORT=5000
EXPOSE 5000
# Local use:  docker run -p 127.0.0.1:5000:5000 -e API_KEY=change-me visa-processor
# Public demo: docker run -p 5000:5000 -e DEMO_MODE=1 visa-processor
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT} --timeout 120 --workers 2 'visa_processor.api:create_app()'"]
