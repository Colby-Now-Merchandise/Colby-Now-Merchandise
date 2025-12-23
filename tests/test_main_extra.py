import io
from unittest.mock import patch
from datetime import datetime
import pytest
from app.models import User, Item, Order, db, RecentlyViewed

EMBED_VECTOR = [0.1, 0.2, 0.3]


# ------------------------------------------
# helpers
# ------------------------------------------
@pytest.fixture
def logged_user(client, app):
    with app.app_context():
        u = User(
            email="extra@colby.edu",
            password="x",
            first_name="Extra",
            last_name="User",
            is_verified=True,
        )
        db.session.add(u)
        db.session.commit()
        client.post("/auth/login", data={"email": u.email, "password": "x"})
        return u


@pytest.fixture
def item(app, logged_user):
    with app.app_context():
        it = Item(
            title="Extra Item",
            description="desc",
            category="electronics",
            size="L",
            seller_type="student",
            condition="good",
            price=15.0,
            seller_id=logged_user.id,
            embedding=EMBED_VECTOR,
        )
        db.session.add(it)
        db.session.commit()
        return it


# ------------------------------------------
# /home edge cases
# ------------------------------------------
def test_home_no_items(client, logged_user):
    resp = client.get("/home")
    assert resp.status_code == 200


# ------------------------------------------
# /buy_item edge-case flows
# ------------------------------------------
@patch("app.main.generate_embedding", return_value=EMBED_VECTOR)
def test_buy_item_empty_semantic(mock_emb, client, logged_user):
    # Search returns empty semantic result → no matches
    resp = client.get("/buy_item?search=NoMatchTerm")
    assert resp.status_code == 200


def test_buy_item_filters_empty(client, logged_user):
    resp = client.get("/buy_item?category=unknown")
    assert resp.status_code == 200


def test_buy_item_sort_paths(client, logged_user, item):
    for sort in ["newest", "oldest", "price_low", "price_high"]:
        resp = client.get(f"/buy_item?sort_by={sort}")
        assert resp.status_code == 200


# ------------------------------------------
# /post-item: invalid file extension & exception branch
# ------------------------------------------
def test_post_item_invalid_extension(client, logged_user):
    bad_file = (io.BytesIO(b"data"), "file.txt")
    resp = client.post(
        "/post-item",
        data={"title": "X", "price": "5", "image": bad_file},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Invalid file type" in resp.data


@patch("app.main.generate_embedding", side_effect=Exception("Boom"))
def test_post_item_embedding_failure(mock_emb, client, logged_user):
    resp = client.post(
        "/post-item",
        data={"title": "Fail", "price": "9.99"},
        follow_redirects=True,
    )
    assert b"Error posting item" in resp.data


# ------------------------------------------
# /item/<id> 404 branch
# ------------------------------------------
def test_item_404(client, logged_user):
    resp = client.get("/item/999999", follow_redirects=True)
    assert resp.status_code == 404


# ------------------------------------------
# /seller/<id> 404 branch
# ------------------------------------------
def test_seller_404(client, logged_user):
    resp = client.get("/seller/999999", follow_redirects=True)
    assert resp.status_code == 404


# ------------------------------------------
# /my_listings multi-term search
# ------------------------------------------
def test_my_listings_multisearch(client, logged_user, item):
    resp = client.get("/my_listings?search=Extra Item")
    assert resp.status_code == 200


# ------------------------------------------
# /handle_order invalid action + 404
# ------------------------------------------
@pytest.fixture
def order(app, logged_user, item):
    with app.app_context():
        o = Order(buyer_id=logged_user.id, item_id=item.id, location="L", notes="N/A")
        db.session.add(o)
        db.session.commit()
        return o


def test_handle_order_invalid_action(client, logged_user, order):
    resp = client.post(f"/handle_order/{order.id}/invalid", follow_redirects=True)
    assert resp.status_code == 200


def test_handle_order_404(client, logged_user):
    resp = client.post("/handle_order/999999/approve")
    assert resp.status_code == 404


# ------------------------------------------
# /edit_item: unauthorized + invalid file + exception
# ------------------------------------------
def test_edit_item_unauthorized(client, logged_user, item, app):
    # create another user
    with app.app_context():
        other = User(
            email="other@colby.edu",
            password="x",
            first_name="O",
            last_name="U",
            is_verified=True,
        )
        db.session.add(other)
        db.session.commit()

    client.post("/auth/login", data={"email": "other@colby.edu", "password": "x"})

    resp = client.post(
        f"/edit_item/{item.id}",
        data={"title": "Nope"},
        follow_redirects=True,
    )
    assert b"Unauthorized" in resp.data


def test_edit_item_invalid_extension(client, logged_user, item):
    bad_file = (io.BytesIO(b"bad"), "bad.exe")
    resp = client.post(
        f"/edit_item/{item.id}",
        data={"title": "X", "price": "5", "image": bad_file},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200  # stays on page


@patch("app.main.generate_embedding", side_effect=Exception("fail"))
def test_edit_item_failure(mock_emb, client, logged_user, item):
    resp = client.post(
        f"/edit_item/{item.id}",
        data={"title": "Err", "price": "10.00"},
        follow_redirects=True,
    )
    assert b"Error updating item" in resp.data


# ------------------------------------------
# /delete_item unauthorized + 404
# ------------------------------------------
def test_delete_item_unauthorized(client, logged_user, item, app):
    with app.app_context():
        other = User(
            email="del@colby.edu",
            password="x",
            first_name="D",
            last_name="L",
            is_verified=True,
        )
        db.session.add(other)
        db.session.commit()

    client.post("/auth/login", data={"email": "del@colby.edu", "password": "x"})
    resp = client.post(f"/delete_item/{item.id}", follow_redirects=True)
    assert b"Unauthorized" in resp.data


def test_delete_item_404(client, logged_user):
    resp = client.post("/delete_item/999999")
    assert resp.status_code == 404


def test_buy_item_no_semantic_results(client, logged_user, monkeypatch):
    """Force semantic search to return empty list to cover the 'if not semantic_results' block."""
    from app.models import Item

    monkeypatch.setattr(Item, "semantic_search", lambda *args, **kwargs: [])

    resp = client.get("/buy_item?search=anything")
    assert resp.status_code == 200
    assert b"Test Item" not in resp.data


def test_post_item_missing_price(client, logged_user):
    """Cover the 'if not price_str' branch."""
    resp = client.post(
        "/post-item", data={"title": "No Price Item"}, follow_redirects=True
    )
    assert b"Price is required" in resp.data


def test_update_profile_with_image(client, logged_user):
    """Cover the profile image upload logic."""
    data = {
        "first_name": "New",
        "last_name": "Name",
        "profile_image": (io.BytesIO(b"fake image data"), "test.png"),
    }
    resp = client.post(
        "/update_profile",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert logged_user.profile_image is not None
