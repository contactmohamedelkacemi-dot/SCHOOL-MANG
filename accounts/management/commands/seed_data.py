import random
from datetime import time
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from accounts.models import User
from teachers.models import Teacher
from classes.models import Class, Module
from students.models import Student
from attendance.models import Attendance
from grades.models import Grade
from schedule.models import Schedule

class Command(BaseCommand):
    help = 'Seed database with sample data'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fake = Faker()
        
        self.stdout.write('Deleting old data...')
        # Clear existing data to prevent duplicates on multiple runs
        User.objects.exclude(is_superuser=True).delete()
        Class.objects.all().delete()
        
        self.stdout.write('Creating Admin user...')
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin', role='admin')
        else:
            admin = User.objects.get(username='admin')
            admin.set_password('admin')
            admin.role = 'admin'
            admin.save()

        self.stdout.write('Creating Classes...')
        classes = []
        for class_name in ['1ère Année Bac', '2ème Année Bac', 'Tronc Commun', 'BTS 1', 'BTS 2']:
            c = Class.objects.create(name=class_name)
            classes.append(c)

        self.stdout.write('Creating Teachers...')
        teachers = []
        specialties = ['Mathematics', 'Physics', 'Computer Science', 'English', 'French']
        for i in range(1, 6):
            user = User.objects.create_user(
                username=f'teacher{i}',
                password='password123',
                role='formateur',
                email=fake.email()
            )
            teacher = Teacher.objects.create(
                user=user,
                full_name=fake.name(),
                email=user.email,
                phone=fake.phone_number()[:20],
                cin=fake.unique.bothify(text='??#######').upper()[:20],
                address=fake.address(),
                date_of_birth=fake.date_of_birth(minimum_age=25, maximum_age=60),
                gender=random.choice(['Male', 'Female']),
                specialty=random.choice(specialties)
            )
            teachers.append(teacher)

        self.stdout.write('Creating Modules...')
        modules = []
        for c in classes:
            # Assign 3-4 modules per class
            for _ in range(random.randint(3, 4)):
                module = Module.objects.create(
                    name=f"{random.choice(['Math', 'Physics', 'Programming', 'Language', 'Science'])} {random.randint(101, 499)}",
                    teacher=random.choice(teachers),
                    class_assigned=c,
                    coefficient=round(random.uniform(1.0, 3.0), 1)
                )
                modules.append(module)

        self.stdout.write('Creating Students...')
        students = []
        for i in range(1, 21):
            user = User.objects.create_user(
                username=f'student{i}',
                password='password123',
                role='stagiaire',
                email=fake.email()
            )
            student = Student.objects.create(
                user=user,
                full_name=fake.name(),
                code=fake.unique.bothify(text='STU-#####'),
                date_of_birth=fake.date_of_birth(minimum_age=15, maximum_age=22),
                class_assigned=random.choice(classes),
                address=fake.address(),
                parent_name=fake.name(),
                parent_phone=fake.phone_number()[:20]
            )
            students.append(student)

        self.stdout.write('Creating Attendance and Grades...')
        statuses = ['Present', 'Absent', 'Late']
        for student in students:
            # Find modules for this student's class
            student_modules = [m for m in modules if m.class_assigned == student.class_assigned]
            for module in student_modules:
                # Grades
                Grade.objects.create(
                    student=student,
                    module=module,
                    score=round(random.uniform(5.0, 20.0), 2)
                )
                # Attendance records
                for _ in range(random.randint(2, 5)):
                    Attendance.objects.create(
                        student=student,
                        module=module,
                        date=fake.date_between(start_date='-30d', end_date='today'),
                        status=random.choices(statuses, weights=[70, 20, 10])[0]
                    )

        self.stdout.write('Creating Schedule...')
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for c in classes:
            class_modules = [m for m in modules if m.class_assigned == c]
            if not class_modules:
                continue
            for day in days:
                for hour in [8, 10, 14, 16]:
                    if random.random() > 0.3: # 70% chance of having a class at this time
                        Schedule.objects.create(
                            class_assigned=c,
                            module=random.choice(class_modules),
                            day=day,
                            time=time(hour=hour, minute=0)
                        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded the database!'))
