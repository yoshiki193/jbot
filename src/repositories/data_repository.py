import json

class DataRepository:
    def __init__(self, path="data.json"):
        self.path = path
        self.data = self._load()

    def _load(self):
        with open(self.path) as f:
            return json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)
    
    def get_guild(self, guild_id :str) -> dict:
        return self.data["guilds"].setdefault(
            guild_id,
            {
                "counter": {
                    "send_channel_id": 0,
                    "last_message_id": 0,
                    "users": {}
                },
                "voicevox": {
                    "speaker": 0,
                    "active_vv": 0
                }
            }
        )
    
    def get_active_vv(self, guild_id: str):
        guild = self.get_guild(guild_id)
        return guild["voicevox"]["active_vv"]
    
    def get_counter_users(self, guild_id: str):
        guild = self.get_guild(guild_id)
        return guild["counter"]["users"]
    
    def increment_counter_users(self, guild_id: str, member_id: str):
        users = self.get_guild(guild_id)["counter"]["users"]
        users[member_id] = users.get(member_id, 0) + 1
        self.save()
    
    def get_send_channel_id(self, guild_id: str):
        guild = self.get_guild(guild_id)
        return guild["counter"]["send_channel_id"]

    def get_last_message_id(self, guild_id: str):
        guild = self.get_guild(guild_id)
        return guild["counter"]["last_message_id"]
    
    def set_last_message_id(self, guild_id: str, last_message_id: int):
        guild = self.get_guild(guild_id)
        guild["counter"]["last_message_id"] = last_message_id
        self.save()

    def get_voicevox_speaker(self, guild_id: str):
        guild = self.get_guild(guild_id)
        return guild["voicevox"]["speaker"]
    
    def set_voicevox_speaker(self, guild_id: str, speaker: int):
        guild = self.get_guild(guild_id)
        guild["voicevox"]["speaker"] = speaker
        self.save()