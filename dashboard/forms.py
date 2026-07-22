from django import forms
from django.contrib.auth import get_user_model
from classes.models import Class, Group

User = get_user_model()

class AdminUserCreationForm(forms.Form):
    ROLE_CHOICES = [
        ('formateur', 'Teacher (Formateur)'),
        ('stagiaire', 'Student (Stagiaire)'),
    ]
    
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select', 'id': 'roleSelector'}))
    
    # Common Fields
    full_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    # Optional Credentials (will be auto-generated if left blank)
    username = forms.CharField(max_length=150, required=False, help_text="Leave blank to auto-generate", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(max_length=128, required=False, help_text="Leave blank to auto-generate", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    # Teacher Specific
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control teacher-field'}))
    
    # Student Specific
    class_assigned = forms.ModelChoiceField(queryset=Class.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select student-field'}))
    group_assigned = forms.ModelChoiceField(queryset=Group.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select student-field'}))

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email
        
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        
        if role == 'stagiaire':
            if not cleaned_data.get('class_assigned'):
                self.add_error('class_assigned', 'Class assignment is required for students.')
                
        return cleaned_data

from teachers.models import Teacher
from students.models import Student

class TeacherProfileCompletionForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['cin', 'address', 'date_of_birth', 'gender', 'specialty', 'profile_image']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cin': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'specialty': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class StudentProfileCompletionForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['date_of_birth', 'address', 'parent_name', 'parent_phone', 'profile_image']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
