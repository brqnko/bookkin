from django.http import HttpResponse


def home(request):
    """Show the application's home page."""
    # HttpResponse completes the request with a plain-text body and a 200 status.
    return HttpResponse("Bookkin home")


def book_list(request):
    """Show the book list page."""
    return HttpResponse("Book list")


def book_detail(request, book_id):
    """Show the page for one book."""
    return HttpResponse(f"Book detail: {book_id}")
