import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("QUIZ_DB_USER"),
    password=os.getenv("QUIZ_DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    sslmode=os.getenv("DB_SSLMODE"),
    connect_timeout=10,
)

try:
    with conn.cursor() as cur:
        cur.execute("SELECT name, rating FROM public.restaurants LIMIT 3;")
        print("Connection successful!")
        print("Restaurants:", cur.fetchall())

        cur.execute(
            "SELECT has_table_privilege("
            "current_user, 'public.restaurants', 'DELETE');"
        )
        print("Can delete restaurants:", cur.fetchone()[0])
finally:
    conn.close()