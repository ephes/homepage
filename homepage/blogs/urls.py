from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^(?P<slug>[^/]+)/add/$',
        view=views.PostCreateView.as_view(),
        name='blogpost_create'
    ),
    url(
        regex=r'^(?P<blog_slug>[^/]+)/(?P<slug>[^/]+)/update/$',
        view=views.PostUpdateView.as_view(),
        name='blogpost_update'
    ),
    url(
        regex=r'^(?P<blog_slug>[^/]+)/(?P<slug>[^/]+)/$',
        view=views.PostDetailView.as_view(),
        name='blogpost_detail'
    ),
    url(
        regex=r'^(?P<slug>[^/]+)/$',
        view=views.PostsListView.as_view(),
        name='blogpost_list'
    ),
    url(
        regex=r'^(?P<slug>[^/]+)/feed.xml$',
        view=views.LatestEntriesFeed(),
        name='blogpost_feed'
    ),
    url(
        regex=r'^(?P<slug>[^/]+)_detail/$',
        view=views.BlogDetailView.as_view(),
        name='blog_detail'
    ),
]
