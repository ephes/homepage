"""
Simple tests for micropub endpoints that don't require full Wagtail setup.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .converters import ContentConverter
from .forms import MicropubPostForm

User = get_user_model()


class MicropubFormTests(TestCase):
    """Tests for the MicropubPostForm."""

    def test_form_valid_note(self):
        """Test form validation for a note."""
        form_data = {"post_type": "note", "content": "This is a test note.", "category": "test, note"}

        form = MicropubPostForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_valid_article(self):
        """Test form validation for an article."""
        form_data = {"post_type": "article", "name": "Test Article", "content": "This is the article content."}

        form = MicropubPostForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_requires_content(self):
        """Test that content is required."""
        form_data = {"post_type": "note", "content": ""}

        form = MicropubPostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)

    def test_to_micropub_properties(self):
        """Test conversion to micropub properties."""
        form_data = {
            "post_type": "article",
            "name": "Test Article",
            "content": "Article content",
            "category": "python, django",
            "photo": "https://example.com/photo.jpg",
        }

        form = MicropubPostForm(data=form_data)
        self.assertTrue(form.is_valid())

        properties = form.to_micropub_properties()

        self.assertEqual(properties["name"], ["Test Article"])
        self.assertEqual(properties["content"], ["Article content"])
        self.assertEqual(properties["category"], ["python", "django"])
        self.assertEqual(properties["photo"], ["https://example.com/photo.jpg"])

    def test_category_cleaning(self):
        """Test that categories are properly cleaned and split."""
        form_data = {"post_type": "note", "content": "Test content", "category": " python ,  django  , testing "}

        form = MicropubPostForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Check cleaned categories
        self.assertEqual(form.cleaned_data["category"], ["python", "django", "testing"])


class ContentConverterTests(TestCase):
    """Tests for the ContentConverter."""

    def setUp(self):
        """Set up test data."""
        self.converter = ContentConverter()

    def test_convert_plain_text(self):
        """Test converting plain text to blocks."""
        content = "This is a simple paragraph."
        blocks = self.converter.convert_content(content, {})

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "paragraph")
        self.assertIn("This is a simple paragraph", blocks[0][1])

    def test_convert_with_heading(self):
        """Test converting text with markdown-style heading."""
        content = "# This is a heading\n\nThis is a paragraph."
        blocks = self.converter.convert_content(content, {})

        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0][0], "heading")
        self.assertEqual(blocks[0][1], "This is a heading")
        self.assertEqual(blocks[1][0], "paragraph")

    def test_convert_code_block(self):
        """Test converting code blocks."""
        content = """Here's some code:

```python
def hello():
    print("Hello, World!")
```

More text after."""

        blocks = self.converter.convert_content(content, {})

        # Should have paragraph, code, paragraph
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0][0], "paragraph")
        self.assertEqual(blocks[1][0], "code")
        self.assertEqual(blocks[1][1]["language"], "python")
        self.assertIn('print("Hello, World!")', blocks[1][1]["code"])
        self.assertEqual(blocks[2][0], "paragraph")

    def test_convert_html_content(self):
        """Test converting HTML content."""
        # The converter expects HTML content to be passed directly
        content = "<p>This is <strong>HTML</strong> content.</p>"

        blocks = self.converter.convert_content(content, {})

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "paragraph")
        self.assertIn("<strong>HTML</strong>", blocks[0][1])

    def test_handle_photo_property(self):
        """Test handling photo property."""
        content = "Check out this photo!"
        properties = {"photo": ["https://example.com/photo.jpg"]}

        blocks = self.converter.convert_content(content, properties)

        # Should have paragraph and photo
        self.assertTrue(any("<img" in str(block[1]) for block in blocks))
        self.assertTrue(any("example.com/photo.jpg" in str(block[1]) for block in blocks))
