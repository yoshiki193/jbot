import asyncio
import aiohttp
import discord
from discord.ext import commands
import json
import logging
import math
import datetime
import io
from collections import deque
from discord import FFmpegPCMAudio
import re

CUSTOM_EMOJI_PATTERN = r"<a?:\w+:\d+>"
URL_PATTERN = r"https?://"
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

class ModelSelect(discord.ui.Select):
    def __init__(self, cog):
        self.cog = cog
        options = [
            discord.SelectOption(label = "四国めたん", value = "2"),
            discord.SelectOption(label = "ずんだもん", value = "3"),
            discord.SelectOption(label = "春日部つむぎ", value = "8"),
            discord.SelectOption(label = "なみだめずんだもん", value = "76"),
            discord.SelectOption(label = "中国うさぎ", value = "61")
        ]
        super().__init__(
            placeholder = "モデルを選択してください",
            min_values = 1,
            max_values = 1,
            options = options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]
        selected_label = next(
            (option.label for option in self.options if option.value == selected_value),
            None
        )
        self.cog.style = int(selected_value)
        await interaction.response.send_message(
            content = f"`{selected_label}` に変更しました", ephemeral=True
        )

class ModelSelectView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout = None)
        self.add_item(ModelSelect(cog))

class command(commands.Cog):
    def __init__(self, bot:commands.Bot):
        with open('data.json') as f:
            data:dict = json.load(f)
        self.bot = bot
        self.style = 0
        self.data = data
        self.audio_queue = deque()
        self.audio_playing = False
        self.queue_lock = asyncio.Lock()
    
    async def enqueue_audio(self, buffer):
        async with self.queue_lock:
            self.audio_queue.append(buffer)
            if not self.audio_playing:
                asyncio.create_task(self._play_next())

    async def _play_next(self):
        async with self.queue_lock:
            if not self.audio_queue:
                self.audio_playing = False
                return
            self.audio_playing = True
            buffer = self.audio_queue.popleft()

        audio_source = FFmpegPCMAudio(buffer, pipe=True)
        self.vc.play(audio_source)

        while self.vc.is_playing():
            await asyncio.sleep(0.5)

        await self._play_next()

    async def generate_embed(self):
        data_list = self.data['list']
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
        if (message.author !=  self.bot.user or 'updated' in message.content) and message.channel.id == self.data['sendChannelId']:
            if self.data['lastMessageId'] == 0:
                send_message = await message.channel.send(embed = discord.Embed.from_dict(await self.generate_embed()))
                self.data['lastMessageId'] = send_message.id
            else:
                send_channel:discord.TextChannel = await self.bot.fetch_channel(self.data['sendChannelId'])
                last_message:discord.Message = await send_channel.fetch_message(self.data['lastMessageId'])
                await last_message.delete()
                send_message = await message.channel.send(embed = discord.Embed.from_dict(await self.generate_embed()),silent=True)
                self.data['lastMessageId'] = send_message.id

            with open('data.json', 'w') as f:
                json.dump(self.data, f, indent = 2)
        
        if message.channel.id in [i for i in self.data["activeVV"]] and re.search(CUSTOM_EMOJI_PATTERN, message.content) is None and re.search(URL_PATTERN, message.content) is None:
            buffer = await synthesize(message.content, self.style)
            await self.enqueue_audio(buffer)      

    @discord.app_commands.command(
        description = 'add to counter'
    )
    async def add(self,interaction:discord.Interaction,member:discord.Member):
        self.data['list'][str(member.id)] = self.data['list'][str(member.id)] + 1 if str(member.id) in self.data['list'] else 1

        with open('data.json', 'w') as f:
            json.dump(self.data, f, indent = 2)

        await interaction.response.send_message(content=f'updated\t{member.display_name}\t{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    @discord.app_commands.command(
        description = "connect VV"
    )
    async def connect_vv(self, interaction:discord.Interaction, style_id:int = 0):
        self.vc = await interaction.channel.connect()
        self.style = style_id

        self.data["activeVV"].append(interaction.channel_id)

        with open("data.json", "w") as f:
            json.dump(self.data, f, indent = 2)

        await interaction.response.send_message(content="接続しました")
    
    @discord.app_commands.command(
        description = "disconnect VV"
    )
    async def disconnect_vv(self, interaction:discord.Interaction):
        await self.vc.disconnect()

        for i, j in enumerate(self.data["activeVV"]):
            if j == interaction.channel_id:
                self.data["activeVV"].pop(i)

        with open("data.json", "w") as f:
            json.dump(self.data, f, indent = 2)
        
        await interaction.response.send_message(content="切断しました")
    
    @discord.app_commands.command(
        description = "change model"
    )
    async def change_model(self, interaction:discord.Interaction):
        await interaction.response.send_message(
            "",
            view=ModelSelectView(self)
        )

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