"""
Forms for local micropub posting.
"""

from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout, Submit
from django import forms


class MicropubPostForm(forms.Form):
    """Form for creating micropub posts locally."""

    POST_TYPE_CHOICES = [
        ("note", "Note (no title)"),
        ("article", "Article (with title)"),
    ]

    post_type = forms.ChoiceField(
        choices=POST_TYPE_CHOICES, initial="note", widget=forms.RadioSelect, label="Post Type"
    )

    name = forms.CharField(
        required=False,
        label="Title",
        help_text="Leave empty for a note",
        widget=forms.TextInput(attrs={"placeholder": "Post Title"}),
    )

    content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "placeholder": "Write your content here...\n\nSupports HTML and Markdown-style code blocks.",
            }
        ),
        label="Content",
        help_text="You can use HTML tags or plain text",
    )

    category = forms.CharField(
        required=False,
        label="Tags/Categories",
        help_text="Comma-separated list",
        widget=forms.TextInput(attrs={"placeholder": "indieweb, micropub, django"}),
    )

    published = forms.DateTimeField(
        required=False,
        label="Published Date",
        help_text="Leave empty for current time",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )

    photo = forms.URLField(
        required=False,
        label="Photo URL",
        help_text="Optional photo to include",
        widget=forms.URLInput(attrs={"placeholder": "https://example.com/photo.jpg"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "micropub-form"
        self.helper.layout = Layout(
            Div(HTML("<h3>Create a Post</h3>"), Field("post_type"), css_class="mb-3"),
            Div(FloatingField("name"), css_id="title-field", css_class="mb-3"),
            FloatingField("content"),
            Div(FloatingField("category"), FloatingField("photo"), FloatingField("published"), css_class="mb-3"),
            Submit("submit", "Publish", css_class="btn btn-primary"),
        )

    def clean_category(self):
        """Convert comma-separated categories to list."""
        categories = self.cleaned_data.get("category", "")
        if categories:
            return [cat.strip() for cat in categories.split(",") if cat.strip()]
        return []

    def to_micropub_properties(self):
        """Convert form data to micropub properties."""
        properties = {}

        # Add content
        content = self.cleaned_data.get("content", "")
        if content:
            properties["content"] = [content]

        # Add name if article
        if self.cleaned_data.get("post_type") == "article":
            name = self.cleaned_data.get("name", "")
            if name:
                properties["name"] = [name]

        # Add categories
        categories = self.cleaned_data.get("category", [])
        if categories:
            properties["category"] = categories

        # Add published date
        published = self.cleaned_data.get("published")
        if published:
            properties["published"] = [published.isoformat()]

        # Add photo
        photo = self.cleaned_data.get("photo", "")
        if photo:
            properties["photo"] = [photo]

        return properties
