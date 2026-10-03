import sqlite3
from typing import NamedTuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS guilds (
    guild_id                INTEGER PRIMARY KEY,
    counter_send_channel_id INTEGER NOT NULL DEFAULT 0,
    counter_last_message_id INTEGER NOT NULL DEFAULT 0,
    active_auto_connect     INTEGER NOT NULL DEFAULT 0,
    counter_title           TEXT    NOT NULL DEFAULT '寝落ちカウンター',
    counter_multiplier      INTEGER NOT NULL DEFAULT 100,
    counter_total_title     TEXT    NOT NULL DEFAULT '合計金額'
);

CREATE TABLE IF NOT EXISTS counter_users (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS counter_ban_users (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS voicevox_speakers (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    speaker_id INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS fix_msgs (
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    content    TEXT,
    PRIMARY KEY (guild_id, channel_id)
);
"""

class FixMsg(NamedTuple):
    message_id: int
    content: str | None

class CounterSettings(NamedTuple):
    title: str
    multiplier: int
    total_title: str

# 設定コマンド追加前から使われているギルド向けの既定値（従来の表示と同じ）
DEFAULT_COUNTER_SETTINGS = CounterSettings("寝落ちカウンター", 100, "合計金額")

class DataRepository:
    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self):
        # content 列追加前に作成された DB への後方互換
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(fix_msgs)")}
        if "content" not in columns:
            self.conn.execute("ALTER TABLE fix_msgs ADD COLUMN content TEXT")

        # カウンター表示設定の列追加前に作成された DB への後方互換
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(guilds)")}
        defaults = DEFAULT_COUNTER_SETTINGS
        if "counter_title" not in columns:
            self.conn.execute(f"ALTER TABLE guilds ADD COLUMN counter_title TEXT NOT NULL DEFAULT '{defaults.title}'")
        if "counter_multiplier" not in columns:
            self.conn.execute(f"ALTER TABLE guilds ADD COLUMN counter_multiplier INTEGER NOT NULL DEFAULT {defaults.multiplier}")
        if "counter_total_title" not in columns:
            self.conn.execute(f"ALTER TABLE guilds ADD COLUMN counter_total_title TEXT NOT NULL DEFAULT '{defaults.total_title}'")

    def close(self):
        self.conn.close()

    def _fetch_one(self, sql: str, params: tuple):
        row = self.conn.execute(sql, params).fetchone()
        return row[0] if row else None

    def _ensure_guild(self, guild_id: int):
        self.conn.execute("INSERT OR IGNORE INTO guilds (guild_id) VALUES (?)", (guild_id,))

    def _set_guild_column(self, guild_id: int, column: str, value):
        with self.conn:
            self._ensure_guild(guild_id)
            self.conn.execute(f"UPDATE guilds SET {column} = ? WHERE guild_id = ?", (value, guild_id))

    def get_fix_msg(self, guild_id: int, channel_id: int) -> FixMsg | None:
        row = self.conn.execute(
            "SELECT message_id, content FROM fix_msgs WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id)
        ).fetchone()
        return FixMsg(*row) if row else None

    def set_fix_msg(self, guild_id: int, channel_id: int, message_id: int, content: str):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO fix_msgs (guild_id, channel_id, message_id, content) VALUES (?, ?, ?, ?)",
                (guild_id, channel_id, message_id, content)
            )

    def delete_fix_msg(self, guild_id: int, channel_id: int):
        with self.conn:
            self.conn.execute(
                "DELETE FROM fix_msgs WHERE guild_id = ? AND channel_id = ?",
                (guild_id, channel_id)
            )

    def get_active_auto_connect(self, guild_id: int) -> bool:
        value = self._fetch_one("SELECT active_auto_connect FROM guilds WHERE guild_id = ?", (guild_id,))
        return bool(value)

    def set_active_auto_connect(self, guild_id: int, enabled: bool):
        self._set_guild_column(guild_id, "active_auto_connect", int(enabled))

    def get_counter_users(self, guild_id: int) -> dict[int, int]:
        rows = self.conn.execute(
            "SELECT user_id, count FROM counter_users WHERE guild_id = ? ORDER BY rowid",
            (guild_id,)
        ).fetchall()
        return {user_id: count for user_id, count in rows}

    def set_counter_users(self, guild_id: int, member_id: int, incremental: int):
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO counter_users (guild_id, user_id, count) VALUES (?, ?, ?)
                ON CONFLICT (guild_id, user_id) DO UPDATE SET count = count + excluded.count
                """,
                (guild_id, member_id, incremental)
            )

    def get_ban_users(self, guild_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT user_id FROM counter_ban_users WHERE guild_id = ?",
            (guild_id,)
        ).fetchall()
        return [user_id for (user_id,) in rows]

    def get_send_channel_id(self, guild_id: int):
        return self._fetch_one("SELECT counter_send_channel_id FROM guilds WHERE guild_id = ?", (guild_id,)) or 0

    def set_send_channel_id(self, guild_id: int, send_channel_id: int):
        self._set_guild_column(guild_id, "counter_send_channel_id", send_channel_id)

    def get_counter_settings(self, guild_id: int) -> CounterSettings:
        row = self.conn.execute(
            "SELECT counter_title, counter_multiplier, counter_total_title FROM guilds WHERE guild_id = ?",
            (guild_id,)
        ).fetchone()
        return CounterSettings(*row) if row else DEFAULT_COUNTER_SETTINGS

    def set_counter_settings(self, guild_id: int, settings: CounterSettings):
        with self.conn:
            self._ensure_guild(guild_id)
            self.conn.execute(
                "UPDATE guilds SET counter_title = ?, counter_multiplier = ?, counter_total_title = ? WHERE guild_id = ?",
                (settings.title, settings.multiplier, settings.total_title, guild_id)
            )

    def get_last_message_id(self, guild_id: int):
        return self._fetch_one("SELECT counter_last_message_id FROM guilds WHERE guild_id = ?", (guild_id,)) or 0

    def set_last_message_id(self, guild_id: int, last_message_id: int):
        self._set_guild_column(guild_id, "counter_last_message_id", last_message_id)

    def get_voicevox_speaker(self, guild_id: int, member_id: int):
        return self._fetch_one(
            "SELECT speaker_id FROM voicevox_speakers WHERE guild_id = ? AND user_id = ?",
            (guild_id, member_id)
        )

    def set_voicevox_speaker(self, guild_id: int, speaker: int, member_id: int):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO voicevox_speakers (guild_id, user_id, speaker_id) VALUES (?, ?, ?)",
                (guild_id, member_id, speaker)
            )
