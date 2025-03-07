FROM python:3.11
RUN pip install discord.py
ENV token=${API_TOKEN}
ENV TZ=Asia/Tokyo
CMD ["python3","/root/opt/bot.py"]