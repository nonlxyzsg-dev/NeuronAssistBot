from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from config import DATABASE_URL


@contextmanager
def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    connection = psycopg2.connect(DATABASE_URL)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def get_cursor():
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            yield cursor
            connection.commit()



def init_db():
    with get_cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS verified_users (
                user_id BIGINT PRIMARY KEY,
                verified_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS moderation_log (
                id SERIAL PRIMARY KEY,
                action TEXT NOT NULL,
                user_id BIGINT,
                message_id BIGINT,
                chat_id BIGINT,
                details TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS spam_votes (
                vote_id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                target_message_id BIGINT NOT NULL,
                target_user_id BIGINT,
                poll_message_id BIGINT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                closed_at TIMESTAMPTZ
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS spam_vote_voters (
                vote_id INT REFERENCES spam_votes(vote_id) ON DELETE CASCADE,
                voter_id BIGINT NOT NULL,
                vote TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (vote_id, voter_id)
            );
            """
        )



def is_verified_user(user_id: int) -> bool:
    with get_cursor() as cursor:
        cursor.execute("SELECT 1 FROM verified_users WHERE user_id = %s", (user_id,))
        return cursor.fetchone() is not None



def add_verified_user(user_id: int):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO verified_users (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user_id,),
        )



def list_verified_users():
    with get_cursor() as cursor:
        cursor.execute("SELECT user_id, verified_at FROM verified_users ORDER BY verified_at")
        return cursor.fetchall()



def log_action(action: str, user_id: int | None, message_id: int | None, chat_id: int | None, details: str | None):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO moderation_log (action, user_id, message_id, chat_id, details)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (action, user_id, message_id, chat_id, details),
        )



def get_spam_vote_by_target(chat_id: int, target_message_id: int):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM spam_votes
            WHERE chat_id = %s AND target_message_id = %s AND closed_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (chat_id, target_message_id),
        )
        return cursor.fetchone()



def create_spam_vote(chat_id: int, target_message_id: int, target_user_id: int | None, poll_message_id: int):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO spam_votes (chat_id, target_message_id, target_user_id, poll_message_id)
            VALUES (%s, %s, %s, %s)
            RETURNING vote_id
            """,
            (chat_id, target_message_id, target_user_id, poll_message_id),
        )
        return cursor.fetchone()["vote_id"]



def add_spam_vote(vote_id: int, voter_id: int, vote: str) -> bool:
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO spam_vote_voters (vote_id, voter_id, vote)
            VALUES (%s, %s, %s)
            ON CONFLICT (vote_id, voter_id) DO NOTHING
            """,
            (vote_id, voter_id, vote),
        )
        return cursor.rowcount > 0



def count_spam_votes(vote_id: int):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_votes,
                SUM(CASE WHEN vote = 'spam' THEN 1 ELSE 0 END) AS spam_votes
            FROM spam_vote_voters
            WHERE vote_id = %s
            """,
            (vote_id,),
        )
        row = cursor.fetchone()
        return {
            "total": row["total_votes"] or 0,
            "spam": row["spam_votes"] or 0,
        }



def close_spam_vote(vote_id: int):
    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE spam_votes
            SET closed_at = NOW()
            WHERE vote_id = %s
            """,
            (vote_id,),
        )



def get_spam_vote(vote_id: int):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM spam_votes WHERE vote_id = %s", (vote_id,))
        return cursor.fetchone()


def list_open_spam_votes():
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM spam_votes WHERE closed_at IS NULL")
        return cursor.fetchall()
