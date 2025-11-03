FROM python:3.11
RUN pip install discord.py && pip install discord.py[voice] && pip install requests
RUN apt update && apt -y install ffmpeg
ENV TZ=Asia/Tokyo
CMD ["python3","/root/opt/bot.py"]