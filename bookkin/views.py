from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_safe

from .forms import ReviewForm
from .models import Book

BOOKS_PER_PAGE = 10
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"


def book_list(request):
    """Show a searchable, paginated list of books."""
    query = request.GET.get("q", "").strip()
    books = (
        Book.objects.only("id", "title")
        .annotate(
            average_rating=Avg("reviews__rating"),
            review_count=Count("reviews"),
        )
        .order_by("title", "id")
    )
    if query:
        books = books.filter(title__icontains=query)

    page = Paginator(books, BOOKS_PER_PAGE).get_page(request.GET.get("page"))
    return render(
        request,
        "bookkin/book_list.html",
        {
            "page": page,
            "query": query,
        },
    )


def book_detail(request, book_id):
    """Show a book and its reviews, and accept new reviews."""
    books = Book.objects.only("id", "title").annotate(
        average_rating=Avg("reviews__rating"),
        review_count=Count("reviews"),
    )
    book = get_object_or_404(books, pk=book_id)

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


@require_safe
def book_cover(request, book_id):
    """Return a book cover stored in the database."""
    book = get_object_or_404(Book.objects.only("cover_image"), pk=book_id)
    cover_image = bytes(book.cover_image)
    if cover_image.startswith(PNG_SIGNATURE):
        content_type = "image/png"
    elif cover_image.startswith(JPEG_SIGNATURE):
        content_type = "image/jpeg"
    else:
        raise Http404("This book does not have a valid cover image.")

    response = HttpResponse(cover_image, content_type=content_type)
    response.headers["Cache-Control"] = "public, max-age=86400"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def signup(request):
    """Create an account and sign the new user in."""
    if request.user.is_authenticated:
        return redirect("bookkin:book-list")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # login() persists the authenticated user's ID in the session.
            login(request, user)
            return redirect("bookkin:book-list")
    else:
        form = UserCreationForm()

    return render(request, "bookkin/signup.html", {"form": form})


def login_view(request):
    """Authenticate an existing user."""
    if request.user.is_authenticated:
        return redirect("bookkin:book-list")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(_safe_next_url(request) or reverse("bookkin:book-list"))
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
    return redirect("bookkin:book-list")


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
