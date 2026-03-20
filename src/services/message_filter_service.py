import discord
import re

class MessageFilterService:
    def __init__(self, bot_user):
        self.bot_user = bot_user
        self.custom_emoji_pattern = r"<a?:\w+:\d+>"
        self.url_pattern = r"https?://"

    def is_playable_message(self, message: discord.Message) -> bool:
        if message is None:
            return False
        if message.guild is None:
            return False
        if message.author == self.bot_user:
            return False
        if re.search(self.custom_emoji_pattern, message.content):
            return False
        if re.search(self.url_pattern, message.content):
            return False
        return True