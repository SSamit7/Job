from django import forms
from .models import Application


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["cover_letter", "proposed_amount"]
        widgets = {"cover_letter": forms.Textarea(attrs={"rows": 4})}
