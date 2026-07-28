import binascii
import struct
import uuid
import zlib
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from bookkin.models import Book, Review

SAMPLE_BOOKS = [
    ("Pride and Prejudice", 14348537, (143, 78, 101)),
    ("Moby-Dick", 10544254, (42, 92, 120)),
    ("Frankenstein", 12356249, (70, 92, 66)),
    ("Jane Eyre", 8235363, (111, 65, 52)),
    ("The Great Gatsby", 10590366, (31, 80, 107)),
    ("The Picture of Dorian Gray", 14314858, (83, 78, 120)),
    ("Little Women", 8775559, (139, 83, 74)),
    ("The Adventures of Sherlock Holmes", 6717853, (63, 72, 91)),
    ("The Time Machine", 9009316, (78, 109, 116)),
    ("Dracula", 12216503, (104, 42, 46)),
    ("The Secret Garden", 12622062, (67, 114, 72)),
    ("The Wonderful Wizard of Oz", 552443, (121, 96, 39)),
]
SAMPLE_USERNAMES = [
    "mika_reads",
    "haru_booklog",
    "sora_pages",
    "yuki_books",
    "ren_reads",
]
LEGACY_SAMPLE_USERNAMES = [f"sample_reader_{number}" for number in range(1, 6)]
SAMPLE_REVIEW_TEXTS = {
    "Pride and Prejudice": [
        (
            "The witty dialogue never clicked for me, and I struggled to care "
            "about the romance."
        ),
    ],
    "Moby-Dick": [
        (
            "There are a few striking scenes, but the long digressions made "
            "this a chore to finish."
        ),
        ("A fascinating obsession story buried beneath far more detail than I wanted."),
    ],
    "Frankenstein": [
        (
            "The central idea is powerful, though the slow pacing kept "
            "pulling me out of the story."
        ),
        (
            "More thoughtful and tragic than I expected, especially in the "
            "creature's chapters."
        ),
        (
            "A haunting, beautifully written novel about loneliness, "
            "ambition, and responsibility."
        ),
    ],
    "Jane Eyre": [
        (
            "Jane is a compelling narrator, even if parts of the romance "
            "have not aged well."
        ),
        ("I loved Jane's fierce independence and the novel's dark, atmospheric mood."),
        (
            "The relationship at the center made me deeply uncomfortable, "
            "and I never became invested."
        ),
        (
            "Jane herself is memorable, but the story felt overly long and "
            "melodramatic to me."
        ),
    ],
    "The Great Gatsby": [
        ("Short, sharp, and full of memorable images; the ending stayed with me."),
        (
            "I disliked every character and found the symbolism far less "
            "moving than I expected."
        ),
        "The prose is polished, but the distant characters left me cold.",
        ("A quick, beautifully written read, though its emotional impact felt uneven."),
        (
            "The language is gorgeous, and the emptiness beneath all that "
            "glamour comes through perfectly."
        ),
    ],
    "The Picture of Dorian Gray": [
        (
            "Darkly funny, elegant, and unsettling from beginning to end. "
            "Every conversation feels dangerously clever."
        ),
    ],
    "Little Women": [
        (
            "The episodic story moved too slowly for me, and the moral "
            "lessons felt heavy-handed."
        ),
        (
            "The sisters are charming, but the uneven pacing made it "
            "difficult to stay engaged."
        ),
    ],
    "The Adventures of Sherlock Holmes": [
        (
            "A few mysteries were clever, but the formula became repetitive "
            "quite quickly."
        ),
        (
            "Entertaining cases and a great detective, though some solutions "
            "feel a little too convenient."
        ),
        (
            "Smart, brisk mysteries with an iconic partnership at their "
            "center. I enjoyed nearly every case."
        ),
    ],
    "The Time Machine": [
        (
            "The ideas are more interesting than the characters, but it "
            "remains a worthwhile short read."
        ),
        (
            "A compact and imaginative story with a surprisingly bleak view "
            "of the future."
        ),
        (
            "The flat characters and rushed storytelling gave me nothing to "
            "connect with."
        ),
        (
            "The future world is intriguing, but the story feels more like a "
            "sketch than a finished novel."
        ),
    ],
    "Dracula": [
        ("The journal format builds suspense well, although the middle section drags."),
        (
            "Genuinely eerie and full of unforgettable scenes. The shifting "
            "narrators made the danger feel immediate."
        ),
        (
            "The opening was excellent, but the repetitive later chapters "
            "drained all the tension for me."
        ),
        (
            "Atmospheric and influential, but much slower and more "
            "repetitive than I expected."
        ),
        (
            "A wonderfully creepy classic with a strong cast and an "
            "especially memorable beginning."
        ),
    ],
    "The Secret Garden": [
        (
            "Warm, hopeful, and deeply satisfying. Watching both the garden "
            "and the children come back to life was lovely."
        ),
    ],
    "The Wonderful Wizard of Oz": [
        (
            "The adventure felt thin and repetitive, and none of the "
            "characters held my attention."
        ),
        (
            "There are some imaginative moments, but the simple plot did not "
            "offer enough to keep me engaged."
        ),
    ],
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
MAX_COVER_BYTES = 5 * 1024 * 1024
OPEN_LIBRARY_COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
USER_AGENT = "bookkin-course-project/0.1"


class Command(BaseCommand):
    help = "Create a repeatable catalog of sample books, covers, and reviews."

    def add_arguments(self, parser):
        parser.add_argument(
            "--offline",
            action="store_true",
            help="Generate placeholder PNG covers instead of downloading covers.",
        )

    def handle(self, *args, **options):
        validate_sample_data()
        covers = {}
        downloaded_cover_count = 0
        for title, cover_id, color in SAMPLE_BOOKS:
            cover_image = make_cover_png(color)
            if not options["offline"]:
                try:
                    cover_image = download_cover_image(cover_id)
                except (OSError, ValueError) as error:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Could not download the cover for {title}: {error}. "
                            "Using a generated placeholder."
                        )
                    )
                else:
                    downloaded_cover_count += 1
            covers[title] = cover_image

        with transaction.atomic():
            users = get_sample_users()
            review_count = 0
            for book_index, (title, _, _) in enumerate(SAMPLE_BOOKS):
                book_id = uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"https://bookkin.example/books/{title}",
                )
                book, _ = Book.objects.update_or_create(
                    id=book_id,
                    defaults={
                        "title": title,
                        "cover_image": covers[title],
                    },
                )

                review_texts = SAMPLE_REVIEW_TEXTS[title]
                reviewers = users[: len(review_texts)]
                for reviewer_index, (reviewer, review_text) in enumerate(
                    zip(reviewers, review_texts, strict=True)
                ):
                    rating = (book_index * 2 + reviewer_index * 3) % 11
                    Review.objects.update_or_create(
                        book=book,
                        reviewer=reviewer,
                        defaults={
                            "rating": rating,
                            "text": review_text,
                        },
                    )
                    review_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sample data ready: {len(SAMPLE_BOOKS)} books and "
                f"{review_count} reviews. Downloaded "
                f"{downloaded_cover_count} covers."
            )
        )


