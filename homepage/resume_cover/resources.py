"""Explicit ownership of public, pre-rendered resume resources."""

from django.conf import settings

DEFAULT_PUBLIC_RESOURCES = {
    "katharina": {
        "cv_pdf": "resume/katharina-lebenslauf.pdf",
        "cover_pdf": "resume/katharina-anschreiben.pdf",
    },
}


def resources_for_slug(slug):
    """Unlisted resumes never inherit another resume's published documents."""
    configured = getattr(settings, "RESUME_PUBLIC_RESOURCES", DEFAULT_PUBLIC_RESOURCES)
    return dict(configured.get(slug, {}))
