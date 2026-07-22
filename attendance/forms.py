from django import forms
from .models import Justification

class JustificationForm(forms.ModelForm):
    sessions = forms.MultipleChoiceField(
        choices=[(1, 'Session 1'), (2, 'Session 2'), (3, 'Session 3'), (4, 'Session 4')],
        widget=forms.CheckboxSelectMultiple,
        help_text="Select the sessions covered by this justification."
    )

    class Meta:
        model = Justification
        fields = ['student', 'date', 'reason', 'image', 'status']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'student': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class StudentJustificationForm(forms.ModelForm):

    class Meta:
        model = Justification
        fields = ['reason', 'image']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Please provide a detailed reason for your absence...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
