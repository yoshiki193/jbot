import discord
from discord.ext import commands
import json
import logging
import math
import datetime

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers = [
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

class command(commands.Cog):
    def __init__(self, bot:commands.Bot):
        with open('data.json') as f:
            data = json.load(f)
        self.last_message_id = data['lastMessageId']
        self.send_channel_id = data['sendChannelId']
        self.bot = bot
    
    async def generate_embed(self):
        with open('data.json') as f:
            data_list:dict = json.load(f)['list']
            
        payload = []
        
        for i in data_list:
            user:discord.User = await self.bot.fetch_user(i)
            payload.append({
                'name':f'__**{user.display_name}\t{data_list[i]}\t#1**__' if data_list[i] == max(j for j in data_list.values()) else f'{user.display_name}\t{data_list[i]}',
                'value':'█'*math.ceil((data_list[i]/max(j for j in data_list.values()))*10)
            })
            
        embed = {
            'title':'**寝落ちカウンター**',
            'description':'コマンド：/add',
            'fields':payload,
            'color':11584734,
            'thumbnail':{
                'url':'https://cdn.wikiwiki.jp/to/w/kc-summary/eqgb/::attach/e065gb.png?rev=01386a742f306fe4398d5cf66da4ba28&t=20150123094908'
            }
        }

        return embed

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if (message.author !=  self.bot.user or "updated" in message.content) and message.channel.id == self.send_channel_id:
            with open('data.json') as f:
                data:dict = json.load(f)

            if self.last_message_id == 0:
                send_message = await message.channel.send(embed = discord.Embed.from_dict(await self.generate_embed()))
                self.last_message_id = send_message.id
            else:
                send_channel:discord.TextChannel = await self.bot.fetch_channel(self.send_channel_id)
                last_message:discord.Message = await send_channel.fetch_message(self.last_message_id)
                await last_message.delete()
                send_message = await message.channel.send(embed = discord.Embed.from_dict(await self.generate_embed()))
                self.last_message_id = send_message.id
            
            data['lastMessageId'] = self.last_message_id

            with open('data.json', 'w') as f:
                json.dump(data, f, indent = 2)

    
    @discord.app_commands.command(
        description = "add to counter"
    )
    async def add(self,interaction:discord.Interaction,member:discord.Member):
        with open('data.json') as f:
            data:dict = json.load(f)
            data_list = data['list']

        data_list[str(member.id)] = data_list[str(member.id)] + 1 if str(member.id) in data_list else 1
        data['list'] = data_list

        with open('data.json', 'w') as f:
                json.dump(data, f, indent = 2)
        
        await interaction.response.send_message(content=f'updated\t{member.display_name}\t{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

async def setup(bot:commands.Bot):
    await bot.add_cog(command(bot))