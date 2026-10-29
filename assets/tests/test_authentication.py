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
