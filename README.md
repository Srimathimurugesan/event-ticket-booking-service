# Event Ticket Booking Service

## Project Overview
The Event Ticket Booking Service is a full-stack web application that allows users to create events, view event details, book tickets, check booking information, and view seat availability and event summaries.

## Technologies Used
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, FastAPI
- **Database:** SQLite
- **API Documentation:** FastAPI Swagger UI

## Features
- Create and retrieve events
- Book event tickets
- Retrieve booking details
- Check seat availability
- View event summaries and booking history
- Validate booking requests and handle rejected bookings

## Project Structure
- `main.py` — FastAPI application and API endpoints
- `database.py` — Database connection and table setup
- `event_booking.db` — SQLite database
- `static/index.html` — Frontend webpage
- `static/style.css` — Frontend styling
- `static/script.js` — Frontend logic and API integration
- `requirements.txt` — Python dependencies

## How to Run the Project

### 1. Install Dependencies
Open the terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

### 2. Start the Backend

```bash
uvicorn main:app --reload
```

### 3. Open the Application
Open this URL in your browser:

http://127.0.0.1:8000

### 4. View API Documentation
Open:

http://127.0.0.1:8000/docs

## Database
The application uses SQLite to store event and booking information. The database file is `event_booking.db`.

## Purpose
This project demonstrates frontend-backend integration, REST API development, database operations, and event ticket booking logic.