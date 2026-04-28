
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import TankerLog
from datetime import date

cost_bp = Blueprint('cost', __name__)

@cost_bp.route('/cost/summary', methods=['GET'])
@login_required
def cost_summary():
    logs = TankerLog.query.filter_by(user_id=current_user.id).all()

    total_spent     = sum(l.total_cost or 0 for l in logs)
    total_litres    = sum(l.litres for l in logs)
    avg_cost_litre  = round(total_spent / total_litres, 2) if total_litres else 0

    # This month only
    this_month = [
        l for l in logs
        if l.delivery_date.month == date.today().month
        and l.delivery_date.year == date.today().year
    ]
    monthly_spent = sum(l.total_cost or 0 for l in this_month)

    return jsonify({
        'total_spent'       : round(total_spent, 2),
        'total_litres'      : round(total_litres, 2),
        'avg_cost_per_litre': avg_cost_litre,
        'monthly_spent'     : round(monthly_spent, 2),
        'total_deliveries'  : len(logs)
    }), 200