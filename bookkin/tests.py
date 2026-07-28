import uuid

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class ViewTests(SimpleTestCase):
    def test_home(self):
        response = self.client.get(reverse("bookkin:home"))

        self.assertContains(response, "Bookkin home")

    def test_book_list(self):
        response = self.client.get(reverse("bookkin:book-list"))

        self.assertContains(response, "Book list")

    def test_book_detail(self):
        book_id = uuid.uuid4()

        response = self.client.get(
            reverse("bookkin:book-detail", kwargs={"book_id": book_id})
        )

        self.assertContains(response, f"Book detail: {book_id}")

    def test_book_detail_rejects_non_uuid_id(self):
        response = self.client.get("/books/not-a-uuid/")

        self.assertEqual(response.status_code, 404)


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
