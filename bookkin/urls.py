from django.urls import path

from . import views

# Namespacing URL names prevents collisions with routes from other Django apps.
app_name = "bookkin"

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("books/", views.book_list, name="book-list"),
    # The uuid converter rejects malformed values and passes a UUID to the view.
    path("books/<uuid:book_id>/", views.book_detail, name="book-detail"),
]
