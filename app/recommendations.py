from sqlalchemy import func
from .models import db, Item, ItemView, UserCategoryPreference, Order
from datetime import datetime

class RecommendationEngine:
    @staticmethod
    def track_item_view(user_id, item_id):
        view = ItemView(user_id=user_id, item_id=item_id)
        db.session.add(view)
        item = Item.query.get(item_id)
        if item and item.category:
            pref = UserCategoryPreference.query.filter_by(user_id=user_id, category=item.category).first()
            if pref:
                pref.score += 1.0
            else:
                pref = UserCategoryPreference(user_id=user_id, category=item.category, score=1.0)
                db.session.add(pref)
        db.session.commit()

    @staticmethod
    def get_recommendations(user_id, limit=6):
        # combine viewed categories, purchase categories, and trending items
        recommendations = []
        seen = set()

        viewed_cats = (
            db.session.query(Item.category, func.count(ItemView.id).label("cnt"))
            .join(Item, Item.id == ItemView.item_id)
            .filter(ItemView.user_id == user_id, Item.category.isnot(None))
            .group_by(Item.category)
            .order_by(func.count(ItemView.id).desc())
            .limit(3)
            .all()
        )
        purchased_cats = (
            db.session.query(Item.category)
            .join(Order, Order.item_id == Item.id)
            .filter(Order.buyer_id == user_id, Order.status == "completed", Item.category.isnot(None))
            .distinct()
            .all()
        )

        categories = [c[0] for c in viewed_cats] + [c[0] for c in purchased_cats]

        if categories:
            items = (
                Item.query.filter(Item.category.in_(categories), Item.seller_id != user_id)
                .order_by(Item.created_at.desc())
                .limit(limit)
                .all()
            )
            recommendations.extend(items)
            seen.update(i.id for i in items)

        if len(recommendations) < limit:
            trending = (
                db.session.query(Item)
                .outerjoin(ItemView, ItemView.item_id == Item.id)
                .filter(Item.seller_id != user_id, ~Item.id.in_(seen))
                .group_by(Item.id)
                .order_by(func.count(ItemView.id).desc(), Item.created_at.desc())
                .limit(limit - len(recommendations))
                .all()
            )
            recommendations.extend(trending)

        return recommendations[:limit]

    @staticmethod
    def get_similar_items(item_id, limit=6):
        item = Item.query.get(item_id)
        if not item or not item.category:
            return []
        price_delta = item.price * 0.5
        similar = (
            Item.query.filter(
                Item.id != item_id,
                Item.category == item.category,
                Item.price.between(item.price - price_delta, item.price + price_delta),
                Item.seller_id != item.seller_id,
            )
            .order_by(Item.created_at.desc())
            .limit(limit)
            .all()
        )
        return similar