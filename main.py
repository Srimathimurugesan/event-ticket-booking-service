
from datetime import date
from fastapi import Query
import re
import sqlite3
import json

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import create_tables, get_connection

app = FastAPI(
    title="Event Ticket Booking Service",
    description="REST API for events and ticket bookings",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


@app.on_event("startup")
def startup():
    create_tables()


# Return all request validation errors as HTTP 400

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Malformed JSON or an empty request body
    if exc.body is None or any(
        error["type"] == "json_invalid"
        for error in exc.errors()
    ):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid-request"},
        )

    # Collect all field validation errors
    errors = {}

    for error in exc.errors():
        field = str(error["loc"][-1])
        errors[field] = error["msg"]

    return JSONResponse(
        status_code=400,
        content={
            "error": "validation-failed",
            "fields": errors,
        },
    )


# Validate incoming event data
class EventCreate(BaseModel):
    name: str
    venue: str
    category: str
    event_date: date
    total_seats: int
    base_price: float



@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")



@app.post("/api/events", status_code=201)
def create_event(event: EventCreate):
    errors = {}

    # Name validation
    if len(event.name.strip()) < 3:
        errors["name"] = "Event name must contain at least 3 characters."

    # Venue validation
    if len(event.venue.strip()) < 2:
        errors["venue"] = "Venue must contain at least 2 characters."

    # Only allow the specified event categories
    allowed_categories = {"concert", "sports", "tech_meetup", "theater"}
    if event.category not in allowed_categories:
        errors["category"] = (
            "Category must be concert, sports, tech_meetup, or theater."
        )

    # Date validation
    if event.event_date < date.today():
        errors["event_date"] = "Event date cannot be in the past."

    # Minimum seat capacity is 10
    if event.total_seats < 10:
        errors["total_seats"] = "Total seats must be at least 10."

    # Price validation
    if event.base_price <= 0:
        errors["base_price"] = "Base price must be greater than zero."

    # Return every field validation error together
    if errors:
        return JSONResponse(
            status_code=400,
            content={"error": "validation-failed", "fields": errors},
        )

    try:
        with get_connection() as connection:
            # Event name and date must be unique together
            existing = connection.execute(
                """
                SELECT id FROM events
                WHERE LOWER(name) = LOWER(?) AND event_date = ?
                """,
                (event.name.strip(), event.event_date.isoformat()),
            ).fetchone()

            if existing:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "validation-failed",
                        "fields": {
                            "name": "An event with this name and date already exists."
                        },
                    },
                )

            cursor = connection.execute(
                """
                INSERT INTO events
                (name, venue, category, event_date, total_seats, base_price)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.name.strip(),
                    event.venue.strip(),
                    event.category,
                    event.event_date.isoformat(),
                    event.total_seats,
                    event.base_price,
                ),
            )

            event_id = cursor.lastrowid

            saved_event = connection.execute(
                "SELECT * FROM events WHERE id = ?", (event_id,)
            ).fetchone()

            return dict(saved_event)

    except sqlite3.Error:
        return JSONResponse(
            status_code=500,
            content={"error": "internal-error"},
        )


@app.get("/api/events/{event_id}")
def get_event(event_id: int):
    try:
        with get_connection() as connection:
            event = connection.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()

            if event is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": "not-found"},
                )

            return dict(event)

    except sqlite3.Error:
        return JSONResponse(
            status_code=500,
            content={"error": "internal-error"},
        )

        
# Request structure for creating a booking
class BookingCreate(BaseModel):
    event_id: int
    customer_name: str
    customer_email: str
    seat_numbers: list[int]


@app.post("/api/bookings", status_code=201)
def create_booking(booking: BookingCreate):
    errors = {}

    # 1. Validate customer details and seat numbers
    if booking.event_id <= 0:
        errors["event_id"] = "Event ID must be positive."

    if len(booking.customer_name.strip()) < 2:
        errors["customer_name"] = "Customer name must contain at least 2 characters."

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", booking.customer_email):
        errors["customer_email"] = "Enter a valid email address."

    if not booking.seat_numbers:
        errors["seat_numbers"] = "Select at least one seat."
    elif len(booking.seat_numbers) > 6:
        errors["seat_numbers"] = "You can request at most 6 seats per booking."

    if len(set(booking.seat_numbers)) != len(booking.seat_numbers):
        errors["seat_numbers"] = "Duplicate seat numbers are not allowed."

    if any(seat <= 0 for seat in booking.seat_numbers):
        errors["seat_numbers"] = "Seat numbers must be positive."

    if errors:
        return JSONResponse(
            status_code=400,
            content={"error": "validation-failed", "fields": errors},
        )

    try:
        with get_connection() as connection:
            # Keep booking checks and insertion in one transaction
            connection.execute("BEGIN IMMEDIATE")

            event = connection.execute(
                "SELECT * FROM events WHERE id = ?",
                (booking.event_id,),
            ).fetchone()

            # 2. Check whether the event exists
            if event is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": "not-found"},
                )

            # 3. Check seat numbers against the event capacity
            if any(seat > event["total_seats"] for seat in booking.seat_numbers):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "validation-failed",
                        "fields": {
                            "seat_numbers": (
                                f"Seat numbers must be between 1 and "
                                f"{event['total_seats']}."
                            )
                        },
                    },
                )

            # Find seats belonging to confirmed bookings only
            confirmed_bookings = connection.execute(
                """
                SELECT seat_numbers FROM bookings
                WHERE event_id = ? AND status = 'CONFIRMED'
                """,
                (booking.event_id,),
            ).fetchall()

            booked_seats = set()
            for row in confirmed_bookings:
                booked_seats.update(json.loads(row["seat_numbers"]))

            # Check the customer's existing confirmed seat count
            customer_rows = connection.execute(
                """
                SELECT COALESCE(SUM(seats), 0) AS total_seats
                FROM bookings
                WHERE event_id = ?
                  AND LOWER(customer_email) = LOWER(?)
                  AND status = 'CONFIRMED'
                """,
                (booking.event_id, booking.customer_email.strip()),
            ).fetchone()

            customer_seats = customer_rows["total_seats"]

            # 4. Apply booking business rules
            rejection_reason = None

            if date.fromisoformat(event["event_date"]) < date.today():
                rejection_reason = "the event is already over"

            elif booked_seats.intersection(booking.seat_numbers):
                rejection_reason = "the seats are already booked"

            elif customer_seats + len(booking.seat_numbers) > 6:
                rejection_reason = (
                    "customer already holds the maximum seats for this event"
                )

            # 5. Calculate ticket price and discounts
            if rejection_reason:
                status = "REJECTED"
                price_per_seat = 0.0
                total_amount = 0.0
            else:
                status = "CONFIRMED"
                price = float(event["base_price"])

                days_until_event = (
                    date.fromisoformat(event["event_date"]) - date.today()
                ).days

                # Early-bird discount: 10% when booked 30+ days ahead
                if days_until_event >= 30:
                    price *= 0.90

                # Group discount: an additional 5% for 4+ seats
                if len(booking.seat_numbers) >= 4:
                    price *= 0.95

                price_per_seat = round(price + 1e-9, 2)
                total_amount = round(
                    price_per_seat * len(booking.seat_numbers) + 1e-9, 2
                )

            # 6. Save confirmed and rejected bookings
            cursor = connection.execute(
                """
                INSERT INTO bookings (
                    event_id, customer_name, customer_email,
                    seat_numbers, seats, price_per_seat,
                    total_amount, status, rejection_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking.event_id,
                    booking.customer_name.strip(),
                    booking.customer_email.strip(),
                    json.dumps(booking.seat_numbers),
                    len(booking.seat_numbers),
                    price_per_seat,
                    total_amount,
                    status,
                    rejection_reason,
                ),
            )

            saved_booking = connection.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()

            return dict(saved_booking)

    except sqlite3.Error:
        return JSONResponse(
            status_code=500,
            content={"error": "internal-error"},
        )


        
