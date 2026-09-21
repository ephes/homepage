"""Structured, reusable content blocks for portfolio case studies.

The blocks deliberately model editorial meaning rather than layout classes.  Page
templates can therefore reproduce the approved prototype without allowing editors
to create arbitrary markup that breaks its grid or heading hierarchy.
"""

from django.core.exceptions import ValidationError
from wagtail import blocks
from wagtail.blocks import StructBlockValidationError
from wagtail.images.blocks import ImageBlock

INLINE_RICH_TEXT_FEATURES = ["bold", "italic", "link", "no-break"]
BODY_RICH_TEXT_FEATURES = ["bold", "italic", "ol", "ul", "link", "no-break"]


class LegalContactBlock(blocks.StructBlock):
    """A structural reference to the site's one public contact address."""

    prefix = blocks.CharBlock(
        required=False,
        max_length=240,
        label="Text vor dem Link",
        help_text=(
            "Zum Beispiel „E-Mail:“; Abstand und globale Adresse werden automatisch ergänzt."
        ),
    )
    label = blocks.CharBlock(
        required=False,
        max_length=160,
        label="Abweichender Linktext",
        help_text="Leer lassen, um die globale Kontaktadresse sichtbar auszugeben.",
    )
    suffix = blocks.CharBlock(
        required=False,
        max_length=120,
        label="Text nach dem Link",
        help_text="Zum Beispiel ein abschließender Punkt.",
    )

    class Meta:
        icon = "mail"
        label = "Globale Kontaktadresse"


class LegalCopyBlock(blocks.StreamBlock):
    """Semantic copy fragments used inside one legal section."""

    paragraph = blocks.RichTextBlock(
        features=INLINE_RICH_TEXT_FEATURES,
        label="Absatz",
    )
    address = blocks.RichTextBlock(
        features=INLINE_RICH_TEXT_FEATURES,
        label="Adresse",
    )
    note = blocks.CharBlock(
        max_length=240,
        label="Stand oder Hinweis",
    )
    contact = LegalContactBlock()

    class Meta:
        label = "Inhalt"


class LegalSectionBlock(blocks.StructBlock):
    """A titled legal section whose document heading stays template-owned."""

    heading = blocks.CharBlock(max_length=160, label="Überschrift")
    copy = LegalCopyBlock(label="Text")

    class Meta:
        icon = "doc-full"
        label = "Rechtsabschnitt"


class LegalSectionsBlock(blocks.StreamBlock):
    section = LegalSectionBlock()

    class Meta:
        label = "Rechtstext"


class ProjectGalleryImageValue(blocks.StructValue):
    """Expose source-image facts without persisting presentation metadata."""

    @property
    def orientation(self):
        image = self.get("image")
        if image and image.height > image.width:
            return "portrait"
        return "landscape"

    @property
    def is_portrait(self):
        return self.orientation == "portrait"

    @property
    def is_large(self):
        return bool(self.get("large"))


class CaptionedImageBlock(blocks.StructBlock):
    """An image with enforced contextual alt text and an optional caption."""

    image = ImageBlock(label="Bild")
    caption = blocks.CharBlock(
        required=False,
        max_length=240,
        label="Bildunterschrift",
    )

    class Meta:
        icon = "image"
        label = "Bild"
        template = "portfolio/blocks/captioned_image.html"


class ProjectGalleryImageBlock(CaptionedImageBlock):
    """A gallery image whose orientation comes from the uploaded source file."""

    large = blocks.BooleanBlock(
        required=False,
        default=False,
        label="Großes Motiv",
        help_text="Beginnt eine eigene, vollbreite Galeriezeile.",
    )

    class Meta:
        value_class = ProjectGalleryImageValue
        icon = "image"
        label = "Galeriebild"
        template = "portfolio/blocks/captioned_image.html"


class FullWidthImageBlock(CaptionedImageBlock):
    class Meta:
        icon = "image"
        label = "Vollbreites Bild"
        template = "portfolio/blocks/full_width_image.html"


class ImagePairBlock(blocks.StructBlock):
    left = CaptionedImageBlock(label="Bild links")
    right = CaptionedImageBlock(label="Bild rechts")

    class Meta:
        icon = "image"
        label = "Bildpaar"
        template = "portfolio/blocks/image_pair.html"


class PortraitDuoBlock(ImagePairBlock):
    """A semantic pair for two portrait-oriented editorial images."""

    def clean(self, value):
        cleaned = super().clean(value)
        errors = {}
        for side in ("left", "right"):
            image = cleaned[side]["image"]
            if image.height <= image.width:
                errors[side] = ValidationError("Bitte wähle ein Bild im Hochformat.")
        if errors:
            raise StructBlockValidationError(block_errors=errors)
        return cleaned

    class Meta:
        icon = "image"
        label = "Hochformat-Duo"
        template = "portfolio/blocks/portrait_duo.html"


