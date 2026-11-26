#>>
FROM python:3.13-alpine
WORKDIR /app
COPY reconcile.py kv_operator.py ./
USER 10001:10001
ENTRYPOINT ["python", "-u", "/app/kv_operator.py"]
#<<
