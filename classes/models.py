from django.db import models
from teachers.models import Teacher
from students.models import Student

class Class(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Module(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    coefficient = models.FloatField(default=1)

    def __str__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=100)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    teachers = models.ManyToManyField(Teacher, related_name='groups')
    students = models.ManyToManyField(Student, related_name='groups')

    class Meta:
        unique_together = ('name', 'class_assigned')

    def __str__(self):
        return f"{self.class_assigned.name} - {self.name}"

