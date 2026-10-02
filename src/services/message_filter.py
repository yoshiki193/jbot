import re
import discord

CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:\w+:\d+>")
URL_PATTERN = re.compile(r"https?://")

def is_readable_message(message: discord.Message, bot_user: discord.ClientUser | None) -> bool:
    if message.guild is None or not isinstance(message.channel, discord.VoiceChannel):
        return False
    if bot_user is not None and message.author.id == bot_user.id:
        return False
    if message.clean_content == "":
        return False
    if CUSTOM_EMOJI_PATTERN.search(message.content):
        return False
    if URL_PATTERN.search(message.content):
        return False
    return True
