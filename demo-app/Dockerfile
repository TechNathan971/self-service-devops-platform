FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ARG APP_VERSION=dev
ARG BROKEN=false
ENV APP_VERSION=${APP_VERSION} BROKEN=${BROKEN}

# Run as a non-root user (our policy requires it)
USER 10001

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]