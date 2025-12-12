# tests/test_validators_models.py
from app.validators import is_valid_email, is_strong_password
from app.models import User, Item, Order, Chat, db
from datetime import datetime


def test_is_valid_email_colby():
    assert is_valid_email("abc123@colby.edu")
    assert not is_valid_email("abc123@gmail.com")
    assert not is_valid_email("not-an-email")
    assert not is_valid_email("")


def test_is_strong_password_valid():
    pw = "StrongPass123!"
    assert is_strong_password(pw)


def test_is_strong_password_invalid_variants():
    assert not is_strong_password("short1!")              # too short
    assert not is_strong_password("alllowercase123!")     # no uppercase
    assert not is_strong_password("ALLUPPERCASE123!")     # no lowercase
    assert not is_strong_password("NoNumber!!!!!")        # no number
    assert not is_strong_password("NoSpecialChar1234")    # no special


def test_user_and_item_repr(app):
    u = User(
        name="Alice",
        email="alice@colby.edu",
        password="hashed",
        is_verified=True,
    )
    db.session.add(u)
    db.session.commit()
    assert "alice@colby.edu" in repr(u)

    item = Item(
        title="Laptop",
        description="Nice laptop",
        category="electronics",
        size="15in",
        seller_type="student",
        condition="used",
        price=500.0,
        seller_id=u.id,
    )
    db.session.add(item)
    db.session.commit()
    r = repr(item)
    assert "Laptop" in r and "500.0" in r


def test_item_search_no_term_returns_query(app):
    # Just ensure it returns a query object and doesn't crash
    q = Item.search(None)
    assert hasattr(q, "all")


def test_item_search_with_term(app):
    u = User(
        name="Bob",
        email="bob@colby.edu",
        password="hashed",
        is_verified=True,
    )
    db.session.add(u)
    db.session.commit()

    item1 = Item(
        title="Blue Jacket",
        description="Warm and cozy",
        category="clothing",
        size="M",
        seller_type="student",
        condition="new",
        price=60.0,
        seller_id=u.id,
    )
    item2 = Item(
        title="Math Book",
        description="Calculus",
        category="books",
        size="N/A",
        seller_type="student",
        condition="used",
        price=20.0,
        seller_id=u.id,
    )
    db.session.add_all([item1, item2])
    db.session.commit()

    results = Item.search("Jacket").all()
    assert item1 in results
    assert item2 not in results


def test_order_and_chat_models(app):
    seller = User(
        name="Seller",
        email="seller@colby.edu",
        password="x",
        is_verified=True,
    )
    buyer = User(
        name="Buyer",
        email="buyer@colby.edu",
        password="y",
        is_verified=True,
    )
    db.session.add_all([seller, buyer])
    db.session.commit()

    item = Item(
        title="Desk",
        description="Wooden desk",
        category="furniture",
        size="L",
        seller_type="student",
        condition="used",
        price=100.0,
        seller_id=seller.id,
    )
    db.session.add(item)
    db.session.commit()

    order = Order(
        buyer_id=buyer.id,
        item_id=item.id,
        price_offer=90.0,
        location="Library",
        payment_method="cash",
        notes="After class",
        status="pending",
    )
    db.session.add(order)
    db.session.commit()
    assert "Order" in repr(order)

    msg = Chat(
        sender_id=buyer.id,
        receiver_id=seller.id,
        content="Hi, is this still available?",
        timestamp=datetime.utcnow(),
    )
    db.session.add(msg)
    db.session.commit()

    assert msg in buyer.messages_sent.all()
    assert msg in seller.messages_received.all()
