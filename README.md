# Movie Ticket Booking Management Application

A Flask + SQLite web application based on the SkillWallet project brief.

## Main user stories implemented
- US-001: Submit Movie Ticket Request
- US-002: Check Show Availability
- US-003: Calculate Booking Cost
- US-004: Confirm Booking Request
- US-005: Maintain Movie and Show Data
- US-006: Review Booking Details
- US-007: Process Ticket Booking
- US-008: Notify Booking Confirmation
- US-009: Define Booking SLA
- US-010: Route Booking Request by Show Type

## Technology
- Frontend: HTML, CSS, JavaScript
- Backend: Python Flask
- Database: SQLite
- API: Flask JSON endpoints

## Run in VS Code
1. Open this folder in VS Code.
2. Create a virtual environment:
   `python -m venv venv`
3. Activate it on Windows:
   `venv\Scripts\activate`
4. Install packages:
   `pip install -r requirements.txt`
5. Run:
   `python app.py`
6. Open Chrome and visit:
   `http://127.0.0.1:5000`

The SQLite database is created automatically on first run.

## Workflow
Customer -> Select Movie/Show -> Check Seats -> Select Seats -> Calculate Cost
-> Submit Request -> Review Details -> Confirm Booking -> Notification -> Dashboard

## Demo
The app contains sample movies and shows. New booking requests receive a 30-minute SLA due time. Confirmed bookings are reflected in the dashboard and a notification event is recorded.
