from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import TemplateView
from django.views import defaults as default_views
from django.http import HttpResponse

from rest_framework.documentation import include_docs_urls
from rest_framework.authtoken import views as authtokenviews

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='pages/home.html'), name='home'),
    url(r'^about/$', TemplateView.as_view(template_name='pages/about.html'), name='about'),

    # Django Admin, use {% url 'admin:index' %}
    url(settings.ADMIN_URL, admin.site.urls),

    # User management
    url(r'^users/', include('homepage.users.urls', namespace='users')),
    url(r'^accounts/', include('allauth.urls')),

    # Your stuff: custom urls includes go here

    # Blog
    # url(r'^blogs/', include('homepage.blogs.urls', namespace='blogs')),

    # CKEditor upload
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),

    # Cast Blog
    url(r'^blogs/', include('cast.urls', namespace='cast')),

    # rest
    url(r'^api/api-token-auth/', authtokenviews.obtain_auth_token),
    # url(r'api/', include('homepage.blogs.api.urls', namespace='api')),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^docs/', include_docs_urls(title='My Blog API service')),

    # robots.txt
    url(r'^robots.txt',
        lambda x: HttpResponse("User-Agent: *\nDisallow: /*claas", content_type="text/plain"),
        name="robots_file"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        url(r'^400/$', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')}),
        url(r'^403/$', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')}),
        url(r'^404/$', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')}),
        url(r'^500/$', default_views.server_error),
    ]
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
