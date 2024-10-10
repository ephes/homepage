from django import forms

from homepage.resume.models import CVToken


class CVTokenForm(forms.Form):
    token = forms.CharField(max_length=255, required=True, label="Token")

    def clean_token(self):
        token = self.cleaned_data["token"]
        if not token:
            raise forms.ValidationError("Token required.")
        try:
            return CVToken.objects.get(token=token)
        except CVToken.DoesNotExist:
            raise forms.ValidationError("Invalid token.")