class GalleryValue(blocks.StructValue):
    """Provide deterministic mobile rows while preserving editor order."""

    @property
    def mobile_rows(self):
        """Group only adjacent ordinary portraits; all other items stand alone."""

        images = self.get("images")
        if not images:
            return ()

        # Keep each ListBlock item bound to ProjectGalleryImageBlock so templates
        # can render it through that block's declared Meta.template. Iterating a
        # ListValue directly returns only its StructValue and loses the binding.
        images = list(images.bound_blocks)
        rows = []
        index = 0
        while index < len(images):
            image = images[index]
            next_image = images[index + 1] if index + 1 < len(images) else None
            if (
                not image.value.is_large
                and image.value.is_portrait
                and next_image is not None
                and not next_image.value.is_large
                and next_image.value.is_portrait
            ):
                rows.append((image, next_image))
                index += 2
            else:
                rows.append((image,))
                index += 1
        return tuple(rows)


class GalleryBlock(blocks.StructBlock):
    images = blocks.ListBlock(
        ProjectGalleryImageBlock(),
        min_num=2,
        label="Bilder",
        help_text="Mindestens zwei Bilder; die Reihenfolge kann frei geändert werden.",
    )

    class Meta:
        value_class = GalleryValue
        icon = "image"
        label = "Flexible Galerie"
        template = "portfolio/blocks/gallery.html"


class StatementBlock(blocks.StructBlock):
    text = blocks.RichTextBlock(
        features=INLINE_RICH_TEXT_FEATURES,
        label="Text",
    )

    class Meta:
        icon = "openquote"
        label = "Statement"
        template = "portfolio/blocks/statement.html"


class ChallengeSolutionBlock(blocks.StructBlock):
    challenge = blocks.RichTextBlock(
        features=BODY_RICH_TEXT_FEATURES,
        label="Aufgabe",
    )
    solution = blocks.RichTextBlock(
        features=BODY_RICH_TEXT_FEATURES,
        label="Lösung",
    )

    class Meta:
        icon = "form"
        label = "Aufgabe und Lösung"
        template = "portfolio/blocks/challenge_solution.html"


class StatBlock(blocks.StructBlock):
    value = blocks.CharBlock(max_length=80, label="Wert")
    label = blocks.CharBlock(max_length=160, label="Bezeichnung")

    class Meta:
        icon = "order"
        label = "Mehrwert"


class StatsBlock(blocks.StructBlock):
    items = blocks.ListBlock(
        StatBlock(),
        min_num=1,
        label="Mehrwert",
    )

    class Meta:
        icon = "list-ul"
        label = "Mehrwert"
        template = "portfolio/blocks/stats.html"


class TestimonialBlock(blocks.StructBlock):
    quote = blocks.TextBlock(label="Zitat")
    name = blocks.CharBlock(max_length=120, label="Name")
    role = blocks.CharBlock(required=False, max_length=160, label="Rolle")

    class Meta:
        icon = "openquote"
        label = "Kundenstimmen"
        template = "portfolio/blocks/testimonial.html"


PROJECT_BLOCK_REGION_CASE_STUDY = "case-study"
PROJECT_BLOCK_REGION_MEDIA = "media"
PROJECT_BLOCK_REGION_RESULTS = "results"
PROJECT_BLOCK_REGION_TESTIMONIAL = "testimonial"

PROJECT_BLOCK_REGIONS = {
    "statement": PROJECT_BLOCK_REGION_CASE_STUDY,
    "challenge_solution": PROJECT_BLOCK_REGION_CASE_STUDY,
    "full_width_image": PROJECT_BLOCK_REGION_MEDIA,
    "image_pair": PROJECT_BLOCK_REGION_MEDIA,
    "portrait_duo": PROJECT_BLOCK_REGION_MEDIA,
    "gallery": PROJECT_BLOCK_REGION_MEDIA,
    "stats": PROJECT_BLOCK_REGION_RESULTS,
    "testimonial": PROJECT_BLOCK_REGION_TESTIMONIAL,
}


def get_project_block_region(block_type):
    """Place every project block once, keeping future types visible by default."""

    return PROJECT_BLOCK_REGIONS.get(block_type, PROJECT_BLOCK_REGION_CASE_STUDY)


class ProjectBodyBlock(blocks.StreamBlock):
    """The complete editorial contract for a project case study."""

    statement = StatementBlock()
    challenge_solution = ChallengeSolutionBlock()
    full_width_image = FullWidthImageBlock()
    image_pair = ImagePairBlock()
    portrait_duo = PortraitDuoBlock()
    gallery = GalleryBlock()
    stats = StatsBlock()
    testimonial = TestimonialBlock()

    class Meta:
        label = "Projektinhalt"
