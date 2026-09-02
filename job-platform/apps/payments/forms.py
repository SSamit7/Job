from django import forms
from .models import Payment, WalletTopup


class PaymentMethodForm(forms.Form):
    method = forms.ChoiceField(choices=Payment.Method.choices, widget=forms.RadioSelect)


class TopupAmountForm(forms.ModelForm):
    """Used on the amount-entry step, after a top-up method has already been picked."""

    class Meta:
        model = WalletTopup
        fields = ["amount"]
        widgets = {
            "amount": forms.NumberInput(attrs={"min": "50", "step": "10", "placeholder": "e.g. 500", "autofocus": True}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount < 50:
            raise forms.ValidationError("Minimum top-up amount is Rs. 50.")
        return amount
