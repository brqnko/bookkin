from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    """Validate a review for a specific book and signed-in user."""

    def __init__(self, *args, book, reviewer, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = book
        self.reviewer = reviewer

    def clean(self):
        cleaned_data = super().clean()
        duplicate_review = Review.objects.filter(
            book=self.book,
            reviewer=self.reviewer,
        ).exclude(pk=self.instance.pk)
        if duplicate_review.exists():
            raise forms.ValidationError("You have already reviewed this book.")
        return cleaned_data

    def save(self, commit=True):
        self.instance.book = self.book
        self.instance.reviewer = self.reviewer
        return super().save(commit=commit)

    class Meta:
        model = Review
        fields = ["rating", "text"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 0, "max": 10}),
            "text": forms.Textarea(attrs={"rows": 5}),
        }
