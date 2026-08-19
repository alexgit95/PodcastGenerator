FROM python:3.11-slim

ARG BUILD_COMMIT_SHA=unknown

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PODCAST_BUILD_COMMIT_SHA=${BUILD_COMMIT_SHA}
ENV PIPER_MODEL_DIR=/opt/piper
ENV PODCAST_PIPER_MODEL_PATH=/opt/piper/fr_FR-upmc-medium.onnx
ENV PODCAST_PIPER_COMMAND=piper
ENV PODCAST_FFMPEG_COMMAND=ffmpeg

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends ffmpeg curl ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt piper-tts

RUN mkdir -p /opt/piper \
	&& curl -fsSL \
		-o /opt/piper/fr_FR-upmc-medium.onnx \
		https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx \
	&& curl -fsSL \
		-o /opt/piper/fr_FR-upmc-medium.onnx.json \
		https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx.json

COPY . .

EXPOSE 8080

CMD ["python", "-m", "app.main"]
