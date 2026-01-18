import discord

class CounterMessageManager:
    def __init__(self, bot, counter_service, counter_embed_service):
        self.bot = bot
        self.counter = counter_service
        self.counter_embed = counter_embed_service

    async def update(self, channel: discord.TextChannel):
        last_id = self.counter.get_last_message_id(str(channel.guild.id))

        if last_id:
            await self._delete_previous(self.counter.get_send_channel_id(str(channel.guild.id)), last_id)

        new_id = await self._send_new(channel)
        self.counter.set_last_message_id(str(channel.guild.id), new_id)

    async def _delete_previous(self, channel_id: int, message_id: int):
        channel = await self.bot.fetch_channel(channel_id)
        try:
            msg = await channel.fetch_message(message_id)
            await msg.delete()
        except discord.NotFound:
            pass

    async def _send_new(self, channel: discord.TextChannel):
        embed = await self.counter_embed.generate_embed(str(channel.guild.id), self.bot)
        msg = await channel.send(
            embed=discord.Embed.from_dict(embed),
            silent=True
        )
        return msg.id