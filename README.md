# ICT Service Management System

A web-based ICT support and ticket management system built for company use. It allows employees to submit IT support tickets and enables technicians and administrators to manage, track, and resolve them efficiently.

## Features

- Submit and track IT support tickets
- Ticket status updates (Pending, In Progress, Resolved, Closed)
- Priority levels (Low, Medium, High, Critical)
- Role-based access control (Admin, Technician, User)
- Admin dashboard with statistics and reports
- User management (Admin only)
- Notifications system
- Mobile responsive interface

## Tech Stack

- **Backend:** Python, Django
- **Frontend:** HTML, CSS, Bootstrap 5
- **Database:** SQLite
- **Hosting:** PythonAnywhere

## Live Demo

[alghafir.pythonanywhere.com](https://alghafir.pythonanywhere.com)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/najla5002/ict-service-management.git
   ```

2. Navigate to the project folder:
   ```
   cd ict-service-management
   ```

3. Install dependencies:
   ```
   pip install django reportlab pillow
   ```

4. Run migrations:
   ```
   python manage.py migrate
   ```

5. Start the server:
   ```
   python manage.py runserver
   ```

6. Open your browser and go to `http://127.0.0.1:8000`

## Developer

**Najla Nassor Mohamed**

---

© 2026 ICT Service Management System. All rights reserved.
