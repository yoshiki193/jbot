FROM python:3.14-slim

RUN pip install discord.py && pip install discord.py[voice] && pip install requests
RUN apt update && apt -y install ffmpeg

ENV TZ=Asia/Tokyo