FROM python:3.11
RUN pip install discord.py
ENV TZ=Asia/Tokyo
CMD ["python3","/root/opt/bot.py"]