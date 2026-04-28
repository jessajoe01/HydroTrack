from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Alert, TankerLog
from datetime import date, timedelta, datetime

alerts_bp = Blueprint('alerts', __name__)


# ── Weekly check-in logic ────────────────────────────────
def should_send_weekly_checkin(user_id):
    last_delivery = TankerLog.query.filter_by(
        user_id=user_id
    ).order_by(TankerLog.delivery_date.desc()).first()

    if not last_delivery:
        return False

    days_since = (date.today() - last_delivery.delivery_date).days
    if days_since < 7:
        return False

    one_week_ago = datetime.now() - timedelta(days=7)
    existing = Alert.query.filter(
        Alert.user_id    == user_id,
        Alert.alert_type == 'weekly_checkin',
        Alert.created_on >= one_week_ago
    ).first()

    return existing is None


def generate_weekly_checkin(user_id, days_since):
    alert = Alert(
        user_id    = user_id,
        alert_type = 'weekly_checkin',
        message    = (
            f'It has been {days_since} days since your last tanker delivery. '
            f'Do you need a refill?'
        ),
        is_read    = 0
    )
    db.session.add(alert)
    db.session.commit()
    return alert


# ── Trigger weekly alert ─────────────────────────────────
@alerts_bp.route('/api/alerts/check', methods=['POST'])
@login_required
def check_alerts():
    user_id = current_user.id

    last_delivery = TankerLog.query.filter_by(
        user_id=user_id
    ).order_by(TankerLog.delivery_date.desc()).first()

    if not last_delivery:
        return jsonify({'alert_sent': False, 'message': 'No delivery logged yet'}), 200

    days_since = (date.today() - last_delivery.delivery_date).days

    if should_send_weekly_checkin(user_id):
        alert = generate_weekly_checkin(user_id, days_since)
        return jsonify({
            'alert_sent': True,
            'alert_id'  : alert.id,
            'message'   : alert.message
        }), 200

    return jsonify({'alert_sent': False, 'message': 'No alert needed yet'}), 200


# ── Get all alerts ───────────────────────────────────────
@alerts_bp.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    alerts = Alert.query.filter_by(
        user_id=current_user.id
    ).order_by(Alert.created_on.desc()).all()

    return jsonify([{
        'id'        : a.id,
        'alert_type': a.alert_type,
        'message'   : a.message,
        'is_read'   : a.is_read,
        'created_on': a.created_on.isoformat()
    } for a in alerts]), 200


# ✅ FIXED: '/api/alerts/unread' registered BEFORE '/api/alerts/<int:alert_id>/respond'
# Flask matches routes top-down — if the dynamic route came first,
# "unread" would be parsed as an integer ID and fail with 404.
@alerts_bp.route('/api/alerts/unread', methods=['GET'])
@login_required
def unread_count():
    count = Alert.query.filter_by(
        user_id=current_user.id,
        is_read=0
    ).count()
    return jsonify({'unread_count': count}), 200


# ── Respond to alert ─────────────────────────────────────
@alerts_bp.route('/api/alerts/<int:alert_id>/respond', methods=['POST'])
@login_required
def respond_to_alert(alert_id):
    data        = request.get_json() or {}
    needs_water = data.get('needs_water', False)

    alert = Alert.query.filter_by(
        id      = alert_id,
        user_id = current_user.id
    ).first()

    if not alert:
        return jsonify({'error': 'Alert not found'}), 404

    alert.is_read = 1

    if needs_water:
        refill_alert = Alert(
            user_id    = current_user.id,
            alert_type = 'refill_needed',
            message    = (
                'You have indicated you need a water refill. '
                'Please check the supplier portal to place an order.'
            ),
            is_read    = 0
        )
        db.session.add(refill_alert)

    db.session.commit()
    return jsonify({
        'status' : 'success',
        'action' : 'refill_needed' if needs_water else 'no_refill',
        'message': 'Refill alert created.' if needs_water else 'Noted! We will check again next week.'
    }), 200