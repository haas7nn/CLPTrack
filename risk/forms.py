"""The form on the score settings page."""
from django import forms

from .models import ScoreSettings


class ScoreSettingsForm(forms.ModelForm):
    class Meta:
        model = ScoreSettings
        fields = ["overdue", "lateness", "supervision", "proximity", "actions", "amber_from", "red_from"]

    def clean(self):
        """The five weights must add up to 100, and amber must start before red."""
        data = super().clean()
        if any(data.get(name) is None for name in self.Meta.fields):
            return data
        total = sum(data[name] for name in ScoreSettings.INDICATORS)
        if total != 100:
            raise forms.ValidationError(f"The five weights must add up to 100. They add up to {total}.")
        if not 0 < data["amber_from"] < data["red_from"] <= 100:
            raise forms.ValidationError("Amber must start above 0 and below red, and red at 100 or below.")
        return data
