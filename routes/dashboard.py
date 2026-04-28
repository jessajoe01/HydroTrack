from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import db, TankerLog, SpecialRequest, Alert, User
from datetime import date, timedelta, datetime

dashboard_bp = Blueprint('dashboard', __name__)


# ── Calculate avg daily usage from tanker cycles ─────────
def calculate_avg_daily(user_id):
    logs = TankerLog.query.filter_by(
        user_id=user_id
    ).order_by(TankerLog.delivery_date.asc()).all()

    if len(logs) >= 2:
        total_litres = 0
        total_days   = 0
        for i in range(len(logs) - 1):
            cycle_days = (logs[i+1].delivery_date - logs[i].delivery_date).days
            if cycle_days > 0:
                total_litres += logs[i].litres
                total_days   += cycle_days
        if total_days > 0:
            return round(total_litres / total_days, 1)

    user = User.query.get(user_id)
    if user and user.family_size:
        return user.family_size * 50

    return None


# ── Core prediction function ─────────────────────────────
def get_days_remaining(user_id):
    logs = TankerLog.query.filter_by(
        user_id=user_id
    ).order_by(TankerLog.delivery_date.asc()).all()

    if not logs:
        return None, None, None

    last_log   = logs[-1]
    days_since = (date.today() - last_log.delivery_date).days
    avg_daily  = calculate_avg_daily(user_id)

    if not avg_daily:
        return None, None, None

    today          = date.today()
    active_request = SpecialRequest.query.filter(
        SpecialRequest.user_id    == user_id,
        SpecialRequest.start_date <= today,
        SpecialRequest.end_date   >= today,
        SpecialRequest.status     == 'Active'
    ).first()

    adjusted_daily = avg_daily
    if active_request:
        adjusted_daily += active_request.extra_litres_per_day

    current_level = last_log.litres - (days_since * adjusted_daily)
    current_level = max(current_level, 0)

    if adjusted_daily == 0:
        return current_level, avg_daily, None

    days_remaining = round(current_level / adjusted_daily, 1)
    return current_level, avg_daily, days_remaining


# ── Weekly checkin alert logic ───────────────────────────
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


# ── Generate weekly checkin alert ────────────────────────
def generate_weekly_checkin(user_id, days_since):
    alert = Alert(
        user_id        = user_id,
        alert_type     = 'weekly_checkin',
        message        = (
            f'It has been {days_since} days since your last tanker delivery. '
            f'Do you still have enough water or do you need a refill?'
        ),
        days_remaining = None,
        is_read        = 0
    )
    db.session.add(alert)
    db.session.commit()
    return alert


# ✅ NEW: Create level alerts (no duplicates in 24h)
def create_level_alert(user_id, alert_type, message, days_remaining):
    recent = datetime.now() - timedelta(days=1)

    exists = Alert.query.filter(
        Alert.user_id == user_id,
        Alert.alert_type == alert_type,
        Alert.created_on >= recent
    ).first()

    if exists:
        return None

    alert = Alert(
        user_id=user_id,
        alert_type=alert_type,
        message=message,
        days_remaining=days_remaining,
        is_read=0
    )
    db.session.add(alert)
    db.session.commit()
    return alert


# ── Dashboard summary endpoint ───────────────────────────
@dashboard_bp.route('/api/dashboard', methods=['GET'])
@login_required
def dashboard():
    user_id = current_user.id

    current_level, avg_daily, days_remaining = get_days_remaining(user_id)

    # ✅ NEW: Auto-generate water level alerts
    if days_remaining is not None:

        if days_remaining <= 2:
            create_level_alert(
                user_id,
                '2_day',
                '🚨 Critical: Water may run out in 2 days!',
                days_remaining
            )

        elif days_remaining <= 3:
            create_level_alert(
                user_id,
                '3_day',
                '⚠️ Warning: Only 3 days of water remaining.',
                days_remaining
            )

        elif days_remaining <= 4:
            create_level_alert(
                user_id,
                '4_day',
                '🔔 Reminder: About 4 days of water left.',
                days_remaining
            )

    # Weekly checkin
    last_delivery = TankerLog.query.filter_by(
        user_id=user_id
    ).order_by(TankerLog.delivery_date.desc()).first()

    weekly_alert = None
    if last_delivery and should_send_weekly_checkin(user_id):
        days_since   = (date.today() - last_delivery.delivery_date).days
        weekly_alert = generate_weekly_checkin(user_id, days_since)

    # Unread alerts count
    unread_alerts = Alert.query.filter_by(
        user_id=user_id, is_read=0
    ).count()

    # Active special request
    today          = date.today()
    active_request = SpecialRequest.query.filter(
        SpecialRequest.user_id    == user_id,
        SpecialRequest.start_date <= today,
        SpecialRequest.end_date   >= today,
        SpecialRequest.status     == 'Active'
    ).first()

    # Status colour
    if days_remaining is None:
        status = 'unknown'
    elif days_remaining <= 2:
        status = 'critical'
    elif days_remaining <= 4:
        status = 'warning'
    else:
        status = 'safe'

    return jsonify({
        'current_level'   : round(current_level, 1) if current_level else 0,
        'avg_daily_usage' : avg_daily,
        'days_remaining'  : days_remaining,
        'status'          : status,
        'unread_alerts'   : unread_alerts,
        'weekly_alert'    : {
            'alert_id': weekly_alert.id,
            'message' : weekly_alert.message
        } if weekly_alert else None,
        'active_request'  : {
            'title'               : active_request.title,
            'end_date'            : str(active_request.end_date),
            'extra_litres_per_day': active_request.extra_litres_per_day
        } if active_request else None
    }), 200