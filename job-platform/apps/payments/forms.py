from django import forms
from .models import Payment


class PaymentMethodForm(forms.Form):
    method = forms.ChoiceField(choices=Payment.Method.choices, widget=forms.RadioSelect)
