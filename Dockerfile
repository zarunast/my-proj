FROM python:3.12-slim
WORKDIR /app
COPY --chown=10001:10001 docker_start.py server.py report.py questions.json ./
COPY --chown=10001:10001 public ./public
ENV PORT=8000 DATA_DIR=/data PYTHONUNBUFFERED=1
RUN mkdir /data && chown -R 10001:10001 /data
EXPOSE 8000
CMD ["python", "docker_start.py"]