def get_sample_users():
    """Create sample authors or safely rename authors from the old seed."""
    users = []
    user_model = get_user_model()
    for username, legacy_username in zip(
        SAMPLE_USERNAMES,
        LEGACY_SAMPLE_USERNAMES,
        strict=True,
    ):
        user = user_model.objects.filter(username=username).first()
        legacy_user = user_model.objects.filter(username=legacy_username).first()

        if user is not None and legacy_user is not None:
            raise CommandError(
                f"Both {username} and {legacy_username} exist; "
                "refusing to merge user accounts."
            )
        if user is not None:
            if user.has_usable_password():
                raise CommandError(
                    f"{username} belongs to a login-capable user; "
                    "choose another sample nickname."
                )
        elif legacy_user is not None:
            if legacy_user.has_usable_password():
                raise CommandError(
                    f"{legacy_username} is login-capable; refusing to rename it."
                )
            user = legacy_user
            # Renaming preserves the sample author's review foreign keys.
            user.username = username
            user.save(update_fields=["username"])
        else:
            user = user_model.objects.create(username=username)
            user.set_unusable_password()
            user.save(update_fields=["password"])

        users.append(user)
    return users


def validate_sample_data():
    """Fail before writing when the sample catalog definitions disagree."""
    book_titles = [title for title, _, _ in SAMPLE_BOOKS]
    if len(book_titles) != len(set(book_titles)):
        raise CommandError("Sample book titles must be unique.")
    if len(SAMPLE_USERNAMES) != len(set(SAMPLE_USERNAMES)):
        raise CommandError("Sample usernames must be unique.")
    if set(book_titles) != set(SAMPLE_REVIEW_TEXTS):
        raise CommandError("Every sample book must have one review text list.")
    if any(
        not 1 <= len(review_texts) <= min(10, len(SAMPLE_USERNAMES))
        for review_texts in SAMPLE_REVIEW_TEXTS.values()
    ):
        raise CommandError("Each sample book must have between 1 and 10 reviews.")


def download_cover_image(cover_id):
    """Download one medium JPEG cover from Open Library."""
    request = Request(
        OPEN_LIBRARY_COVER_URL.format(cover_id=cover_id),
        headers={"User-Agent": USER_AGENT},
    )
    with urlopen(request, timeout=15) as response:
        cover_image = response.read(MAX_COVER_BYTES + 1)

    if len(cover_image) > MAX_COVER_BYTES:
        raise ValueError("cover image exceeds the 5 MB limit")
    if not cover_image.startswith(JPEG_SIGNATURE):
        raise ValueError("response is not a JPEG image")
    return cover_image


def make_cover_png(color, width=240, height=360):
    """Build a small dependency-free PNG placeholder for a sample book."""
    dark = tuple(max(channel - 50, 0) for channel in color)
    paper = (240, 232, 208)
    rows = bytearray()

    for y_position in range(height):
        if y_position < 12 or y_position >= height - 12:
            row = bytes(dark) * width
        elif 82 <= y_position < 106 or 260 <= y_position < 268:
            row = bytes(dark) * 12
            row += bytes(paper) * (width - 24)
            row += bytes(dark) * 12
        else:
            row = bytes(dark) * 12
            row += bytes(color) * (width - 24)
            row += bytes(dark) * 12
        rows.extend(b"\x00")
        rows.extend(row)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + png_chunk(b"IEND", b"")
    )


def png_chunk(chunk_type, data):
    checksum = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)
    )
