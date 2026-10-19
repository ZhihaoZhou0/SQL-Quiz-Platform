import os
import psycopg2
from psycopg2 import errors
from dotenv import load_dotenv

# Read .env. The same script works for Docker (localhost) and Supabase (cloud);
# only the values in .env change.
load_dotenv()

DB_NAME = os.getenv("POSTGRES_DB", "duke_restaurants")
DB_USER = os.getenv("POSTGRES_USER", "vscode")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "vscode")
DB_HOST = os.getenv("DB_HOST", "localhost")   # Docker publishes 5432 to your laptop
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SSLMODE = os.getenv("DB_SSLMODE", "prefer")  # Supabase requires "require"


def main():
    print(f"Connecting to {DB_NAME} at {DB_HOST}:{DB_PORT} as {DB_USER} ...")
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT, sslmode=DB_SSLMODE,
    )
    cur = conn.cursor()

    # READ
    print("\nTop rated places:")
    cur.execute("""
        SELECT name, rating
        FROM restaurants
        ORDER BY rating DESC, name ASC;
    """)
    for row in cur.fetchall():
        print(row)

    try:
        # CREATE
        print("\nInserting a new restaurant...")
        cur.execute("""
            INSERT INTO restaurants (name, address, distance_miles, rating, cuisine, avg_cost, personal_rank)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name;
        """, ("Queeny's", "321 E Chapel Hill St, Durham, NC", 1.5, 4.3, "American", 22.00, 7))
        print("Inserted:", cur.fetchone())

        # UPDATE
        print("\nUpdating rating for NuvoTaco...")
        cur.execute("""
            UPDATE restaurants
            SET rating = rating + 0.1
            WHERE name = %s
            RETURNING name, rating;
        """, ("NuvoTaco",))
        print("Updated:", cur.fetchone())

        # DELETE
        print("\nDeleting lowest-rated place...")
        cur.execute("""
            DELETE FROM restaurants
            WHERE id = (
              SELECT id FROM restaurants
              ORDER BY rating ASC, id ASC
              LIMIT 1
            )
            RETURNING id, name, rating;
        """)
        print("Deleted:", cur.fetchone())

        conn.commit()
        print("\nChanges committed.")

    except errors.InsufficientPrivilege as e:
        # Only happens if you connect with a read-only role (see Troubleshooting).
        conn.rollback()
        print("\nWrite blocked by the database:", str(e).strip().splitlines()[0])
        print("This connection is read-only, so INSERT/UPDATE/DELETE are refused and nothing was changed.")

    cur.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()