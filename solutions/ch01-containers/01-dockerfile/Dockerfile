#>>
FROM python:3.13-alpine
WORKDIR /app
COPY hello.py .
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["python", "-u", "hello.py"]
#<<
