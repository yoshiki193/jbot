"""data.json の内容を SQLite に移行する一回限りのスクリプト。

使い方: python migrate_json_to_sqlite.py [data.json] [data.db]
voicevox_url は移行しない（環境変数 VOICEVOX_URL で指定する）。
"""
import json
import sys
from repositories.data_repository import DataRepository

def migrate(json_path: str, db_path: str):
    with open(json_path) as f:
        data = json.load(f)

    repo = DataRepository(db_path)
    conn = repo.conn

    with conn:
        for guild_id_str, guild in data.get("guilds", {}).items():
            guild_id = int(guild_id_str)
            counter = guild.get("counter", {})
            voicevox = guild.get("voicevox", {})

            conn.execute(
                """
                INSERT OR REPLACE INTO guilds
                    (guild_id, counter_send_channel_id, counter_last_message_id, active_auto_connect)
                VALUES (?, ?, ?, ?)
                """,
                (
                    guild_id,
                    counter.get("send_channel_id", 0),
                    counter.get("last_message_id", 0),
                    int(voicevox.get("active_auto_connect", False)),
                )
            )

            for user_id, count in counter.get("users", {}).items():
                conn.execute(
                    "INSERT OR REPLACE INTO counter_users (guild_id, user_id, count) VALUES (?, ?, ?)",
                    (guild_id, int(user_id), count)
                )

            for user_id in counter.get("ban_users", []):
                conn.execute(
                    "INSERT OR IGNORE INTO counter_ban_users (guild_id, user_id) VALUES (?, ?)",
                    (guild_id, int(user_id))
                )

            for user_id, speaker_id in voicevox.get("speaker", {}).items():
                conn.execute(
                    "INSERT OR REPLACE INTO voicevox_speakers (guild_id, user_id, speaker_id) VALUES (?, ?, ?)",
                    (guild_id, int(user_id), speaker_id)
                )

            for channel_id, message_id in guild.get("fix_msgs", {}).items():
                conn.execute(
                    "INSERT OR REPLACE INTO fix_msgs (guild_id, channel_id, message_id) VALUES (?, ?, ?)",
                    (guild_id, int(channel_id), message_id)
                )

    repo.close()

if __name__ == "__main__":
    json_path = sys.argv[1] if len(sys.argv) > 1 else "./data.json"
    db_path = sys.argv[2] if len(sys.argv) > 2 else "./data.db"
    migrate(json_path, db_path)
    print(f"migrated {json_path} -> {db_path}")
