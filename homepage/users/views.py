from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView

from .models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    """Show a profile to its owner, or to staff.

    Other users get a 404, so the page does not confirm whether a username
    exists.
    """

    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(pk=self.request.user.pk)


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


class UserUpdateView(LoginRequiredMixin, UpdateView):

    fields = ["name"]

    model = User

    # send the user back to their own page after a successful update
    def get_success_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})

    def get_object(self):
        return get_object_or_404(User, pk=self.request.user.pk)

    def form_valid(self, form):
        updated = User.objects.filter(pk=self.request.user.pk).update(name=form.cleaned_data["name"])
        if not updated:
            raise Http404
        return HttpResponseRedirect(self.get_success_url())


class UserListView(UserPassesTestMixin, ListView):
    """List accounts by username, one page at a time. Staff only.

    Anonymous visitors are redirected to the login page; logged-in non-staff
    users get a 403.
    """

    model = User
    ordering = "username"
    paginate_by = 50

    def test_func(self):
        return self.request.user.is_staff
