import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username="security_test_user",
        password="SecureTestPassword123!",
        role="viewer",
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_valid_login(api_client, test_user):
    response = api_client.post(
        "/api/token/",
        {
            "username": "security_test_user",
            "password": "SecureTestPassword123!",
        },
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_invalid_login(api_client, test_user):
    response = api_client.post(
        "/api/token/",
        {
            "username": "security_test_user",
            "password": "WrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_password_is_hashed(test_user):
    assert test_user.password != "SecureTestPassword123!"
    assert check_password("SecureTestPassword123!", test_user.password)


@pytest.mark.django_db
def test_protected_endpoint_rejects_anonymous(api_client):
    response = api_client.get("/api/me/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_protected_endpoint_rejects_invalid_token(api_client):
    api_client.credentials(
        HTTP_AUTHORIZATION="Bearer invalid.jwt.token"
    )

    response = api_client.get("/api/me/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_new_password_uses_argon2(test_user):
    assert test_user.password.startswith("argon2$")
    assert check_password(
        "SecureTestPassword123!",
        test_user.password
    )


@pytest.mark.django_db
def test_user_serializer_rejects_weak_password():
    from assets.serializers import UserSerializer

    serializer = UserSerializer(
        data={
            "username": "weak_password_user",
            "password": "123",
            "role": "viewer",
        }
    )

    assert not serializer.is_valid()
    assert "password" in serializer.errors


@pytest.mark.django_db
def test_user_creation_requires_password():
    from assets.serializers import UserSerializer

    serializer = UserSerializer(
        data={
            "username": "no_password_user",
            "role": "viewer",
        }
    )

    assert not serializer.is_valid()
    assert "password" in serializer.errors


@pytest.mark.django_db
def test_user_serializer_rejects_similar_password():
    from assets.serializers import UserSerializer

    serializer = UserSerializer(
        data={
            "username": "similarpassword123",
            "password": "similarpassword123",
            "role": "viewer",
        }
    )

    assert not serializer.is_valid()
    assert "password" in serializer.errors


@pytest.mark.django_db
def test_user_password_update_rejects_weak_password(test_user):
    from assets.serializers import UserSerializer

    serializer = UserSerializer(
        test_user,
        data={"password": "123"},
        partial=True,
    )

    assert not serializer.is_valid()
    assert "password" in serializer.errors


@pytest.mark.django_db
def test_login_rate_limit_blocks_repeated_failures(api_client, test_user):
    responses = []

    for _ in range(7):
        response = api_client.post(
            "/api/token/",
            {
                "username": "security_test_user",
                "password": "IncorrectPassword123!",
            },
            format="json",
        )
        responses.append(response.status_code)

    assert 429 in responses, (
        f"Expected HTTP 429 after repeated failed logins, "
        f"but received: {responses}"
    )


@pytest.mark.django_db
def test_login_rate_limit_threshold(api_client, test_user):
    from django.core.cache import cache

    cache.clear()

    statuses = []

    for _ in range(6):
        response = api_client.post(
            "/api/token/",
            {
                "username": "security_test_user",
                "password": "IncorrectPassword123!",
            },
            format="json",
        )
        statuses.append(response.status_code)

    assert statuses == [401, 401, 401, 401, 401, 429]


@pytest.mark.django_db
def test_refresh_token_rotation_blacklists_old_token(api_client, test_user):
    from django.core.cache import cache

    # Prevent login throttling from affecting this test.
    cache.clear()

    # Step 1: Log in and obtain the original refresh token.
    login_response = api_client.post(
        "/api/token/",
        {
            "username": "security_test_user",
            "password": "SecureTestPassword123!",
        },
        format="json",
    )

    assert login_response.status_code == 200

    original_refresh = login_response.data["refresh"]

    # Step 2: Exchange the original refresh token.
    refresh_response = api_client.post(
        "/api/token/refresh/",
        {"refresh": original_refresh},
        format="json",
    )

    assert refresh_response.status_code == 200
    assert "access" in refresh_response.data
    assert "refresh" in refresh_response.data

    new_refresh = refresh_response.data["refresh"]

    assert new_refresh != original_refresh

    # Step 3: Attempt to reuse the old refresh token.
    reuse_response = api_client.post(
        "/api/token/refresh/",
        {"refresh": original_refresh},
        format="json",
    )

    assert reuse_response.status_code == 401

    # Step 4: Confirm the replacement refresh token works.
    new_refresh_response = api_client.post(
        "/api/token/refresh/",
        {"refresh": new_refresh},
        format="json",
    )

    assert new_refresh_response.status_code == 200


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(api_client, test_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    # Generate tokens for the test user.
    refresh = RefreshToken.for_user(test_user)
    access = str(refresh.access_token)
    refresh_string = str(refresh)

    # Authenticate using the access token.
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access}"
    )

    # Logout using the refresh token.
    logout_response = api_client.post(
        "/api/logout/",
        {"refresh": refresh_string},
        format="json",
    )

    assert logout_response.status_code == 200

    # The revoked refresh token must no longer work.
    refresh_response = api_client.post(
        "/api/token/refresh/",
        {"refresh": refresh_string},
        format="json",
    )

    assert refresh_response.status_code == 401


@pytest.mark.django_db
def test_logout_rejects_missing_refresh_token(api_client, test_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    access = str(RefreshToken.for_user(test_user).access_token)

    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access}"
    )

    response = api_client.post(
        "/api/logout/",
        {},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_logout_requires_authentication(api_client, test_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = str(RefreshToken.for_user(test_user))

    response = api_client.post(
        "/api/logout/",
        {"refresh": refresh},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_logout_cannot_revoke_another_users_token(api_client, test_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    from assets.models import User

    other_user = User.objects.create_user(
        username="another_security_user",
        password="AnotherSecurePassword123!",
        role="viewer",
    )

    # Authenticate as the first user.
    access = str(RefreshToken.for_user(test_user).access_token)

    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access}"
    )

    # Attempt to revoke the second user's refresh token.
    other_refresh = str(RefreshToken.for_user(other_user))

    response = api_client.post(
        "/api/logout/",
        {"refresh": other_refresh},
        format="json",
    )

    assert response.status_code == 400

    # Confirm the other user's refresh token still works.
    refresh_response = api_client.post(
        "/api/token/refresh/",
        {"refresh": other_refresh},
        format="json",
    )

    assert refresh_response.status_code == 200


@pytest.mark.django_db
def test_expired_access_token_is_rejected(api_client, test_user):
    from datetime import timedelta
    from rest_framework_simplejwt.tokens import AccessToken

    # Create an access token that expired one minute ago.
    token = AccessToken.for_user(test_user)
    token.set_exp(
        from_time=token.current_time,
        lifetime=timedelta(minutes=-1),
    )

    # Attempt to access an authenticated endpoint.
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {str(token)}"
    )

    response = api_client.get("/api/me/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_expired_refresh_token_is_rejected(api_client, test_user):
    from datetime import timedelta
    from rest_framework_simplejwt.tokens import RefreshToken

    # Create a refresh token that expired one minute ago.
    token = RefreshToken.for_user(test_user)
    token.set_exp(
        from_time=token.current_time,
        lifetime=timedelta(minutes=-1),
    )

    # Attempt to exchange the expired refresh token.
    response = api_client.post(
        "/api/token/refresh/",
        {"refresh": str(token)},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_login_does_not_enumerate_users(api_client, test_user):
    from django.core.cache import cache

    cache.clear()

    wrong_password = api_client.post(
        "/api/token/",
        {
            "username": test_user.username,
            "password": "IncorrectPassword123!",
        },
        format="json",
    )

    unknown_user = api_client.post(
        "/api/token/",
        {
            "username": "nonexistent_security_user",
            "password": "IncorrectPassword123!",
        },
        format="json",
    )

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.data == unknown_user.data


@pytest.mark.django_db
def test_anonymous_user_cannot_create_accounts(api_client):
    response = api_client.post(
        "/api/users/",
        {
            "username": "unauthorized_new_user",
            "password": "SecureNewPassword123!",
            "role": "viewer",
        },
        format="json",
    )

    assert response.status_code == 401
    assert not User.objects.filter(
        username="unauthorized_new_user"
    ).exists()


@pytest.mark.django_db
def test_non_staff_user_cannot_create_accounts(api_client, test_user):
    api_client.force_authenticate(user=test_user)

    response = api_client.post(
        "/api/users/",
        {
            "username": "unauthorized_new_user",
            "password": "SecureNewPassword123!",
            "role": "viewer",
        },
        format="json",
    )

    assert response.status_code == 403
    assert not User.objects.filter(
        username="unauthorized_new_user"
    ).exists()


@pytest.mark.django_db
def test_staff_admin_creates_user_with_hashed_password(api_client):
    admin = User.objects.create_superuser(
        username="security_admin",
        password="SecureAdminPassword123!",
    )
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        "/api/users/",
        {
            "username": "new_security_viewer",
            "password": "SecureViewerPassword123!",
            "role": "viewer",
        },
        format="json",
    )

    assert response.status_code == 201, response.data

    new_user = User.objects.get(username="new_security_viewer")
    assert new_user.password.startswith("argon2$")
    assert new_user.check_password("SecureViewerPassword123!")
    assert "password" not in response.data


@pytest.mark.django_db
def test_staff_admin_updates_password_securely(api_client):
    admin = User.objects.create_superuser(
        username="security_admin",
        password="SecureAdminPassword123!",
    )
    target = User.objects.create_user(
        username="password_update_target",
        password="OriginalSecurePassword123!",
        role="viewer",
    )

    api_client.force_authenticate(user=admin)

    response = api_client.patch(
        f"/api/users/{target.id}/",
        {"password": "UpdatedSecurePassword123!"},
        format="json",
    )

    assert response.status_code == 200, response.data

    target.refresh_from_db()

    assert target.password.startswith("argon2$")
    assert target.check_password("UpdatedSecurePassword123!")
    assert not target.check_password("OriginalSecurePassword123!")
    assert "password" not in response.data


@pytest.mark.django_db
def test_non_staff_cannot_change_another_users_password(api_client, test_user):
    target = User.objects.create_user(
        username="protected_password_target",
        password="OriginalSecurePassword123!",
        role="viewer",
    )

    api_client.force_authenticate(user=test_user)

    response = api_client.patch(
        f"/api/users/{target.id}/",
        {"password": "UnauthorizedPassword123!"},
        format="json",
    )

    assert response.status_code == 403

    target.refresh_from_db()
    assert target.check_password("OriginalSecurePassword123!")
    assert not target.check_password("UnauthorizedPassword123!")


@pytest.mark.django_db
def test_non_staff_cannot_promote_self_to_admin(api_client, test_user):
    api_client.force_authenticate(user=test_user)

    response = api_client.patch(
        f"/api/users/{test_user.id}/",
        {"role": "admin", "is_staff": True},
        format="json",
    )

    assert response.status_code == 403

    test_user.refresh_from_db()
    assert test_user.role == "viewer"
    assert test_user.is_staff is False


@pytest.mark.django_db
def test_non_staff_cannot_delete_another_user(api_client, test_user):
    target = User.objects.create_user(
        username="protected_delete_target",
        password="SecureTargetPassword123!",
        role="viewer",
    )

    api_client.force_authenticate(user=test_user)

    response = api_client.delete(f"/api/users/{target.id}/")

    assert response.status_code == 403
    assert User.objects.filter(pk=target.id).exists()


@pytest.mark.django_db
def test_staff_viewer_cannot_manage_users(api_client):
    staff_viewer = User.objects.create_user(
        username="staff_viewer",
        password="SecureViewerPassword123!",
        role="viewer",
        is_staff=True,
    )
    target = User.objects.create_user(
        username="protected_role_target",
        password="OriginalSecurePassword123!",
        role="viewer",
    )

    api_client.force_authenticate(user=staff_viewer)

    response = api_client.patch(
        f"/api/users/{target.id}/",
        {"role": "admin"},
        format="json",
    )

    assert response.status_code == 403

    target.refresh_from_db()
    assert target.role == "viewer"


@pytest.mark.django_db
def test_staff_application_admin_can_manage_users(api_client):
    admin = User.objects.create_superuser(
        username="authorized_role_admin",
        password="SecureAdminPassword123!",
    )
    target = User.objects.create_user(
        username="authorized_role_target",
        password="SecureTargetPassword123!",
        role="viewer",
    )

    api_client.force_authenticate(user=admin)

    response = api_client.patch(
        f"/api/users/{target.id}/",
        {"role": "editor"},
        format="json",
    )

    assert response.status_code == 200, response.data

    target.refresh_from_db()
    assert target.role == "editor"


@pytest.mark.django_db
def test_login_throttle_cannot_bypass_with_spoofed_xff(api_client, test_user):
    from django.core.cache import cache

    cache.clear()
    statuses = []

    for attempt in range(6):
        response = api_client.post(
            "/api/token/",
            {
                "username": "security_test_user",
                "password": "IncorrectPassword123!",
            },
            format="json",
            REMOTE_ADDR="127.0.0.1",
            HTTP_X_FORWARDED_FOR=f"192.0.2.{attempt + 1}",
        )
        statuses.append(response.status_code)

    assert statuses == [401, 401, 401, 401, 401, 429], (
        f"Login throttle bypass detected: {statuses}"
    )
