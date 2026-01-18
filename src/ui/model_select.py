import discord

class ModelSelect(discord.ui.Select):
    def __init__(self, repo):
        self.repo = repo

        options = [
            discord.SelectOption(label = "四国めたん", value = "2"),
            discord.SelectOption(label = "ずんだもん", value = "3"),
            discord.SelectOption(label = "春日部つむぎ", value = "8"),
            discord.SelectOption(label = "なみだめずんだもん", value = "76"),
            discord.SelectOption(label = "中国うさぎ", value = "61")
        ]

        super().__init__(
            placeholder="モデルを選択してください",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        speaker = int(self.values[0])
        self.repo.set_voicevox_speaker(str(interaction.guild_id), speaker)

        label = next(
            o.label for o in self.options if o.value == self.values[0]
        )

        await interaction.response.send_message(
            f"`{label}` に変更しました",
            ephemeral=True
        )

class ModelSelectView(discord.ui.View):
    def __init__(self, repo):
        super().__init__(timeout=None)
        self.add_item(ModelSelect(repo))