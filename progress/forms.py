"""The forms people fill in: upload work, record a meeting, leave feedback."""
from django import forms

from .models import Feedback, Meeting

ALLOWED_TYPES = (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".png", ".jpg", ".jpeg")
MAX_SIZE_MB = 20


class SubmissionForm(forms.Form):
    file = forms.FileField()
    note = forms.CharField(max_length=300, required=False, label="Note for your supervisor (optional)")

    def clean_file(self):
        """Only accept normal document types, and nothing huge."""
        f = self.cleaned_data["file"]
        name = f.name.lower()
        if not name.endswith(ALLOWED_TYPES):
            raise forms.ValidationError("Please upload a PDF, Word, PowerPoint, zip or image file.")
        if f.size > MAX_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(f"The file is too big. The limit is {MAX_SIZE_MB} MB.")
        return f


class MeetingForm(forms.ModelForm):
    # the student types one agreed action per line, we turn each line into an Action row
    actions = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}),
                              help_text="One agreed action per line")

    class Meta:
        model = Meeting
        fields = ["held_on", "discussed"]
        widgets = {"held_on": forms.DateInput(attrs={"type": "date"}), "discussed": forms.Textarea(attrs={"rows": 4})}

    def action_lines(self):
        return [line.strip() for line in self.cleaned_data.get("actions", "").splitlines() if line.strip()]


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3})}
