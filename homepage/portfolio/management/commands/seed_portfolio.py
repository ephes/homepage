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
            help="Create a draft portfolio page at the requested site or path if needed.",
        )
        parser.add_argument("--slug", help="Slug for the page created by --create (defaults to portfolio).")
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
    def handle(self, *args, create, slug=None, hostname=None, port=443, **options):
        for name in CATEGORIES:
            ProjectCategory.objects.get_or_create(name=name)

        portfolios = PortfolioIndexPage.objects.all()
        missing_page = "No portfolio page exists. Create one in the Wagtail admin or pass --create."
        if not create and not hostname:
            if not portfolios.exists():
                raise CommandError(missing_page)
            return

        if hostname:
            site = Site.objects.filter(hostname=hostname, port=port).first()
            if site is not None:
                existing = portfolios.filter(pk=site.root_page_id)
                if slug:
                    existing = existing.filter(slug=slug)
                if existing.exists():
                    return
                raise CommandError(
                    f"A Wagtail site for {hostname}:{port} already exists. "
                    "Its root does not match the requested portfolio."
                )
            if not create:
                raise CommandError(missing_page)
            parent = Page.get_first_root_node()
            if parent is None:
                raise CommandError("No Wagtail page tree root configured.")
        else:
            site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
            if site is None:
                raise CommandError("No default Wagtail site configured.")
            parent = site.root_page
            slug = slug or "portfolio"
            if portfolios.filter(pk=parent.pk).exists() or portfolios.child_of(parent).filter(slug=slug).exists():
                return

        # Wagtail assigns a unique sibling slug if none was supplied for a dedicated site.
        page = parent.add_child(instance=PortfolioIndexPage(title="Portfolio", slug=slug or "", live=False))
        if hostname:
            Site.objects.create(hostname=hostname, port=port, root_page=page, site_name=page.title)
        page.save_revision()
        self.stdout.write(f"Created {page.title} ({page.url_path})")
