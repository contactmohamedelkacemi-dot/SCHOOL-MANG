import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')

APPS = ['accounts', 'students', 'teachers', 'classes', 'attendance', 'grades', 'schedule', 'dashboard', 'school_communication']

print("1. Deleting db.sqlite3...")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("   Deleted.")
else:
    print("   Not found.")

print("2. Cleaning migrations folders...")
for app in APPS:
    migrations_dir = os.path.join(BASE_DIR, app, 'migrations')
    if os.path.exists(migrations_dir):
        shutil.rmtree(migrations_dir)
        print(f"   Deleted {migrations_dir}")
    
    # Recreate migrations folder with __init__.py
    os.makedirs(migrations_dir, exist_ok=True)
    with open(os.path.join(migrations_dir, '__init__.py'), 'w') as f:
        pass
    print(f"   Recreated {migrations_dir} with __init__.py")

print("3. Making new migrations...")
os.system(sys.executable + ' manage.py makemigrations ' + ' '.join(APPS))

print("4. Applying migrations...")
os.system(sys.executable + ' manage.py migrate')

print("5. Creating default superuser (admin / admin)...")
os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'admin'
os.system(sys.executable + ' manage.py createsuperuser --noinput --username admin --email admin@example.com')

print("\n--- RESET COMPLETE ---")
print("You can now run: python manage.py runserver")
print("Log in with username: admin | password: admin")
