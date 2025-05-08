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

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

class command(commands.Cog):
    def __init__(self, bot:commands.Bot):
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
        with open('data.json') as f:
            data:dict = json.load(f)
        if (message.author !=  self.bot.user or 'updated' in message.content) and message.channel.id == data['sendChannelId']:
            if data['lastMessageId'] == 0:
                send_message = await message.channel.send(embed = discord.Embed.from_dict(await self.generate_embed()))
                data['lastMessageId'] = send_message.id
            else:
                send_channel:discord.TextChannel = await self.bot.fetch_channel(data['sendChannelId'])
                last_message:discord.Message = await send_channel.fetch_message(data['lastMessageId'])
                await last_message.delete()
                send_message = await message.channel.send(embed = discord.Embed.from_dict(await self.generate_embed()),silent=True)
                data['lastMessageId'] = send_message.id

            with open('data.json', 'w') as f:
                json.dump(data, f, indent = 2)
        elif message.author != self.bot.user and message.channel.id != data['sendChannelId']:
            with open('data.json') as f:
                data:dict = json.load(f)
            if str(message.channel.id) in [i for i in data['announcement']]:
                last_message = await message.channel.fetch_message(data['announcement'][str(message.channel.id)]['messageId'])
                await last_message.delete()
                send_message = await message.channel.send(content=data['announcement'][str(message.channel.id)]['value'],silent=True)
                data['announcement'][str(message.channel.id)]['messageId'] = send_message.id

                with open('data.json', 'w') as f:
                    json.dump(data, f, indent = 2)

    @discord.app_commands.command(
        description = 'add to counter'
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

    @discord.app_commands.command(
        description = 'announcement'
    )
    @discord.app_commands.describe(mode='モードの指定')
    @discord.app_commands.choices(mode=[
        discord.app_commands.Choice(name='新規', value='new'),
        discord.app_commands.Choice(name='削除', value='delete'),
    ])
    async def announcement(self,interaction:discord.Interaction,mode:discord.app_commands.Choice[str],text:str = None):
        with open('data.json') as f:
            data:dict = json.load(f)
        if mode.value == 'new' and interaction.channel_id != data['sendChannelId'] and text != None:
            data['announcement'][interaction.channel_id] = {}
            data['announcement'][interaction.channel_id]['value'] = text
            last_message = await interaction.response.send_message(content=text)
            data['announcement'][interaction.channel_id]['messageId'] = last_message.message_id

            with open('data.json', 'w') as f:
                json.dump(data, f, indent = 2)
        elif mode.value == 'delete' and interaction.channel_id != data['sendChannelId'] and text == None:
            with open('data.json') as f:
                data:dict = json.load(f)
            
            if str(interaction.channel_id) in [i for i in data['announcement']]:
                data['announcement'].pop(str(interaction.channel_id))

                with open('data.json', 'w') as f:
                    json.dump(data, f, indent = 2)

                await interaction.response.send_message(content='complete',silent=True)
            else:
                await interaction.response.send_message(content='error',silent=True)
        else:
            await interaction.response.send_message(content='error',silent=True)

async def setup(bot:commands.Bot):
    await bot.add_cog(command(bot))