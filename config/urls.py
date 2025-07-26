from cast.views import defaults as default_views_cast
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.authtoken import views as authtokenviews
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from homepage.core import views as core_views

handler404 = default_views_cast.page_not_found
handler500 = default_views_cast.server_error
handler400 = default_views_cast.bad_request
handler403 = default_views_cast.permission_denied


urlpatterns = [
    path("", core_views.home, name="home"),
    path("favicon.ico", core_views.favicon),
    path("about/", TemplateView.as_view(template_name="pages/about.html"), name="about"),
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
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("homepage.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    # Threadedcomments
    path("show/comments/", include("fluent_comments.urls")),
    # Indieweb
    path("indieweb/", include("indieweb.urls")),
    # Micropub local interface (form for creating posts)
    path("indieweb/micropub-form/", include("homepage.micropub.urls")),
    # rest
    path("api/api-token-auth/", authtokenviews.obtain_auth_token),
    # url(r'api/', include('homepage.blogs.api.urls', namespace='api')),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # re_path(r"^docs/", include_docs_urls(title="My Blog API service")),
    # Cast Blog
    path("blogs/", include("cast.urls", namespace="cast")),
    # Fediverse redirects etc.
    path("", include("homepage.fedi.urls", namespace="fedi")),
    # Resume
    path("resume/", include("django_resume.urls", namespace="resume")),
    # Wagtail
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
