
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Store the database in the project folder
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "event_booking.db"


@contextmanager
def get_connection():
    """Create, manage, and close a database connection."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_tables():
    """Create the events and bookings tables if they do not exist."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                venue TEXT NOT NULL,
                category TEXT NOT NULL,
                event_date TEXT NOT NULL,
                total_seats INTEGER NOT NULL,
                base_price REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                seat_numbers TEXT NOT NULL,
                seats INTEGER NOT NULL,
                price_per_seat REAL NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('CONFIRMED', 'REJECTED')),
                rejection_reason TEXT,
                booked_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        """)


if __name__ == "__main__":
    create_tables()
    print("Database created successfully!")
    print(f"Database location: {DATABASE_PATH}")
