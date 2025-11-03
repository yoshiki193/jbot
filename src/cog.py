import asyncio
import aiohttp
import discord
from discord.ext import commands
import json
import logging
import math
import datetime
import io
from discord import FFmpegPCMAudio

VOICEVOX_URL = "http://192.168.0.71:50021"

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
            data:dict = json.load(f)

        data_list = data['list']
        payload = []

        for i in data_list:
            user:discord.User = await self.bot.fetch_user(i)
            payload.append({
                'name':f'__{user.display_name}\t{data_list[i]}\t#1__' if data_list[i] == max(j for j in data_list.values()) else f'{user.display_name}\t{data_list[i]}',
                'value':'█'*math.ceil((data_list[i]/max(j for j in data_list.values()))*10)
            })

        embed = {
            'title':'**寝落ちカウンター**',
            'description':'コマンド：/add',
            'fields':payload,
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
        
        if message.channel.id in [i for i in data["activeVV"]]:
            buffer = await synthesize(message.content, self.style)

            audio_source = FFmpegPCMAudio(buffer, pipe=True)
            self.vc.play(audio_source)

            while self.vc.is_playing():
                await asyncio.sleep(0.5)          

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
        description = "connect VV"
    )
    async def connect_vv(self, interaction:discord.Interaction, style_id:int = 0):
        self.vc = await interaction.channel.connect()
        self.style = style_id

        with open("data.json") as f:
            data:dict = json.load(f)

        data["activeVV"].append(interaction.channel_id)

        with open("data.json", "w") as f:
            json.dump(data, f, indent = 2)

        await interaction.response.send_message(content="接続しました")
    
    @discord.app_commands.command(
        description = "disconnect VV"
    )
    async def disconnect_vv(self, interaction:discord.Interaction):
        await self.vc.disconnect()

        with open("data.json") as f:
            data:dict = json.load(f)

        for i, j in enumerate(data["activeVV"]):
            if j == interaction.channel_id:
                data["activeVV"].pop(i)

        with open("data.json", "w") as f:
            json.dump(data, f, indent = 2)
        
        await interaction.response.send_message(content="切断しました")

async def setup(bot:commands.Bot):
    await bot.add_cog(command(bot))

async def synthesize(text:str, speaker:int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{VOICEVOX_URL}/audio_query",
            params={"text": text, "speaker": speaker}
        ) as resp:
            resp.raise_for_status()
            query_json = await resp.json()

        async with session.post(
            f"{VOICEVOX_URL}/synthesis",
            params={"speaker": speaker},
            json=query_json
        ) as resp:
            resp.raise_for_status()
            wav_bytes = await resp.read()

    buffer = io.BytesIO(wav_bytes)
    buffer.seek(0)
    return buffer