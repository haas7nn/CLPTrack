"""The form on the Add people page."""
from django import forms


class ImportForm(forms.Form):
    file = forms.FileField(label="CSV file")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a .csv file. In Excel choose Save As, CSV.")
        if f.size > 1024 * 1024:
            raise forms.ValidationError("The file is too big. The limit is 1 MB.")
        return f
