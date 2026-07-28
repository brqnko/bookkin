from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import ReviewForm
from .models import Book

BOOKS_PER_PAGE = 10


def home(request):
    """Show the application's home page."""
    return render(request, "bookkin/home.html")


def book_list(request):
    """Show a paginated list of books."""
    books = Book.objects.only("id", "title").order_by("title", "id")
    page = Paginator(books, BOOKS_PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "bookkin/book_list.html", {"page": page})


def book_detail(request, book_id):
    """Show a book and its reviews, and accept new reviews."""
    book = get_object_or_404(Book.objects.only("id", "title"), pk=book_id)

    if request.method == "POST":
        if not request.user.is_authenticated:
            login_url = reverse("bookkin:login")
            return redirect(f"{login_url}?next={request.path}")

        review_form = ReviewForm(
            request.POST,
            book=book,
            reviewer=request.user,
        )
        if review_form.is_valid():
            try:
                # The database constraint remains the final guard against two
                # simultaneous submissions by the same user.
                with transaction.atomic():
                    review_form.save()
            except IntegrityError:
                if book.reviews.filter(reviewer=request.user).exists():
                    review_form.add_error(
                        None,
                        "You have already reviewed this book.",
                    )
                else:
                    raise
            else:
                return redirect("bookkin:book-detail", book_id=book.id)
    else:
        review_form = ReviewForm(book=book, reviewer=request.user)

    reviews = book.reviews.select_related("reviewer").order_by(
        "reviewer__username",
        "id",
    )
    user_has_reviewed = (
        request.user.is_authenticated and reviews.filter(reviewer=request.user).exists()
    )
    return render(
        request,
        "bookkin/book_detail.html",
        {
            "book": book,
            "reviews": reviews,
            "review_form": review_form,
            "show_review_form": review_form.is_bound or not user_has_reviewed,
        },
    )


def signup(request):
    """Create an account and sign the new user in."""
    if request.user.is_authenticated:
        return redirect("bookkin:home")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # login() persists the authenticated user's ID in the session.
            login(request, user)
            return redirect("bookkin:home")
    else:
        form = UserCreationForm()

    return render(request, "bookkin/signup.html", {"form": form})


def login_view(request):
    """Authenticate an existing user."""
    if request.user.is_authenticated:
        return redirect("bookkin:home")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(_safe_next_url(request) or reverse("bookkin:home"))
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "bookkin/login.html",
        {
            "form": form,
            "next_url": _safe_next_url(request),
        },
    )


@require_POST
def logout_view(request):
    """End the current user's authenticated session."""
    logout(request)
    return redirect("bookkin:home")


def _safe_next_url(request):
    """Return a local post-login destination, rejecting external redirects."""
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""
