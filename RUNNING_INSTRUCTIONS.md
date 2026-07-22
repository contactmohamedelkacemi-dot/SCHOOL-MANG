# School Management System

## How to Run the Web App

Open a terminal or PowerShell in the `c:\NEWAPP` directory and run the following commands:

**1. Activate the virtual environment:**
```powershell
.\venv\Scripts\Activate.ps1
```
*(If you are using Command Prompt instead of PowerShell, use `venv\Scripts\activate`)*

**2. Start the Django Development Server:**
```powershell
python manage.py runserver
```

**3. Access the Application:**
Open your web browser and navigate to:
**[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

To stop the server at any time, press `Ctrl + C` in the terminal.

---

## Default Login Credentials

If you have reset the database using the `reset_db.py` script, the following default superuser account is created for you:

### Admin Account
- **Username:** `admin`
- **Password:** `admin`
- **Email:** `admin@example.com`

### Test Teacher (Formateur) Account
To create a test teacher account, run `python create_teacher.py`. You can then log in using:
- **Username:** `teacher1`
- **Password:** `password123`
- **Email:** `teacher1@example.com`

---

## Database Reset (Optional)

If you ever need to completely reset the database and re-apply all migrations, you can run:

```powershell
python reset_db.py
```
*Note: This will delete the existing database and re-create it with the default admin user.*
