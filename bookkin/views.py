from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


def home(request):
    """Show the application's home page."""
    return render(request, "bookkin/home.html")


def book_list(request):
    """Show the book list page."""
    return HttpResponse("Book list")


def book_detail(request, book_id):
    """Show the page for one book."""
    return HttpResponse(f"Book detail: {book_id}")


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
            return redirect("bookkin:home")
    else:
        form = AuthenticationForm(request)

    return render(request, "bookkin/login.html", {"form": form})


@require_POST
def logout_view(request):
    """End the current user's authenticated session."""
    logout(request)
    return redirect("bookkin:home")
