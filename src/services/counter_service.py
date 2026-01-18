import discord

class CounterService:
    def __init__(self, repo):
        self.repo = repo

    def add(self, member_id: str, guild_id: str):
        self.repo.increment_counter_users(guild_id, member_id)
    
    def get_users(self, guild_id: str):
        return self.repo.get_counter_users(guild_id)
    
    def get_last_message_id(self, guild_id: str):
        return self.repo.get_last_message_id(guild_id)

    def set_last_message_id(self, guild_id: str, message_id: int):
        self.repo.set_last_message_id(guild_id, message_id)
    
    def get_send_channel_id(self, guild_id: str):
        return self.repo.get_send_channel_id(guild_id)
    
    def is_counter_update_message(self, message: discord.Message, bot) -> bool:
        if message is None or message.guild is None or message.channel is None:
            return False

        send_channel_id = self.get_send_channel_id(str(message.guild.id))
        if send_channel_id is None:
            return False

        if (message.author != bot or "updated" in message.content) and message.channel.id == send_channel_id:
            return True

        return False