@echo off
echo Setting up virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo Installing requirements...
pip install -r requirements.txt

echo Applying migrations...
python manage.py makemigrations accounts students teachers classes attendance grades schedule dashboard school_communication
python manage.py migrate

echo Setup complete. You can now create a superuser or run the server.
echo To run the server: python manage.py runserver
pause
