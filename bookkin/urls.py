from django.urls import path

from . import views

# Namespacing URL names prevents collisions with routes from other Django apps.
app_name = "bookkin"

urlpatterns = [
    path("", views.book_list, name="book-list"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("books/<uuid:book_id>/cover/", views.book_cover, name="book-cover"),
    # The uuid converter rejects malformed values and passes a UUID to the view.
    path("books/<uuid:book_id>/", views.book_detail, name="book-detail"),
]
