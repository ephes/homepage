from django.urls import path, re_path

from . import views

app_name = "users"
urlpatterns = [
    path("", view=views.UserListView.as_view(), name="list"),
    re_path(r"^~redirect/$", view=views.UserRedirectView.as_view(), name="redirect"),
    re_path(
        r"^(?P<username>[\w.@+-]+)/$",
        view=views.UserDetailView.as_view(),
        name="detail",
    ),
    re_path(r"^~update/$", view=views.UserUpdateView.as_view(), name="update"),
]
