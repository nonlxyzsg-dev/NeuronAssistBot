import os
from typing import Optional

try:  # pragma: no cover - allow import without psycopg2 in constrained envs
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover
    class _PsycopgStub:  # type: ignore
        IntegrityError = RuntimeError

    psycopg2 = _PsycopgStub()
    RealDictCursor = None


DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5432/postgres"


def get_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not installed. Install requirements.txt first.")
    db_url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def init_db():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS verified_users (
                user_id BIGINT PRIMARY KEY,
                verified_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS moderation_log (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                action TEXT NOT NULL,
                message_id BIGINT,
                details TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS spam_votes (
                id SERIAL PRIMARY KEY,
                target_chat_id BIGINT NOT NULL,
                target_message_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                closed BOOLEAN DEFAULT FALSE,
                closed_reason TEXT,
                UNIQUE (target_chat_id, target_message_id)
            );

            CREATE TABLE IF NOT EXISTS spam_vote_voters (
                id SERIAL PRIMARY KEY,
                vote_id INTEGER REFERENCES spam_votes(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL,
                is_spam BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (vote_id, user_id)
            );
            """
        )
        conn.commit()


def is_user_verified(user_id: int) -> bool:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM verified_users WHERE user_id = %s", (user_id,))
        return cur.fetchone() is not None


def add_verified_user(user_id: int):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO verified_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (user_id,),
        )
        conn.commit()


def log_action(user_id: Optional[int], action: str, message_id: Optional[int] = None, details: Optional[str] = None):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO moderation_log (user_id, action, message_id, details) VALUES (%s, %s, %s, %s)",
            (user_id, action, message_id, details),
        )
        conn.commit()


def get_verified_users():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT user_id, verified_at FROM verified_users ORDER BY verified_at")
        return cur.fetchall()


def get_or_create_vote(chat_id: int, message_id: int) -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM spam_votes WHERE target_chat_id=%s AND target_message_id=%s",
            (chat_id, message_id),
        )
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute(
            "INSERT INTO spam_votes (target_chat_id, target_message_id) VALUES (%s, %s) RETURNING id",
            (chat_id, message_id),
        )
        vote_id = cur.fetchone()["id"]
        conn.commit()
        return vote_id


def add_vote(vote_id: int, user_id: int, is_spam: bool) -> bool:
    with get_connection() as conn, conn.cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO spam_vote_voters (vote_id, user_id, is_spam) VALUES (%s, %s, %s)",
                (vote_id, user_id, is_spam),
            )
            conn.commit()
            return True
        except psycopg2.IntegrityError:
            conn.rollback()
            return False


def count_spam_votes(vote_id: int) -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM spam_vote_voters WHERE vote_id=%s AND is_spam=TRUE",
            (vote_id,),
        )
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0


def close_vote(vote_id: int, reason: str):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE spam_votes SET closed=TRUE, closed_reason=%s WHERE id=%s",
            (reason, vote_id),
        )
        conn.commit()


def get_open_votes_older_than(seconds: int):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM spam_votes WHERE closed=FALSE AND (NOW() - created_at) > (%s || ' seconds')::interval",
            (seconds,),
        )
        return cur.fetchall()
