import discord
import math

class CounterEmbedService:
    def __init__(self, counter_service):
        self.counter = counter_service

    async def generate_embed(self, guild_id: str, bot):
        data_list = self.counter.get_users(guild_id)
        payload = []

        for i in data_list:
            user:discord.User = await bot.fetch_user(i)
            payload.append({
                "name":f"__{user.display_name}\t{data_list[i]}\t#1__" if data_list[i] == max(j for j in data_list.values()) else f"{user.display_name}\t{data_list[i]}",
                "value":"█"*math.ceil((data_list[i]/max(j for j in data_list.values()))*10)
            })

        embed = {
            "title":"**寝落ちカウンター**",
            "description":"コマンド：/add",
            "fields":payload
        }

        return embed