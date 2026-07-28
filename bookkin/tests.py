import uuid
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count
from django.test import TestCase
from django.urls import reverse

from .management.commands.seed_sample_data import (
    JPEG_SIGNATURE,
    LEGACY_SAMPLE_USERNAMES,
    PNG_SIGNATURE,
    SAMPLE_BOOKS,
    SAMPLE_REVIEW_TEXTS,
    SAMPLE_USERNAMES,
    make_cover_png,
)
from .models import Book, Review


class BookViewTests(TestCase):
    def setUp(self):
        self.cover_image = make_cover_png((80, 100, 120))
        self.book = Book.objects.create(
            title="A Book to Review",
            cover_image=self.cover_image,
        )

    def test_book_list_displays_books(self):
        self.assertEqual(reverse("bookkin:book-list"), "/")

        response = self.client.get(reverse("bookkin:book-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookkin/book_list.html")
        self.assertContains(response, self.book.title)
        self.assertContains(
            response,
            reverse("bookkin:book-detail", kwargs={"book_id": self.book.id}),
        )
        self.assertContains(
            response,
            reverse("bookkin:book-cover", kwargs={"book_id": self.book.id}),
        )
        self.assertContains(response, "No reviews yet.")

    def test_old_book_list_url_is_removed(self):
        response = self.client.get("/books/")

        self.assertEqual(response.status_code, 404)

    def test_book_list_searches_titles(self):
        matching_book = Book.objects.create(
            title="A Searchable Mystery",
            cover_image=self.cover_image,
        )

        response = self.client.get(
            reverse("bookkin:book-list"),
            {"q": "searchable"},
        )

        self.assertEqual(list(response.context["page"]), [matching_book])
        self.assertContains(response, matching_book.title)
        self.assertNotContains(response, self.book.title)

    def test_book_list_is_paginated_with_previous_and_next_links(self):
        Book.objects.bulk_create(
            [
                Book(title=f"Book {number:02}", cover_image=self.cover_image)
                for number in range(10)
            ]
        )

        first_page = self.client.get(reverse("bookkin:book-list"))
        second_page = self.client.get(
            reverse("bookkin:book-list"),
            {"page": 2},
        )

        self.assertEqual(len(first_page.context["page"]), 10)
        self.assertContains(
            first_page,
            '<button type="submit">Next</button>',
            html=True,
        )
        self.assertNotContains(
            first_page,
            '<button type="submit">Previous</button>',
            html=True,
        )
        self.assertEqual(len(second_page.context["page"]), 1)
        self.assertContains(
            second_page,
            '<button type="submit">Previous</button>',
            html=True,
        )
        self.assertNotContains(
            second_page,
            '<button type="submit">Next</button>',
            html=True,
        )

    def test_pagination_preserves_title_search(self):
        Book.objects.bulk_create(
            [
                Book(
                    title=f"Search Result {number:02}",
                    cover_image=self.cover_image,
                )
                for number in range(11)
            ]
        )

        first_page = self.client.get(
            reverse("bookkin:book-list"),
            {"q": "Search Result"},
        )
        second_page = self.client.get(
            reverse("bookkin:book-list"),
            {
                "q": "Search Result",
                "page": 2,
            },
        )

        self.assertContains(
            first_page,
            '<input type="hidden" name="q" value="Search Result">',
            html=True,
        )
        self.assertEqual(len(second_page.context["page"]), 1)

    def test_book_detail_displays_book_and_reviews(self):
        first_reviewer = get_user_model().objects.create_user(
            username="first-reviewer",
            password="A-secure-password-314",
        )
        second_reviewer = get_user_model().objects.create_user(
            username="second-reviewer",
            password="A-secure-password-314",
        )
        Review.objects.create(
            reviewer=first_reviewer,
            book=self.book,
            rating=8,
            text="A thoughtful review.",
        )
        Review.objects.create(
            reviewer=second_reviewer,
            book=self.book,
            rating=4,
            text="A different perspective.",
        )

        response = self.client.get(
            reverse("bookkin:book-detail", kwargs={"book_id": self.book.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookkin/book_detail.html")
        self.assertContains(response, self.book.title)
        self.assertContains(response, first_reviewer.username)
        self.assertContains(response, second_reviewer.username)
        self.assertContains(response, "Average rating: 6.0 / 10")
        self.assertContains(response, "Rating: 8 / 10")
        self.assertContains(response, "Rating: 4 / 10")
        self.assertContains(response, "A thoughtful review.")
        self.assertContains(response, "A different perspective.")

    def test_book_detail_clearly_indicates_no_reviews(self):
        response = self.client.get(
            reverse("bookkin:book-detail", kwargs={"book_id": self.book.id})
        )

        self.assertContains(response, "This book has no reviews yet.")
        self.assertContains(response, "No reviews yet.")

    def test_book_cover_returns_png_from_database(self):
        response = self.client.get(
            reverse("bookkin:book-cover", kwargs={"book_id": self.book.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/png")
        self.assertEqual(response.content, self.cover_image)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_book_cover_rejects_non_image_data(self):
        self.book.cover_image = b"not-an-image"
        self.book.save(update_fields=["cover_image"])

        response = self.client.get(
            reverse("bookkin:book-cover", kwargs={"book_id": self.book.id})
        )

        self.assertEqual(response.status_code, 404)

    def test_book_cover_returns_downloaded_jpeg(self):
        cover_image = JPEG_SIGNATURE + b"downloaded-cover"
        self.book.cover_image = cover_image
        self.book.save(update_fields=["cover_image"])

        response = self.client.get(
            reverse("bookkin:book-cover", kwargs={"book_id": self.book.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/jpeg")
        self.assertEqual(response.content, cover_image)

    def test_book_detail_rejects_non_uuid_id(self):
        response = self.client.get("/books/not-a-uuid/")

        self.assertEqual(response.status_code, 404)

    def test_book_detail_returns_404_for_unknown_book(self):
        response = self.client.get(
            reverse(
                "bookkin:book-detail",
                kwargs={"book_id": uuid.uuid4()},
            )
        )

        self.assertEqual(response.status_code, 404)


class ReviewSubmissionTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="A Book to Review",
            cover_image=make_cover_png((80, 100, 120)),
        )
        self.user = get_user_model().objects.create_user(
            username="reviewer",
            password="A-secure-password-314",
        )
        self.detail_url = reverse(
            "bookkin:book-detail",
            kwargs={"book_id": self.book.id},
        )

    def test_logged_in_user_can_submit_review(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.detail_url,
            {
                "rating": 7,
                "text": "Worth reading.",
            },
        )

        self.assertRedirects(response, self.detail_url)
        review = Review.objects.get()
        self.assertEqual(review.book, self.book)
        self.assertEqual(review.reviewer, self.user)
        self.assertEqual(review.rating, 7)
        self.assertEqual(review.text, "Worth reading.")

    def test_rating_boundaries_are_accepted(self):
        for rating in (0, 10):
            with self.subTest(rating=rating):
                user = get_user_model().objects.create_user(
                    username=f"reviewer-{rating}",
                    password="A-secure-password-314",
                )
                self.client.force_login(user)

                response = self.client.post(
                    self.detail_url,
                    {
                        "rating": rating,
                        "text": f"Rating {rating}.",
                    },
                )

                self.assertRedirects(response, self.detail_url)
                self.assertTrue(
                    Review.objects.filter(
                        reviewer=user,
                        book=self.book,
                        rating=rating,
                    ).exists()
                )

    def test_rating_outside_range_is_rejected(self):
        self.client.force_login(self.user)

        for rating in (-1, 11):
            with self.subTest(rating=rating):
                response = self.client.post(
                    self.detail_url,
                    {
                        "rating": rating,
                        "text": "Outside the allowed range.",
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn("rating", response.context["review_form"].errors)
                self.assertFalse(Review.objects.exists())

    def test_blank_review_text_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.detail_url,
            {
                "rating": 5,
                "text": "   ",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text", response.context["review_form"].errors)
        self.assertFalse(Review.objects.exists())

    def test_user_cannot_review_same_book_twice(self):
        Review.objects.create(
            reviewer=self.user,
            book=self.book,
            rating=4,
            text="Original review.",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            self.detail_url,
            {
                "rating": 9,
                "text": "Second review.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You have already reviewed this book.")
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.get().text, "Original review.")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.post(
            self.detail_url,
            {
                "rating": 7,
                "text": "Anonymous review.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("bookkin:login")))
        self.assertFalse(Review.objects.exists())


class SampleDataCommandTests(TestCase):
    @patch(
        "bookkin.management.commands.seed_sample_data.download_cover_image",
        return_value=JPEG_SIGNATURE + b"downloaded-cover",
    )
    def test_command_creates_repeatable_catalog_with_reviews_and_covers(
        self,
        download_cover,
    ):
        output = StringIO()

        call_command("seed_sample_data", stdout=output)
        call_command("seed_sample_data", stdout=output)

        books = Book.objects.annotate(review_count=Count("reviews"))
        self.assertEqual(books.count(), len(SAMPLE_BOOKS))
        self.assertEqual(
            Review.objects.count(),
            sum(len(texts) for texts in SAMPLE_REVIEW_TEXTS.values()),
        )
        self.assertTrue(all(1 <= book.review_count <= 10 for book in books))
        self.assertTrue(
            all(bytes(book.cover_image).startswith(JPEG_SIGNATURE) for book in books)
        )
        self.assertEqual(download_cover.call_count, len(SAMPLE_BOOKS) * 2)
        self.assertEqual(
            get_user_model().objects.filter(username__in=SAMPLE_USERNAMES).count(),
            len(SAMPLE_USERNAMES),
        )
        self.assertIn(
            "Sample data ready: 12 books and 33 reviews. Downloaded 12 covers.",
            output.getvalue(),
        )

    def test_offline_command_generates_png_covers(self):
        call_command("seed_sample_data", offline=True, stdout=StringIO())

        self.assertTrue(
            all(
                bytes(book.cover_image).startswith(PNG_SIGNATURE)
                for book in Book.objects.all()
            )
        )

    def test_command_renames_legacy_authors_without_changing_review_owners(self):
        user_model = get_user_model()
        existing_book = Book.objects.create(
            title="An Existing Sample Book",
            cover_image=make_cover_png((40, 50, 60)),
        )
        legacy_users = [
            user_model.objects.create(username=username)
            for username in LEGACY_SAMPLE_USERNAMES
        ]
        for user in legacy_users:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        existing_reviews = [
            Review.objects.create(
                book=existing_book,
                reviewer=user,
                rating=5,
                text="An existing review.",
            )
            for user in legacy_users
        ]

        call_command("seed_sample_data", offline=True, stdout=StringIO())

        for new_username, legacy_username, user, review in zip(
            SAMPLE_USERNAMES,
            LEGACY_SAMPLE_USERNAMES,
            legacy_users,
            existing_reviews,
            strict=True,
        ):
            with self.subTest(username=new_username):
                self.assertFalse(
                    user_model.objects.filter(username=legacy_username).exists()
                )
                renamed_user = user_model.objects.get(username=new_username)
                self.assertEqual(renamed_user.pk, user.pk)
                review.refresh_from_db()
                self.assertEqual(review.reviewer_id, renamed_user.pk)

    def test_command_uses_curated_review_text_instead_of_template_copy(self):
        call_command("seed_sample_data", offline=True, stdout=StringIO())

        for title, expected_texts in SAMPLE_REVIEW_TEXTS.items():
            with self.subTest(title=title):
                actual_texts = set(
                    Review.objects.filter(book__title=title).values_list(
                        "text",
                        flat=True,
                    )
                )
                self.assertEqual(actual_texts, set(expected_texts))
                self.assertTrue(
                    all("sample review of" not in text.lower() for text in actual_texts)
                )

    def test_command_does_not_take_over_existing_login_user(self):
        user_model = get_user_model()
        existing_user = user_model.objects.create_user(
            username=SAMPLE_USERNAMES[0],
            password="A-secure-password-314",
        )

        with self.assertRaises(CommandError):
            call_command("seed_sample_data", offline=True, stdout=StringIO())

        existing_user.refresh_from_db()
        self.assertTrue(existing_user.check_password("A-secure-password-314"))


class SignupViewTests(TestCase):
    def setUp(self):
        self.signup_url = reverse("bookkin:signup")

    def test_get_displays_signup_form(self):
        response = self.client.get(self.signup_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookkin/signup.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password1"')
        self.assertContains(response, 'name="password2"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_valid_post_creates_user_and_logs_them_in(self):
        response = self.client.post(
            self.signup_url,
            {
                "username": "new-reader",
                "password1": "A-secure-password-314",
                "password2": "A-secure-password-314",
            },
        )

        self.assertRedirects(response, reverse("bookkin:book-list"))
        user = get_user_model().objects.get(username="new-reader")
        self.assertTrue(user.check_password("A-secure-password-314"))
        self.assertEqual(str(user.pk), self.client.session["_auth_user_id"])

    def test_invalid_post_rerenders_form_without_creating_user(self):
        response = self.client.post(
            self.signup_url,
            {
                "username": "new-reader",
                "password1": "A-secure-password-314",
                "password2": "different-password-271",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(
            get_user_model().objects.filter(username="new-reader").exists()
        )

    def test_authenticated_user_is_redirected_to_book_list(self):
        user = get_user_model().objects.create_user(
            username="existing-reader",
            password="A-secure-password-314",
        )
        self.client.force_login(user)

        response = self.client.get(self.signup_url)

        self.assertRedirects(response, reverse("bookkin:book-list"))


class LoginLogoutViewTests(TestCase):
    def setUp(self):
        self.password = "A-secure-password-314"
        self.user = get_user_model().objects.create_user(
            username="existing-reader",
            password=self.password,
        )
        self.login_url = reverse("bookkin:login")
        self.logout_url = reverse("bookkin:logout")

    def test_get_displays_login_form(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookkin/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_valid_post_logs_user_in(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": self.password,
            },
        )

        self.assertRedirects(response, reverse("bookkin:book-list"))
        self.assertEqual(str(self.user.pk), self.client.session["_auth_user_id"])

    def test_valid_post_returns_user_to_safe_next_page(self):
        book_list_url = reverse("bookkin:book-list")

        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": self.password,
                "next": book_list_url,
            },
        )

        self.assertRedirects(response, book_list_url)

    def test_invalid_post_rerenders_form_without_logging_user_in(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": "incorrect-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_authenticated_user_is_redirected_from_login_to_book_list(self):
        self.client.force_login(self.user)

        response = self.client.get(self.login_url)

        self.assertRedirects(response, reverse("bookkin:book-list"))

    def test_post_logs_user_out(self):
        self.client.force_login(self.user)

        response = self.client.post(self.logout_url)

        self.assertRedirects(response, reverse("bookkin:book-list"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_does_not_log_user_out(self):
        self.client.force_login(self.user)

        response = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(str(self.user.pk), self.client.session["_auth_user_id"])
