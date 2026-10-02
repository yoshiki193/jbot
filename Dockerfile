FROM python:3.14-slim

ENV TZ=Asia/Tokyo
ENV PYTHONUNBUFFERED=1
ENV VOICEVOX_URL=http://voicevox-engine.default.svc.cluster.local:50021

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt update && apt -y install ffmpeg

COPY src/ .

CMD ["python3","bot.py"]