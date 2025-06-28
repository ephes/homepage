"""
Management command to test micropub functionality.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from ...handler import CastPostMicropubHandler


class Command(BaseCommand):
    help = "Test micropub handler by creating a sample post"

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, default="admin", help="Username to create post as")
        parser.add_argument("--title", type=str, default="Test Micropub Post", help="Post title")
        parser.add_argument(
            "--content", type=str, default="This is a test post created via the micropub handler.", help="Post content"
        )

    def handle(self, *args, **options):
        User = get_user_model()

        # Get user
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User '{options['username']}' not found"))
            return

        # Create micropub properties
        properties = {
            "name": [options["title"]],
            "content": [options["content"]],
            "category": ["test", "micropub"],
        }

        # Create post
        handler = CastPostMicropubHandler()
        try:
            entry = handler.create_entry(properties, user)
            self.stdout.write(self.style.SUCCESS(f"Successfully created post: {entry.url}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating post: {str(e)}"))
