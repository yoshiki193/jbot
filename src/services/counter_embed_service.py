import discord
from discord.ext import commands
from services.counter_service import CounterService
import math

class CounterEmbedService:
    def __init__(self, counter_service: CounterService):
        self.counter = counter_service

    async def generate_embed(self, guild_id: str, bot: commands.Bot):
        data_list = self.counter.get_users(guild_id)
        payload = []
        sum = 0

        for i in data_list:
            user:discord.User = await bot.fetch_user(i)
            sum = sum + data_list[i]
            payload.append({
                "name":f"__{user.display_name}\t{data_list[i]}\t#1__" if data_list[i] == max(j for j in data_list.values()) else f"{user.display_name}\t{data_list[i]}",
                "value":"█"*math.ceil((data_list[i]/max(j for j in data_list.values()))*10)
            })
        
        payload.append({
            "name":" ",
            "value":"──────────"
        })
        
        payload.append({
            "name":"合計金額",
            "value":f"```￥{sum * 100}```"
        })

        embed = {
            "title":"**寝落ちカウンター**",
            "description":"コマンド：/add",
            "fields":payload
        }

        return embed