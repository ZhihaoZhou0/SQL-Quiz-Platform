import os
import re

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def run_quiz_query(sql):
    """Execute a read-only SQL query against Supabase PostgreSQL."""

    query = sql.strip()

    # Allow only a single SELECT statement for this quiz.
    if not re.match(r"^SELECT\b", query, flags=re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")

    if query.rstrip(";").find(";") != -1:
        raise ValueError("Only one SQL statement is allowed.")

    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("QUIZ_DB_USER"),
        password=os.getenv("QUIZ_DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        sslmode="require",
        connect_timeout=10,
        options="-c default_transaction_read_only=on",
    )

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout = '5s';")
                cur.execute(query)

                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchmany(100)

                return columns, rows
    finally:
        conn.close()