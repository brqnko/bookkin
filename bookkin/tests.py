import uuid

from django.test import SimpleTestCase
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
