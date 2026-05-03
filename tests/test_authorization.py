"""
Member 5 — Role-Based Access Control tests.

Verifies that endpoints enforce role restrictions:
- Admin-only endpoints reject non-admins
- Authors can create posts; readers cannot
- Users can only edit/delete their own content (unless admin)
"""
from tests.conftest import auth_headers


# ─── /auth/users (admin only) ─────────────────────────────────

class TestAdminOnlyEndpoints:
    def test_admin_can_list_users(self, client, admin_token):
        response = client.get("/auth/users", headers=auth_headers(admin_token))
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_reader_cannot_list_users(self, client, reader_token):
        response = client.get("/auth/users", headers=auth_headers(reader_token))
        assert response.status_code == 403

    def test_author_cannot_list_users(self, client, author_token):
        response = client.get("/auth/users", headers=auth_headers(author_token))
        assert response.status_code == 403

    def test_unauthenticated_cannot_list_users(self, client):
        response = client.get("/auth/users")
        assert response.status_code == 401


# ─── Post creation: AUTHOR + ADMIN only ───────────────────────

class TestPostCreationRoles:
    def test_admin_can_create_post(self, client, admin_token):
        response = client.post(
            "/posts/",
            json={"title": "Admin post", "body": "Body of the admin post here."},
            headers=auth_headers(admin_token),
        )
        assert response.status_code in (200, 201)

    def test_author_can_create_post(self, client, author_token):
        response = client.post(
            "/posts/",
            json={"title": "Author post", "body": "Body of the author post here."},
            headers=auth_headers(author_token),
        )
        assert response.status_code in (200, 201)

    def test_reader_cannot_create_post(self, client, reader_token):
        response = client.post(
            "/posts/",
            json={"title": "Reader post", "body": "This should be blocked."},
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 403


# ─── Post deletion: only owner or admin ───────────────────────

class TestPostDeletionRoles:
    def test_author_can_delete_own_post(self, client, author_token):
        created = client.post(
            "/posts/",
            json={"title": "Mine to delete", "body": "About to be removed."},
            headers=auth_headers(author_token),
        ).json()
        response = client.delete(
            f"/posts/{created['id']}",
            headers=auth_headers(author_token),
        )
        assert response.status_code in (200, 204)

    def test_admin_can_delete_any_post(self, client, author_token, admin_token):
        # Author creates
        created = client.post(
            "/posts/",
            json={"title": "Author's post", "body": "Author wrote this."},
            headers=auth_headers(author_token),
        ).json()
        # Admin deletes
        response = client.delete(
            f"/posts/{created['id']}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code in (200, 204)

    def test_reader_cannot_delete_others_post(self, client, author_token, reader_token):
        created = client.post(
            "/posts/",
            json={"title": "Author's", "body": "Author owns this content."},
            headers=auth_headers(author_token),
        ).json()
        response = client.delete(
            f"/posts/{created['id']}",
            headers=auth_headers(reader_token),
        )
        assert response.status_code in (403, 401)


# ─── Comment ownership ────────────────────────────────────────

class TestCommentOwnership:
    def _make_post(self, client, token):
        return client.post(
            "/posts/",
            json={"title": "Post for comments", "body": "Body of the post here."},
            headers=auth_headers(token),
        ).json()

    def test_user_can_edit_own_comment(self, client, author_token, reader_token):
        post = self._make_post(client, author_token)
        comment = client.post(
            f"/posts/{post['id']}/comments",
            json={"body": "Original comment"},
            headers=auth_headers(reader_token),
        ).json()
        response = client.put(
            f"/comments/{comment['id']}",
            json={"body": "Edited comment"},
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 200
        assert response.json()["body"] == "Edited comment"

    def test_user_cannot_edit_others_comment(
        self, client, author_token, reader_token, second_reader_token
    ):
        post = self._make_post(client, author_token)
        comment = client.post(
            f"/posts/{post['id']}/comments",
            json={"body": "Reader 1 wrote this"},
            headers=auth_headers(reader_token),
        ).json()
        # Reader 2 tries to edit Reader 1's comment
        response = client.put(
            f"/comments/{comment['id']}",
            json={"body": "Hijacked"},
            headers=auth_headers(second_reader_token),
        )
        assert response.status_code == 403

    def test_admin_can_delete_any_comment(self, client, author_token, reader_token, admin_token):
        post = self._make_post(client, author_token)
        comment = client.post(
            f"/posts/{post['id']}/comments",
            json={"body": "About to be moderated"},
            headers=auth_headers(reader_token),
        ).json()
        response = client.delete(
            f"/comments/{comment['id']}",
            headers=auth_headers(admin_token),
        )
        assert response.status_code in (200, 204)
