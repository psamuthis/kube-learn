# The image every chapter uses. Built by `./course cluster up` (or `./course cluster images`).
FROM python:3.13-alpine
ARG VERSION=dev
ARG COLOR=blue
ENV APP_VERSION=${VERSION} COLOR=${COLOR} PYTHONUNBUFFERED=1
WORKDIR /app
COPY app.py .
# A fixed, non-root UID: securityContext.runAsNonRoot can verify it (chapter 12).
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["python", "/app/app.py"]
