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
            "I could see why the dialogue is celebrated, but its wit rarely landed "
            "for me. The social misunderstandings began to feel repetitive, and I "
            "never became invested enough in the romance to enjoy the slow build."
        ),
    ],
    "Moby-Dick": [
        (
            "The scenes at sea can be vivid and genuinely tense, especially when "
            "Ahab's obsession takes over the crew. Still, the long technical "
            "digressions repeatedly broke the momentum and made finishing it feel "
            "more like an assignment than an adventure."
        ),
        (
            "I admired the scale of the story and the strange atmosphere aboard the "
            "Pequod. Some chapters are fascinating, while others disappear so far "
            "into whale anatomy that I lost the emotional thread. It was memorable, "
            "but not consistently enjoyable."
        ),
    ],
    "Frankenstein": [
        (
            "The questions about responsibility and ambition are still powerful, "
            "and the creature's situation is more tragic than I expected. However, "
            "the layered narration and slow stretches kept distancing me whenever "
            "the story started to build momentum."
        ),
        (
            "This was much more thoughtful and sorrowful than the simple monster "
            "story I had imagined. The creature's chapters gave the novel real "
            "emotional weight, and Victor's repeated failures made the consequences "
            "feel painfully inevitable."
        ),
        (
            "A haunting and beautifully written novel about loneliness, ambition, "
            "and the obligations a creator has toward what they bring into the "
            "world. The shifting sympathies between Victor and the creature kept me "
            "thinking long after the final page."
        ),
    ],
    "Jane Eyre": [
        (
            "Jane's voice is direct, intelligent, and easy to root for, especially "
            "when she insists on keeping her independence. Some parts of the "
            "central romance have aged poorly, though, and that tension kept me from "
            "fully embracing the ending."
        ),
        (
            "I loved Jane's fierce independence and the way the novel lets her moral "
            "convictions guide the story. Thornfield has a wonderfully uneasy "
            "atmosphere, and even the slower sections added to the sense that "
            "something unsettling was waiting behind a closed door."
        ),
        (
            "Jane is a strong narrator, but the relationship at the center made me "
            "deeply uncomfortable from its earliest stages. Rochester's behavior "
            "overwhelmed the qualities I liked elsewhere, so I never became invested "
            "in the outcome the novel wanted me to celebrate."
        ),
        (
            "There are memorable scenes and Jane herself has a clear, compelling "
            "personality. Even so, the story felt overly long and increasingly "
            "melodramatic, with several coincidences that pulled me out of the "
            "otherwise grounded emotional journey."
        ),
    ],
    "The Great Gatsby": [
        (
            "The novel is short, sharp, and full of images that make its parties and "
            "summer heat feel immediate. I especially liked how the glamorous "
            "surface gradually gives way to disappointment. The final pages stayed "
            "with me after the plot details had faded."
        ),
        (
            "I found nearly every character unpleasant without finding their flaws "
            "particularly revealing. The famous symbols felt heavy-handed rather "
            "than moving, and the emotional distance kept the tragedy from landing. "
            "Its brevity was the main reason I finished."
        ),
        (
            "The prose is polished and there are individual descriptions I wanted "
            "to reread, but the characters remained too distant for me. I understood "
            "the emptiness the book was exposing without feeling much when that "
            "emptiness finally caught up with them."
        ),
        (
            "This was a quick and beautifully written read, with a carefully built "
            "sense of longing beneath every party scene. Some of the characters felt "
            "more like symbols than people, so its emotional impact was uneven, but "
            "the atmosphere is hard to forget."
        ),
        (
            "The language is gorgeous, and the emptiness beneath all that glamour "
            "comes through perfectly. Gatsby's hope feels both absurd and painfully "
            "human, while Nick's distance gives the story a dreamlike quality. I "
            "understood immediately why the ending is so often quoted."
        ),
    ],
    "The Picture of Dorian Gray": [
        (
            "Darkly funny, elegant, and unsettling from beginning to end. Every "
            "conversation feels dangerously clever, yet the wit never hides the "
            "damage caused by Dorian's choices. The portrait is a brilliant device, "
            "and the final sequence delivers exactly the reckoning I hoped for."
        ),
    ],
    "Little Women": [
        (
            "I liked the warmth between the sisters, but the episodic structure made "
            "the story feel much longer than it needed to be. Many chapters end with "
            "a lesson stated too directly for my taste, and the constant moralizing "
            "eventually overshadowed the family moments."
        ),
        (
            "The March sisters have distinct personalities, and their home life has "
            "a comforting, lived-in quality. I enjoyed watching their ambitions "
            "change as they grew older, although the uneven pacing and abrupt time "
            "jumps sometimes made it difficult to stay engaged."
        ),
    ],
    "The Adventures of Sherlock Holmes": [
        (
            "A few mysteries have clever premises, and Holmes is entertaining when "
            "he explains a detail everyone else missed. After several stories, "
            "though, the formula became predictable and the supporting characters "
            "rarely had enough depth to make the cases matter."
        ),
        (
            "These are entertaining cases with a wonderfully confident detective at "
            "their center. The short-story format keeps things moving, though a few "
            "solutions depend on information the reader could never have guessed. "
            "Watson's narration gives the collection plenty of charm."
        ),
        (
            "Smart, brisk mysteries built around one of literature's best "
            "partnerships. Holmes supplies the spectacle, but Watson's curiosity and "
            "loyalty make the stories inviting. I enjoyed the variety of clients and "
            "settings, and nearly every case had at least one great reveal."
        ),
    ],
    "The Time Machine": [
        (
            "The future society is an intriguing thought experiment, and the gradual "
            "discovery of what connects the Eloi and Morlocks is effective. The "
            "characters are little more than vehicles for those ideas, but the book "
            "is concise enough to remain a worthwhile read."
        ),
        (
            "A compact and imaginative adventure with a surprisingly bleak view of "
            "human progress. The ruined future landscapes are described with real "
            "wonder, and the quiet final journey pushes the idea far beyond a simple "
            "story about an unusual machine."
        ),
        (
            "The story moved so quickly that its people never felt like more than "
            "labels attached to an argument. I wanted to care about the Time "
            "Traveller's discoveries, but the rushed storytelling and flat "
            "characters gave me almost nothing emotional to hold onto."
        ),
        (
            "The divided future world is intriguing, and I liked the darker "
            "implications beneath its initially peaceful appearance. Still, the "
            "narrative rushes through each discovery before developing it, leaving "
            "the whole book feeling more like a sketch than a finished novel."
        ),
    ],
    "Dracula": [
        (
            "The journal and letter format builds suspense by letting each character "
            "notice a different piece of the danger. The opening in Transylvania is "
            "excellent, and several later scenes are just as tense, although the "
            "middle section drags before the group takes action."
        ),
        (
            "Genuinely eerie and full of unforgettable scenes, from the castle to "
            "the arrival of the ship in Whitby. The shifting narrators made the "
            "danger feel immediate and gave the group a real sense of camaraderie. "
            "Even knowing the story, I found it gripping."
        ),
        (
            "The opening chapters created a level of dread that the rest of the book "
            "never matched for me. Once the characters began comparing notes, they "
            "repeated the same fears and plans so often that the tension disappeared. "
            "The final confrontation also felt strangely rushed."
        ),
        (
            "It is easy to see how influential the imagery and structure have been, "
            "and the strongest moments are still genuinely atmospheric. At the same "
            "time, the group discussions and repeated explanations slowed the hunt "
            "considerably. I admired it more than I enjoyed it."
        ),
        (
            "A wonderfully creepy classic with a strong ensemble and an especially "
            "memorable beginning. Mina's intelligence keeps the investigation "
            "grounded, while the fragmented documents make each new clue satisfying. "
            "Some passages are slow, but the atmosphere carried me through them."
        ),
    ],
    "The Secret Garden": [
        (
            "Warm, hopeful, and deeply satisfying without pretending its children "
            "are pleasant from the start. Watching the garden return to life "
            "alongside Mary and Colin gives the story a simple but effective shape. "
            "The descriptions of outdoor work made the transformation feel earned."
        ),
    ],
    "The Wonderful Wizard of Oz": [
        (
            "The journey felt like a chain of similar obstacles rather than a story "
            "that was building toward something. Dorothy's companions each have a "
            "clear trait, but none developed enough to hold my attention, and the "
            "resolution made the earlier danger feel pointless."
        ),
        (
            "There are imaginative places and a few playful ideas that must have "
            "felt especially fresh when the book appeared. For me, the simple plot "
            "and repetitive encounters did not offer enough variety, although the "
            "companions' loyalty gave the journey some charm."
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
