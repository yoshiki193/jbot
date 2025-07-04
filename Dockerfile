FROM python:3.11
RUN pip install discord.py && pip install discord.py[voice] && pip install https://github.com/VOICEVOX/voicevox_core/releases/download/0.16.0/voicevox_core-0.16.0-cp310-abi3-manylinux_2_34_x86_64.whl
RUN apt update && apt -y install ffmpeg
ENV TZ=Asia/Tokyo
CMD ["python3","/root/opt/bot.py"]