from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, TankerLog, DailyUsage
from datetime import date, timedelta

tanker_bp = Blueprint('tanker', __name__)


# ── Log a new tanker delivery ────────────────────────────
@tanker_bp.route('/tanker/log', methods=['POST'])
@login_required
def log_tanker():
    data = request.get_json()

    if not data.get('litres') or not data.get('delivery_date'):
        return jsonify({'error': 'Litres and delivery date are required'}), 400

    cost_per_litre = data.get('cost_per_litre', 0)
    litres         = float(data['litres'])
    total_cost     = litres * cost_per_litre

    log = TankerLog(
        user_id        = current_user.id,
        delivery_date  = date.fromisoformat(data['delivery_date']),
        litres         = litres,
        cost_per_litre = cost_per_litre,
        total_cost     = total_cost,
        supplier_name  = data.get('supplier_name', ''),
        notes          = data.get('notes', '')
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'status'     : 'success',
        'message'    : 'Tanker delivery logged successfully',
        'log_id'     : log.id,
        'total_cost' : total_cost
    }), 201


# ── Get all tanker logs for current user ─────────────────
@tanker_bp.route('/tanker/history', methods=['GET'])
@login_required
def tanker_history():
    logs = TankerLog.query.filter_by(
        user_id=current_user.id
    ).order_by(TankerLog.delivery_date.desc()).all()

    return jsonify([{
        'id'            : log.id,
        'delivery_date' : str(log.delivery_date),
        'litres'        : log.litres,
        'cost_per_litre': log.cost_per_litre,
        'total_cost'    : log.total_cost,
        'supplier_name' : log.supplier_name,
        'notes'         : log.notes
    } for log in logs]), 200


# ── Log daily usage manually ─────────────────────────────
@tanker_bp.route('/tanker/usage', methods=['POST'])
@login_required
def log_usage():
    data = request.get_json()

    if not data.get('litres_used') or not data.get('usage_date'):
        return jsonify({'error': 'litres_used and usage_date are required'}), 400

    # Check if entry for this date already exists
    existing = DailyUsage.query.filter_by(
        user_id    = current_user.id,
        usage_date = date.fromisoformat(data['usage_date'])
    ).first()

    if existing:
        existing.litres_used = float(data['litres_used'])
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Usage updated'}), 200

    usage = DailyUsage(
        user_id    = current_user.id,
        usage_date = date.fromisoformat(data['usage_date']),
        litres_used = float(data['litres_used'])
    )
    db.session.add(usage)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Daily usage logged'}), 201


# ── Get usage history ────────────────────────────────────
@tanker_bp.route('/tanker/usage/history', methods=['GET'])
@login_required
def usage_history():
    records = DailyUsage.query.filter_by(
        user_id=current_user.id
    ).order_by(DailyUsage.usage_date.desc()).limit(30).all()

    return jsonify([{
        'date'        : str(r.usage_date),
        'litres_used' : r.litres_used
    } for r in records]), 200