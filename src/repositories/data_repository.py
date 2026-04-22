import json

class DataRepository:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        with open(self.path) as f:
            return json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)
    
    def get_guild(self, guild_id :int) -> dict:
        return self.data["guilds"].setdefault(
            str(guild_id),
            {
                "counter": {
                    "send_channel_id": 0,
                    "last_message_id": 0,
                    "users": {},
                    "ban_users": []
                },
                "voicevox": {
                    "speaker": {},
                    "active_auto_connect": 0
                }
            }
        )

    def get_voicevox_url(self):
        return self.data["voicevox_url"]
    
    def get_active_auto_connect(self, guild_id: int):
        guild = self.get_guild(guild_id)
        return guild["voicevox"]["active_auto_connect"]
    
    def set_active_auto_connect(self, guild_id: int, enabled: bool):
        guild = self.get_guild(guild_id)
        guild["voicevox"]["active_auto_connect"] = enabled
        self.save()
    
    def get_counter_users(self, guild_id: int):
        guild = self.get_guild(guild_id)
        return guild["counter"]["users"]

    def set_counter_users(self, guild_id: int, member_id: int, incremental: int):
        users = self.get_guild(guild_id)["counter"]["users"]
        users[str(member_id)] = users.get(str(member_id), 0) + incremental
        self.save()
    
    def get_ban_users(self, guild_id: int):
        guild = self.get_guild(guild_id)
        return guild["counter"]["ban_users"]
    
    def get_send_channel_id(self, guild_id: int):
        guild = self.get_guild(guild_id)
        return guild["counter"]["send_channel_id"]

    def get_last_message_id(self, guild_id: int):
        guild = self.get_guild(guild_id)
        return guild["counter"]["last_message_id"]
    
    def set_last_message_id(self, guild_id: int, last_message_id: int):
        guild = self.get_guild(guild_id)
        guild["counter"]["last_message_id"] = last_message_id
        self.save()

    def get_voicevox_speaker(self, guild_id: int, member_id: int):
        guild = self.get_guild(guild_id)
        return guild["voicevox"]["speaker"].get(str(member_id))
    
    def set_voicevox_speaker(self, guild_id: int, speaker: int, member_id: int):
        guild = self.get_guild(guild_id)
        guild["voicevox"]["speaker"][str(member_id)] = speaker
        self.save()
