import pytest
from datetime import datetime, timedelta
from app.models import User, Chat, db
import pytz


@pytest.fixture
def two_users(app, client):
    with app.app_context():
        u1 = User(
            email="u1@colby.edu",
            password="x",
            first_name="A",
            last_name="One",
            is_verified=True,
        )
        u2 = User(
            email="u2@colby.edu",
            password="x",
            first_name="B",
            last_name="Two",
            is_verified=True,
        )
        db.session.add_all([u1, u2])
        db.session.commit()

        # login u1
        client.post("/auth/login", data={"email": u1.email, "password": "x"})

        return u1, u2


# --------------------------------------
# chat page — no messages
# --------------------------------------
def test_chat_empty(client, two_users):
    u1, u2 = two_users
    resp = client.get(f"/chat/{u2.id}")
    assert resp.status_code == 200


# --------------------------------------
# chat page — invalid receiver (404)
# --------------------------------------
def test_chat_invalid_receiver(client, two_users):
    resp = client.get("/chat/999999")
    assert resp.status_code == 404


# --------------------------------------
# send_message missing content
# --------------------------------------
def test_send_message_missing_content(client, two_users):
    resp = client.post("/send_message", json={}, follow_redirects=True)
    assert resp.status_code == 400


# --------------------------------------
# send_message success
# --------------------------------------
def test_send_message_success(client, two_users):
    u1, u2 = two_users
    resp = client.post(
        "/send_message",
        json={"receiver_id": u2.id, "content": "hi"},
    )
    assert resp.json["success"] is True


# --------------------------------------
# get_messages — no messages
# --------------------------------------
def test_get_messages_empty(client, two_users):
    u1, u2 = two_users
    resp = client.get(f"/get_messages/{u2.id}")
    assert resp.json == []


# --------------------------------------
# get_messages — with messages
# --------------------------------------
def test_get_messages_with_data(client, two_users, app):
    u1, u2 = two_users
    with app.app_context():
        msg = Chat(sender_id=u1.id, receiver_id=u2.id, content="test")
        db.session.add(msg)
        db.session.commit()

    resp = client.get(f"/get_messages/{u2.id}")
    assert len(resp.json) == 1
    assert resp.json[0]["content"] == "test"


# --------------------------------------
# get_messages — timestamp conversion
# --------------------------------------
def test_get_messages_time_format(client, two_users, app):
    u1, u2 = two_users
    with app.app_context():
        t = datetime.utcnow() - timedelta(hours=1)
        msg = Chat(
            sender_id=u1.id,
            receiver_id=u2.id,
            content="time",
            timestamp=t
        )
        db.session.add(msg)
        db.session.commit()

    resp = client.get(f"/get_messages/{u2.id}")
    assert "•" in resp.json[0]["time"]  # format "Jan 01 • 12:00 PM"


# --------------------------------------
# inbox — empty
# --------------------------------------
def test_inbox_empty(client, two_users):
    resp = client.get("/inbox")
    assert resp.status_code == 200


# --------------------------------------
# inbox — with conversations
# --------------------------------------
def test_inbox_with_messages(client, two_users, app):
    u1, u2 = two_users
    with app.app_context():
        c = Chat(sender_id=u1.id, receiver_id=u2.id, content="hi")
        db.session.add(c)
        db.session.commit()

    resp = client.get("/inbox")
    assert b"Two" in resp.data  # u2 displayed
