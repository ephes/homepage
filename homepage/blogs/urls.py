from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^(?P<slug>[^/]+)/add/$',
        view=views.PostCreateView.as_view(),
        name='blogpost-create'
    ),
    url(
        regex=r'^(?P<blog_slug>[^/]+)/(?P<slug>[^/]+)/$',
        view=views.PostDetailView.as_view(),
        name='blogpost-detail'
    ),
    url(
        regex=r'^(?P<slug>[^/]+)/$',
        view=views.PostsListView.as_view(),
        name='blogpost-list'
    ),
    url(
        regex=r'^(?P<slug>[^/]+)_detail/$',
        view=views.BlogDetailView.as_view(),
        name='blog-detail'
    ),
]
