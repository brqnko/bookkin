import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Book, Review


class BookViewTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="A Book to Review",
            cover_image=b"cover",
        )

    def test_home(self):
        response = self.client.get(reverse("bookkin:home"))

        self.assertContains(response, "Bookkin home")

    def test_book_list_displays_books(self):
        response = self.client.get(reverse("bookkin:book-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookkin/book_list.html")
        self.assertContains(response, self.book.title)
        self.assertContains(
            response,
            reverse("bookkin:book-detail", kwargs={"book_id": self.book.id}),
        )

    def test_book_list_is_paginated_with_previous_and_next_links(self):
        Book.objects.bulk_create(
            [
                Book(title=f"Book {number:02}", cover_image=b"cover")
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

    def test_book_detail_displays_book_and_reviews(self):
        reviewer = get_user_model().objects.create_user(
            username="reviewer",
            password="A-secure-password-314",
        )
        Review.objects.create(
            reviewer=reviewer,
            book=self.book,
            rating=8,
            text="A thoughtful review.",
        )

        response = self.client.get(
            reverse("bookkin:book-detail", kwargs={"book_id": self.book.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookkin/book_detail.html")
        self.assertContains(response, self.book.title)
        self.assertContains(response, reviewer.username)
        self.assertContains(response, "Rating: 8 / 10")
        self.assertContains(response, "A thoughtful review.")

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
            cover_image=b"cover",
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

        self.assertRedirects(response, reverse("bookkin:home"))
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

    def test_authenticated_user_is_redirected_home(self):
        user = get_user_model().objects.create_user(
            username="existing-reader",
            password="A-secure-password-314",
        )
        self.client.force_login(user)

        response = self.client.get(self.signup_url)

        self.assertRedirects(response, reverse("bookkin:home"))


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

        self.assertRedirects(response, reverse("bookkin:home"))
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

    def test_authenticated_user_is_redirected_from_login(self):
        self.client.force_login(self.user)

        response = self.client.get(self.login_url)

        self.assertRedirects(response, reverse("bookkin:home"))

    def test_post_logs_user_out(self):
        self.client.force_login(self.user)

        response = self.client.post(self.logout_url)

        self.assertRedirects(response, reverse("bookkin:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_does_not_log_user_out(self):
        self.client.force_login(self.user)

        response = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(str(self.user.pk), self.client.session["_auth_user_id"])
