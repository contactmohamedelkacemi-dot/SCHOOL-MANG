from django import forms
from .models import Teacher

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['full_name', 'email', 'phone', 'cin', 'address', 'date_of_birth', 'gender', 'specialty', 'profile_image', 'cv']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        if 'gender' in self.fields:
            self.fields['gender'].widget.attrs['class'] = 'form-select'

class TeacherProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['phone', 'address', 'profile_image']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
