"""
Member 5 — Posts CRUD tests (happy paths).

Verifies the basic CRUD lifecycle for posts works end-to-end:
- Create
- Read all (list)
- Read by ID
- Update
- Delete
"""
from tests.conftest import auth_headers


class TestPostsCRUD:
    def test_create_post_returns_post_with_id(self, client, author_token):
        response = client.post(
            "/posts/",
            json={"title": "My first post", "body": "Hello, world! This is body."},
            headers=auth_headers(author_token),
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["title"] == "My first post"
        assert data["body"] == "Hello, world! This is body."
        assert "id" in data
        assert "author_id" in data

    def test_get_all_posts_returns_list(self, client, author_token):
        # Create a couple of posts first
        for i in range(3):
            client.post(
                "/posts/",
                json={"title": f"Post {i}", "body": f"Body of post number {i} here."},
                headers=auth_headers(author_token),
            )

        response = client.get("/posts/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_get_post_by_id_returns_correct_post(self, client, author_token):
        created = client.post(
            "/posts/",
            json={"title": "Findable post", "body": "Body of the findable post."},
            headers=auth_headers(author_token),
        ).json()

        response = client.get(f"/posts/{created['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["title"] == "Findable post"

    def test_update_post_changes_title_and_body(self, client, author_token):
        created = client.post(
            "/posts/",
            json={"title": "Original title", "body": "Original body content here."},
            headers=auth_headers(author_token),
        ).json()

        response = client.put(
            f"/posts/{created['id']}",
            json={"title": "Updated title", "body": "Updated body content here."},
            headers=auth_headers(author_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated title"
        assert data["body"] == "Updated body content here."

    def test_delete_post_removes_it(self, client, author_token):
        created = client.post(
            "/posts/",
            json={"title": "To be deleted", "body": "This post will be deleted."},
            headers=auth_headers(author_token),
        ).json()

        delete_response = client.delete(
            f"/posts/{created['id']}",
            headers=auth_headers(author_token),
        )
        assert delete_response.status_code in (200, 204)

        # Confirm it's gone
        get_response = client.get(f"/posts/{created['id']}")
        assert get_response.status_code == 404
