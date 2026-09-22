# Project Flow

Customer
  -> Browse Movies & Shows
  -> Select Show
  -> Check Seat Availability
  -> Select Seats
  -> Calculate Booking Cost
  -> Submit Booking Request
  -> Review Booking Details
  -> Confirm Booking
  -> Notification Event
  -> Staff Dashboard

Staff
  -> Dashboard
  -> Review Pending Requests
  -> View Booking Details
  -> Maintain Movie Data

Business Rules
- Only available seats can be selected.
- A booking receives a 30-minute SLA due time.
- Booking cost = number of seats × show price.
- Confirmed bookings are counted in dashboard revenue.
- Booking events are stored for case lifecycle tracking.
