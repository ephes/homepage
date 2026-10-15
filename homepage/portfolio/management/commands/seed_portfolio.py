from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Page, Site

from homepage.portfolio.models import PortfolioIndexPage, ProjectCategory

CATEGORIES = ("Web", "Digital", "Print", "Illustration")


class Command(BaseCommand):
    help = (
        "Create the project categories and, with --create, an empty portfolio page. "
        "Editorial content is entered in the Wagtail admin; existing content is never changed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--create",
            action="store_true",
            help="Create a draft portfolio page below the default site's root page if none exists.",
        )
        parser.add_argument("--slug", default="portfolio", help="Slug for the page created by --create.")
        parser.add_argument(
            "--hostname",
            help=(
                "With --create: create the page as root page of a new Wagtail site for this hostname "
                "(e.g. design.wersdoerfer.de) instead of below the default site."
            ),
        )
        parser.add_argument(
            "--port",
            type=int,
            default=443,
            help="Port of the Wagtail site created with --hostname (443 for HTTPS, e.g. 8000 locally).",
        )

    @transaction.atomic
    def handle(self, *args, create, slug, hostname=None, port=443, **options):
        for name in CATEGORIES:
            ProjectCategory.objects.get_or_create(name=name)

        pages = list(PortfolioIndexPage.objects.all())
        if not pages and create:
            page = self.create_page(slug, hostname, port)
            self.stdout.write(f"Created {page.title} ({page.url_path})")
        elif not pages:
            raise CommandError("No portfolio page exists. Create one in the Wagtail admin or pass --create.")

    def create_page(self, slug, hostname=None, port=443):
        page = PortfolioIndexPage(title="Portfolio", slug=slug, live=False)
        if hostname:
            if Site.objects.filter(hostname=hostname).exists():
                raise CommandError(f"A Wagtail site for {hostname} already exists.")
            Page.get_first_root_node().add_child(instance=page)
            Site.objects.create(hostname=hostname, port=port, root_page=page, site_name=page.title)
        else:
            site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
            if site is None:
                raise CommandError("No default Wagtail site configured.")
            site.root_page.add_child(instance=page)
        page.save_revision()
        return page
