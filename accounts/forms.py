"""The form on the Add people page."""
from django import forms
from django.contrib.auth.password_validation import validate_password


class ImportForm(forms.Form):
    file = forms.FileField(label="CSV file")
    first_password = forms.CharField(label="First password for the new accounts", min_length=8,
                                     widget=forms.PasswordInput(render_value=True))

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a .csv file. In Excel choose Save As, CSV.")
        if f.size > 1024 * 1024:
            raise forms.ValidationError("The file is too big. The limit is 1 MB.")
        return f

    def clean_first_password(self):
        password = self.cleaned_data["first_password"]
        validate_password(password)   # the same rules Django applies to any password
        return password
