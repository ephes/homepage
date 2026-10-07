from cast.views import defaults as default_views_cast
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import TemplateView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.admin.views import account as wagtailadmin_account
from wagtail.documents import urls as wagtaildocs_urls

from homepage.core import views as core_views
from homepage.portfolio import views as portfolio_views
from homepage.users import api_auth, login_throttle

handler404 = default_views_cast.page_not_found
handler500 = default_views_cast.server_error
handler400 = default_views_cast.bad_request
handler403 = default_views_cast.permission_denied


urlpatterns = [
    path("", core_views.home, name="home"),
    path("robots.txt", core_views.robots_txt, name="robots_txt"),
    path("favicon.ico", core_views.favicon),
    path("impressum/", portfolio_views.imprint, name="portfolio_imprint"),
    path("datenschutz/", portfolio_views.privacy, name="portfolio_privacy"),
    path(
        "jochen/",
        core_views.jochen_profile,
        name="jochen",
    ),
    path(
        "katharina/",
        TemplateView.as_view(template_name="pages/katharina.html"),
        name="katharina",
    ),
    # Django Admin, use {% url 'admin:index' %}
    # Failed logins are throttled: see docs/admin_login_throttle.rst
    path(f"{settings.ADMIN_URL}login/", login_throttle.throttle_failed_logins(admin.site.login)),
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("homepage.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    # Threadedcomments
    path("show/comments/", include("cast.comments.urls")),
    # Indieweb
    path("indieweb/", include("indieweb.urls")),
    # Micropub local interface (form for creating posts)
    path("indieweb/micropub-form/", include("homepage.micropub.urls")),
    # rest
    # Throttled: see docs/api_token_auth.rst
    path("api/api-token-auth/", api_auth.obtain_auth_token, name="api-token-auth"),
    # url(r'api/', include('homepage.blogs.api.urls', namespace='api')),
    # Same view as rest_framework.urls' login, with failed logins throttled.
    path(
        "api-auth/login/",
        login_throttle.throttle_failed_logins(auth_views.LoginView.as_view(template_name="rest_framework/login.html")),
    ),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # re_path(r"^docs/", include_docs_urls(title="My Blog API service")),
    # Cast Blog
    path("blogs/", include("cast.urls", namespace="cast")),
    # Fediverse redirects etc.
    path("", include("homepage.fedi.urls", namespace="fedi")),
    # Resume
    path("resume/", include("django_resume.urls", namespace="resume")),
    # Explicit portfolio utility routes; Wagtail's page tree remains under /blogs/.
    path("portfolio/", include("homepage.portfolio.urls", namespace="portfolio")),
    # Wagtail
    # Failed logins are throttled: see docs/admin_login_throttle.rst
    path(
        f"{settings.WAGTAILADMIN_BASE_URL}login/",
        login_throttle.throttle_failed_logins(wagtailadmin_account.LoginView.as_view()),
    ),
    path(settings.WAGTAILADMIN_BASE_URL, include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("blogs/", include(wagtail_urls)),  # default is wagtail
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views_cast.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views_cast.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views_cast.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views_cast.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
