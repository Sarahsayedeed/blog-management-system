"""
Member 6 — Edge case tests.

Covers what happens when the API gets weird input:
- Missing or malformed payloads
- Missing resources (404)
- Duplicate entries
- Invalid field formats (e.g. bad emails, too-short usernames)
- Empty strings, oversized strings
"""
from tests.conftest import auth_headers


# ─── Invalid registration payloads ────────────────────────────

class TestRegistrationEdgeCases:
    def test_missing_username_returns_422(self, client):
        response = client.post(
            "/auth/register",
            json={"email": "x@test.com", "password": "password123"},
        )
        assert response.status_code == 422

    def test_missing_email_returns_422(self, client):
        response = client.post(
            "/auth/register",
            json={"username": "noemail", "password": "password123"},
        )
        assert response.status_code == 422

    def test_invalid_email_format_returns_422(self, client):
        response = client.post(
            "/auth/register",
            json={
                "username": "bademail",
                "email": "not-an-email-address",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    def test_empty_payload_returns_422(self, client):
        response = client.post("/auth/register", json={})
        assert response.status_code == 422

    def test_completely_malformed_json_is_rejected(self, client):
        response = client.post(
            "/auth/register",
            content="this is not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in (422, 400)


# ─── Missing resources ────────────────────────────────────────

class TestNotFoundResources:
    def test_get_nonexistent_post_returns_404(self, client):
        response = client.get("/posts/999999")
        assert response.status_code == 404

    def test_update_nonexistent_post_returns_404(self, client, author_token):
        response = client.put(
            "/posts/999999",
            json={"title": "Updated", "body": "Updated body content here."},
            headers=auth_headers(author_token),
        )
        assert response.status_code == 404

    def test_delete_nonexistent_post_returns_404(self, client, author_token):
        response = client.delete(
            "/posts/999999",
            headers=auth_headers(author_token),
        )
        assert response.status_code == 404

    def test_update_nonexistent_comment_returns_404(self, client, reader_token):
        response = client.put(
            "/comments/999999",
            json={"body": "Edit"},
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 404

    def test_delete_nonexistent_comment_returns_404(self, client, reader_token):
        response = client.delete(
            "/comments/999999",
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 404

    def test_reply_to_nonexistent_comment_returns_404(self, client, reader_token):
        response = client.post(
            "/comments/999999/reply",
            json={"body": "Reply to ghost"},
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 404


# ─── Duplicates ───────────────────────────────────────────────

class TestDuplicates:
    def test_duplicate_username_returns_409(self, client):
        client.post(
            "/auth/register",
            json={
                "username": "samename",
                "email": "first@test.com",
                "password": "password123",
            },
        )
        response = client.post(
            "/auth/register",
            json={
                "username": "samename",
                "email": "second@test.com",
                "password": "password123",
            },
        )
        assert response.status_code == 409

    def test_duplicate_email_returns_409(self, client):
        client.post(
            "/auth/register",
            json={
                "username": "user_a",
                "email": "shared@test.com",
                "password": "password123",
            },
        )
        response = client.post(
            "/auth/register",
            json={
                "username": "user_b",
                "email": "shared@test.com",
                "password": "password123",
            },
        )
        assert response.status_code == 409


# ─── Empty / oversized strings ────────────────────────────────

class TestStringValidation:
    def test_empty_post_title_is_rejected(self, client, author_token):
        response = client.post(
            "/posts/",
            json={"title": "", "body": "Body content here."},
            headers=auth_headers(author_token),
        )
        assert response.status_code == 422

    def test_post_title_too_long_is_rejected(self, client, author_token):
        response = client.post(
            "/posts/",
            json={
                "title": "x" * 1000,  # well over any reasonable limit
                "body": "Body content here.",
            },
            headers=auth_headers(author_token),
        )
        assert response.status_code == 422

    def test_short_password_is_rejected(self, client):
        response = client.post(
            "/auth/register",
            json={
                "username": "shortpw",
                "email": "shortpw@test.com",
                "password": "x",  # too short
            },
        )
        assert response.status_code == 422


# ─── Path parameter validation ────────────────────────────────

class TestPathParamValidation:
    def test_non_integer_post_id_returns_422(self, client):
        response = client.get("/posts/not-a-number")
        assert response.status_code == 422

    def test_negative_post_id_returns_404_or_422(self, client):
        response = client.get("/posts/-1")
        assert response.status_code in (404, 422)
