import sqlite3
from typing import NamedTuple

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS guilds (
        guild_id            INTEGER PRIMARY KEY,
        active_auto_connect INTEGER NOT NULL DEFAULT 0
    )
    """,
    # カウンターは 1 チャンネルにつき 1 件
    """
    CREATE TABLE IF NOT EXISTS counters (
        guild_id        INTEGER NOT NULL,
        channel_id      INTEGER NOT NULL,
        last_message_id INTEGER NOT NULL DEFAULT 0,
        title           TEXT    NOT NULL,
        multiplier      INTEGER NOT NULL,
        total_title     TEXT    NOT NULL,
        PRIMARY KEY (guild_id, channel_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS counter_users (
        guild_id   INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        user_id    INTEGER NOT NULL,
        count      INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (guild_id, channel_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS counter_ban_users (
        guild_id INTEGER NOT NULL,
        user_id  INTEGER NOT NULL,
        PRIMARY KEY (guild_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS voicevox_speakers (
        guild_id   INTEGER NOT NULL,
        user_id    INTEGER NOT NULL,
        speaker_id INTEGER NOT NULL,
        PRIMARY KEY (guild_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fix_msgs (
        guild_id   INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        content    TEXT,
        PRIMARY KEY (guild_id, channel_id)
    )
    """,
]

class FixMsg(NamedTuple):
    message_id: int
    content: str | None

class CounterSettings(NamedTuple):
    title: str
    multiplier: int
    total_title: str

class Counter(NamedTuple):
    last_message_id: int
    settings: CounterSettings

class DataRepository:
    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("BEGIN")
        try:
            legacy = self._has_legacy_counter_schema()
            if legacy:
                self.conn.execute("ALTER TABLE guilds RENAME TO guilds_legacy")
                self.conn.execute("ALTER TABLE counter_users RENAME TO counter_users_legacy")

            for statement in SCHEMA:
                self.conn.execute(statement)

            if legacy:
                self._migrate_legacy_counter()
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def _has_legacy_counter_schema(self) -> bool:
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(guilds)")}
        return "counter_send_channel_id" in columns

    def _migrate_legacy_counter(self):
        # カウンターがギルド単位（guilds の列）だった頃の DB を、チャンネル単位のテーブルへ移す。
        # 全環境の DB が移行済みになれば、この処理と _has_legacy_counter_schema は削除してよい。
        self.conn.execute(
            "INSERT INTO guilds (guild_id, active_auto_connect) SELECT guild_id, active_auto_connect FROM guilds_legacy"
        )
        self.conn.execute(
            """
            INSERT INTO counters (guild_id, channel_id, last_message_id, title, multiplier, total_title)
            SELECT guild_id, counter_send_channel_id, counter_last_message_id,
                   counter_title, counter_multiplier, counter_total_title
            FROM guilds_legacy WHERE counter_send_channel_id != 0
            """
        )
        self.conn.execute(
            """
            INSERT INTO counter_users (guild_id, channel_id, user_id, count)
            SELECT u.guild_id, g.counter_send_channel_id, u.user_id, u.count
            FROM counter_users_legacy u JOIN guilds_legacy g ON g.guild_id = u.guild_id
            WHERE g.counter_send_channel_id != 0
            ORDER BY u.rowid
            """
        )
        self.conn.execute("DROP TABLE counter_users_legacy")
        self.conn.execute("DROP TABLE guilds_legacy")

    def close(self):
        self.conn.close()

    def _fetch_one(self, sql: str, params: tuple):
        row = self.conn.execute(sql, params).fetchone()
        return row[0] if row else None

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
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO guilds (guild_id, active_auto_connect) VALUES (?, ?)
                ON CONFLICT (guild_id) DO UPDATE SET active_auto_connect = excluded.active_auto_connect
                """,
                (guild_id, int(enabled))
            )

    def get_counter(self, guild_id: int, channel_id: int) -> Counter | None:
        row = self.conn.execute(
            """
            SELECT last_message_id, title, multiplier, total_title
            FROM counters WHERE guild_id = ? AND channel_id = ?
            """,
            (guild_id, channel_id)
        ).fetchone()
        return Counter(row[0], CounterSettings(*row[1:])) if row else None

    def set_counter(self, guild_id: int, channel_id: int, settings: CounterSettings, last_message_id: int):
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO counters (guild_id, channel_id, last_message_id, title, multiplier, total_title)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (guild_id, channel_id, last_message_id, settings.title, settings.multiplier, settings.total_title)
            )

    def set_counter_last_message_id(self, guild_id: int, channel_id: int, last_message_id: int):
        with self.conn:
            self.conn.execute(
                "UPDATE counters SET last_message_id = ? WHERE guild_id = ? AND channel_id = ?",
                (last_message_id, guild_id, channel_id)
            )

    def delete_counter(self, guild_id: int, channel_id: int):
        with self.conn:
            self.conn.execute(
                "DELETE FROM counters WHERE guild_id = ? AND channel_id = ?",
                (guild_id, channel_id)
            )

    def get_counter_users(self, guild_id: int, channel_id: int) -> dict[int, int]:
        rows = self.conn.execute(
            "SELECT user_id, count FROM counter_users WHERE guild_id = ? AND channel_id = ? ORDER BY rowid",
            (guild_id, channel_id)
        ).fetchall()
        return {user_id: count for user_id, count in rows}

    def set_counter_users(self, guild_id: int, channel_id: int, member_id: int, incremental: int):
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO counter_users (guild_id, channel_id, user_id, count) VALUES (?, ?, ?, ?)
                ON CONFLICT (guild_id, channel_id, user_id) DO UPDATE SET count = count + excluded.count
                """,
                (guild_id, channel_id, member_id, incremental)
            )

    def get_ban_users(self, guild_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT user_id FROM counter_ban_users WHERE guild_id = ?",
            (guild_id,)
        ).fetchall()
        return [user_id for (user_id,) in rows]

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