@app.get("/api/bookings/{booking_id}")
def get_booking(booking_id: int):
    try:
        with get_connection() as connection:
            booking = connection.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,),
            ).fetchone()

            if booking is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": "not-found"},
                )

            result = dict(booking)
            result["seat_numbers"] = json.loads(result["seat_numbers"])
            return result

    except sqlite3.Error:
        return JSONResponse(
            status_code=500,
            content={"error": "internal-error"},
        )


        
@app.get("/api/events/{event_id}/bookings")
def list_event_bookings(
    event_id: int,
    status: str | None = Query(default=None),
):
    # Validate the optional status filter
    if status is not None and status not in {"CONFIRMED", "REJECTED"}:
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation-failed",
                "fields": {
                    "status": "Status must be CONFIRMED or REJECTED."
                },
            },
        )

    try:
        with get_connection() as connection:
            # Check whether the event exists
            event = connection.execute(
                "SELECT id FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()

            if event is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": "not-found"},
                )

            # Return bookings, newest first
            if status is None:
                rows = connection.execute(
                    """
                    SELECT * FROM bookings
                    WHERE event_id = ?
                    ORDER BY booked_on DESC, id DESC
                    """,
                    (event_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM bookings
                    WHERE event_id = ? AND status = ?
                    ORDER BY booked_on DESC, id DESC
                    """,
                    (event_id, status),
                ).fetchall()

            results = []
            for row in rows:
                item = dict(row)
                item["seat_numbers"] = json.loads(item["seat_numbers"])
                results.append(item)

            return results

    except sqlite3.Error:
        return JSONResponse(
            status_code=500,
            content={"error": "internal-error"},
        )




@app.get("/api/events/{event_id}/seats")
def get_event_seats(event_id: int):
    try:
        with get_connection() as connection:
            event = connection.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()

            if event is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": "not-found"},
                )

            rows = connection.execute(
                """
                SELECT seat_numbers FROM bookings
                WHERE event_id = ? AND status = 'CONFIRMED'
                """,
                (event_id,),
            ).fetchall()

            booked_seats = set()

            for row in rows:
                booked_seats.update(json.loads(row["seat_numbers"]))

            booked_seats = sorted(booked_seats)

            available_seats = [
                seat
                for seat in range(1, event["total_seats"] + 1)
                if seat not in booked_seats
            ]

            return {
                "event_id": event_id,
                "total_seats": event["total_seats"],
                "booked_seats": booked_seats,
                "available_seats": available_seats,
            }

    except sqlite3.Error:
        return JSONResponse(
            status_code=500,
            content={"error": "internal-error"},
        )



@app.get("/api/events/{event_id}/summary")
def get_event_summary(event_id: int):
    try:
        with get_connection() as connection:
            event = connection.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()

            if event is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": "not-found"},
                )

            # Aggregate confirmed bookings only
            totals = connection.execute(
                """
                SELECT
                    COALESCE(SUM(seats), 0) AS seats_sold,
                    COALESCE(SUM(total_amount), 0) AS total_revenue
                FROM bookings
                WHERE event_id = ? AND status = 'CONFIRMED'
                """,
                (event_id,),
            ).fetchone()

            seats_sold = totals["seats_sold"]
            total_revenue = round(totals["total_revenue"] + 1e-9, 2)
            total_seats = event["total_seats"]
            available_seats = total_seats - seats_sold

            occupancy_pct = round(
                seats_sold / total_seats * 100, 1
            )

            if occupancy_pct < 40:
                demand_band = "low"
            elif occupancy_pct <= 75:
                demand_band = "medium"
            else:
                demand_band = "high"

            return {
                "event_id": event_id,
                "event_name": event["name"],
                "total_seats": total_seats,
                "seats_sold": seats_sold,
                "available_seats": available_seats,
                "total_revenue": total_revenue,
                "occupancy_pct": occupancy_pct,
                "demand_band": demand_band,
            }

    except sqlite3.Error:
        return JSONResponse(
            status_code=500,
            content={"error": "internal-error"},
        )



