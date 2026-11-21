import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse
from test_plus.test import TestCase

from ..views import UserDetailView, UserListView, UserRedirectView, UserUpdateView
from .factories import UserFactory

user_list_view = UserListView.as_view()
user_detail_view = UserDetailView.as_view()


class BaseUserTestCase(TestCase):
    def setUp(self):
        self.user = self.make_user()
        self.factory = RequestFactory()


class TestUserRedirectView(BaseUserTestCase):
    def test_get_redirect_url(self):
        # Instantiate the view directly. Never do this outside a test!
        view = UserRedirectView()
        # Generate a fake request
        request = self.factory.get("/fake-url")
        # Attach the user to the request
        request.user = self.user
        # Attach the request to the view
        view.request = request
        # Expect: '/users/testuser/', as that is the default username for
        #   self.make_user()
        self.assertEqual(view.get_redirect_url(), "/users/testuser/")


class TestUserUpdateView(BaseUserTestCase):
    def setUp(self):
        # call BaseUserTestCase.setUp()
        super().setUp()
        # Instantiate the view directly. Never do this outside a test!
        self.view = UserUpdateView()
        # Generate a fake request
        request = self.factory.get("/fake-url")
        # Attach the user to the request
        request.user = self.user
        # Attach the request to the view
        self.view.request = request

    def test_get_success_url(self):
        # Expect: '/users/testuser/', as that is the default username for
        #   self.make_user()
        self.assertEqual(self.view.get_success_url(), "/users/testuser/")

    def test_get_object(self):
        # Expect: self.user, as that is the request's user object
        self.assertEqual(self.view.get_object(), self.user)


@pytest.mark.django_db
@pytest.mark.parametrize("delete_account", [False, True], ids=["admin-edit", "account-deleted"])
def test_profile_post_preserves_other_account_changes(monkeypatch, delete_account):
    user = UserFactory(name="Original Name", email="old@example.com")
    get_object = UserUpdateView.get_object

    def interleave_account_change(view):
        profile = get_object(view)
        account = type(user).objects.filter(pk=user.pk)
        if delete_account:
            account.delete()
        else:
            account.update(email="new@example.com", is_staff=True)
        return profile

    monkeypatch.setattr(UserUpdateView, "get_object", interleave_account_change)
    # Call the view directly so ATOMIC_REQUESTS cannot roll back the simulated admin action.
    request = RequestFactory().post(reverse("users:update"), {"name": "  New Name  "})
    request.user = user
    update_view = UserUpdateView.as_view()

    if delete_account:
        with pytest.raises(Http404):
            update_view(request)
        assert not type(user).objects.filter(pk=user.pk).exists()
    else:
        response = update_view(request)
        assert response.status_code == 302
        assert response.url == reverse("users:detail", kwargs={"username": user.username})
        user.refresh_from_db()
        assert user.name == "New Name"
        assert user.email == "new@example.com"
        assert user.is_staff


@pytest.mark.django_db
class TestUserDirectoryAccess:
    """Logged-in users must not be able to enumerate other accounts.

    The views are called directly so the templates are not rendered; the
    context shows what would be.
    """

    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    @pytest.fixture
    def user(self):
        return UserFactory(username="member")

    @pytest.fixture
    def other(self):
        return UserFactory(username="other-member", name="Other Member")

    @pytest.fixture
    def staff(self):
        return UserFactory(username="staff-member", is_staff=True)

    @staticmethod
    def _get(request_factory, path, user):
        request = request_factory.get(path)
        request.user = user
        return request

    def test_list_redirects_anonymous_to_login(self, request_factory):
        response = user_list_view(self._get(request_factory, "/users/", AnonymousUser()))
        assert response.status_code == 302
        assert response.url.startswith(reverse("account_login"))

    def test_list_forbidden_for_non_staff(self, request_factory, user, other):
        with pytest.raises(PermissionDenied):
            user_list_view(self._get(request_factory, "/users/", user))

    def test_list_allowed_for_staff(self, request_factory, staff, other):
        response = user_list_view(self._get(request_factory, "/users/", staff))
        assert response.status_code == 200
        assert list(response.context_data["object_list"]) == [other, staff]

    def test_detail_redirects_anonymous_to_login(self, request_factory, other):
        path = f"/users/{other.username}/"
        response = user_detail_view(self._get(request_factory, path, AnonymousUser()), username=other.username)
        assert response.status_code == 302
        assert response.url.startswith(reverse("account_login"))

    def test_detail_shows_own_profile(self, request_factory, user):
        path = f"/users/{user.username}/"
        response = user_detail_view(self._get(request_factory, path, user), username=user.username)
        assert response.status_code == 200
        assert response.context_data["object"] == user

    def test_detail_of_other_user_is_404_for_non_staff(self, request_factory, user, other):
        path = f"/users/{other.username}/"
        with pytest.raises(Http404):
            user_detail_view(self._get(request_factory, path, user), username=other.username)

    def test_detail_of_missing_user_is_404_for_non_staff(self, request_factory, user):
        with pytest.raises(Http404):
            user_detail_view(self._get(request_factory, "/users/missing/", user), username="missing")

    def test_detail_of_other_user_allowed_for_staff(self, request_factory, staff, other):
        path = f"/users/{other.username}/"
        response = user_detail_view(self._get(request_factory, path, staff), username=other.username)
        assert response.status_code == 200
        assert response.context_data["object"] == other
