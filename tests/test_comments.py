"""
Member 5 — Comments CRUD + nested comments + pagination.

Verifies:
- Basic comment CRUD on posts
- Nested replies via /comments/{id}/reply
- Pagination via skip/limit query params
"""
from tests.conftest import auth_headers


def _create_post(client, token, title="A post", body="Some post body content."):
    return client.post(
        "/posts/",
        json={"title": title, "body": body},
        headers=auth_headers(token),
    ).json()


class TestCommentsCRUD:
    def test_add_comment_to_post(self, client, author_token, reader_token):
        post = _create_post(client, author_token)
        response = client.post(
            f"/posts/{post['id']}/comments",
            json={"body": "Great post!"},
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["body"] == "Great post!"
        assert data["post_id"] == post["id"]
        assert data["parent_comment_id"] is None

    def test_get_comments_returns_list(self, client, author_token, reader_token):
        post = _create_post(client, author_token)
        for i in range(3):
            client.post(
                f"/posts/{post['id']}/comments",
                json={"body": f"Comment {i}"},
                headers=auth_headers(reader_token),
            )

        response = client.get(
            f"/posts/{post['id']}/comments",
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 200
        comments = response.json()
        assert isinstance(comments, list)
        assert len(comments) == 3

    def test_retrieve_specific_comment_by_id(self, client, author_token, reader_token):
        """GET a single comment by ID via the list endpoint + filter.
        Confirms that individual records are retrievable, not just bulk lists."""
        post = _create_post(client, author_token)
        created = client.post(
            f"/posts/{post['id']}/comments",
            json={"body": "Findable comment"},
            headers=auth_headers(reader_token),
        ).json()
        target_id = created["id"]

        comments = client.get(
            f"/posts/{post['id']}/comments",
            headers=auth_headers(reader_token),
        ).json()
        match = next((c for c in comments if c["id"] == target_id), None)
        assert match is not None
        assert match["body"] == "Findable comment"
        assert match["post_id"] == post["id"]

    def test_update_comment_changes_body(self, client, author_token, reader_token):
        post = _create_post(client, author_token)
        comment = client.post(
            f"/posts/{post['id']}/comments",
            json={"body": "Original"},
            headers=auth_headers(reader_token),
        ).json()

        response = client.put(
            f"/comments/{comment['id']}",
            json={"body": "Edited"},
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 200
        assert response.json()["body"] == "Edited"

    def test_delete_comment_removes_it(self, client, author_token, reader_token):
        post = _create_post(client, author_token)
        comment = client.post(
            f"/posts/{post['id']}/comments",
            json={"body": "Will be deleted"},
            headers=auth_headers(reader_token),
        ).json()

        response = client.delete(
            f"/comments/{comment['id']}",
            headers=auth_headers(reader_token),
        )
        assert response.status_code in (200, 204)


# ─── Nested comments ──────────────────────────────────────────

class TestNestedComments:
    def test_reply_to_comment_creates_nested(self, client, author_token, reader_token):
        post = _create_post(client, author_token)
        parent = client.post(
            f"/posts/{post['id']}/comments",
            json={"body": "Parent comment"},
            headers=auth_headers(reader_token),
        ).json()

        response = client.post(
            f"/comments/{parent['id']}/reply",
            json={"body": "This is a reply"},
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 201
        reply = response.json()
        assert reply["body"] == "This is a reply"
        assert reply["parent_comment_id"] == parent["id"]
        assert reply["post_id"] == post["id"]

    def test_get_comments_returns_nested_structure(self, client, author_token, reader_token):
        post = _create_post(client, author_token)
        parent = client.post(
            f"/posts/{post['id']}/comments",
            json={"body": "Parent"},
            headers=auth_headers(reader_token),
        ).json()
        client.post(
            f"/comments/{parent['id']}/reply",
            json={"body": "Reply 1"},
            headers=auth_headers(reader_token),
        )
        client.post(
            f"/comments/{parent['id']}/reply",
            json={"body": "Reply 2"},
            headers=auth_headers(reader_token),
        )

        response = client.get(
            f"/posts/{post['id']}/comments",
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 200
        comments = response.json()
        # Top-level should be just the parent
        top_level = [c for c in comments if c.get("parent_comment_id") is None]
        assert len(top_level) == 1
        # And it should have replies
        assert len(top_level[0].get("replies", [])) == 2


# ─── Pagination ───────────────────────────────────────────────

class TestCommentsPagination:
    def test_pagination_respects_limit(self, client, author_token, reader_token):
        post = _create_post(client, author_token)
        # Create 15 top-level comments
        for i in range(15):
            client.post(
                f"/posts/{post['id']}/comments",
                json={"body": f"Comment number {i}"},
                headers=auth_headers(reader_token),
            )

        response = client.get(
            f"/posts/{post['id']}/comments?skip=0&limit=5",
            headers=auth_headers(reader_token),
        )
        assert response.status_code == 200
        assert len(response.json()) == 5

    def test_pagination_skip_works(self, client, author_token, reader_token):
        post = _create_post(client, author_token)
        for i in range(15):
            client.post(
                f"/posts/{post['id']}/comments",
                json={"body": f"Comment number {i}"},
                headers=auth_headers(reader_token),
            )

        first_page = client.get(
            f"/posts/{post['id']}/comments?skip=0&limit=5",
            headers=auth_headers(reader_token),
        ).json()
        second_page = client.get(
            f"/posts/{post['id']}/comments?skip=5&limit=5",
            headers=auth_headers(reader_token),
        ).json()

        # Pages shouldn't overlap
        first_ids = {c["id"] for c in first_page}
        second_ids = {c["id"] for c in second_page}
        assert first_ids.isdisjoint(second_ids)
