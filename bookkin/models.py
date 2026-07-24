import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# Inheriting from models.Model makes this class a Django ORM model.
# makemigrations turns its Field attributes into database column definitions.
class Book(models.Model):
    # Django calls a callable default each time it creates a Book.
    # editable=False keeps this field out of generated forms, including the admin.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=72)
    # FileField stores the file under book_covers/ in the configured storage.
    # The database stores the storage path rather than the file itself.
    cover_image = models.FileField(upload_to="book_covers/")

    # Django uses this value when displaying a model instance, so the admin
    # shows the title instead of the UUID.
    def __str__(self):
        return self.title


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # ForeignKey creates a reviewer_id column and exposes the related user as
    # review.reviewer. AUTH_USER_MODEL follows the authentication model selected
    # in settings instead of hard-coding Django's default User model.
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        # CASCADE makes Django delete the user's reviews with the user.
        on_delete=models.CASCADE,
        # related_name enables reverse queries through user.reviews.
        related_name="reviews",
    )
    book = models.ForeignKey(
        Book,
        # CASCADE makes Django delete a book's reviews with the book.
        on_delete=models.CASCADE,
        # related_name enables reverse queries through book.reviews.
        related_name="reviews",
    )
    text = models.TextField()
    # Validators run during ModelForm validation or full_clean(), but save()
    # does not call them automatically, so a database constraint is also used.
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )

    # Django uses this value when displaying a review in the admin and other
    # automatically generated model choices.
    def __str__(self):
        return f"{self.reviewer} - {self.book} ({self.rating}/10)"

    class Meta:
        # Migrations turn Meta.constraints into database constraints, applying
        # these rules even to writes that bypass Django form validation.
        constraints = [
            # CheckConstraint enforces the rating range in the database.
            models.CheckConstraint(
                condition=models.Q(rating__gte=0, rating__lte=10),
                name="review_rating_between_0_and_10",
            ),
            # This field pair allows only one review per user and book.
            models.UniqueConstraint(
                fields=["reviewer", "book"],
                name="one_review_per_user_and_book",
            ),
        ]
