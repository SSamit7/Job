from django import forms
from .models import Job


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "category",
            "title",
            "description",
            "location",
            "address",
            "latitude",
            "longitude",
            "scheduled_date",
            "start_time",
            "estimated_duration_hours",
            "budget",
            "deadline",
            "image",
        ]
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "scheduled_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 5}),
            "address": forms.TextInput(attrs={"placeholder": "Landmark or full address of the work site"}),
            "latitude": forms.NumberInput(attrs={"step": "any", "placeholder": "Optional, e.g. 27.700769"}),
            "longitude": forms.NumberInput(attrs={"step": "any", "placeholder": "Optional, e.g. 85.300140"}),
            "estimated_duration_hours": forms.NumberInput(attrs={"step": "0.5", "placeholder": "e.g. 2"}),
        }


class JobSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Keyword")
    location = forms.CharField(required=False)
    min_budget = forms.DecimalField(required=False)
    max_budget = forms.DecimalField(required=False)
