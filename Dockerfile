FROM python:3.12
RUN pip install discord.py && pip install discord.py[voice]
RUN apt update && apt -y install ffmpeg
ENV TZ=Asia/Tokyo
CMD ["python3","/root/opt/bot.py"]