# routes/prediction.py
# ─────────────────────────────────────────────────────────────
# ML Prediction Engine for HydroTrack
#
# Three strategies, automatically selected by data availability:
#
#   Strategy 1 — FamilySizeFallback  (< 2 tanker logs)
#     Uses family_size × 50L/day (standard Indian estimate)
#     Confidence: 20–25%
#
#   Strategy 2 — TankerCycleAverage  (2–4 tanker logs)
#     Divides litres by days between deliveries across all cycles
#     Confidence: 40–65%
#
#   Strategy 3 — TankerCycleLR       (5+ tanker logs)
#     Linear Regression on cycle index → predicts trend in usage
#     Pure Python — no sklearn needed, no install required
#     Confidence: 30–92% based on R² and data volume
#
# Vacation mode adjustment:
#   If an active VacationMode exists for today, daily usage is
#   multiplied by (occupancy_percent / 100) before computing days.
#
# Every prediction is saved to PredictionHistory so accuracy
# can be tracked and shown to the user over time.
# ─────────────────────────────────────────────────────────────

from datetime   import datetime, date, timedelta
from flask      import Blueprint, jsonify, request
from flask_login import login_required, current_user

from models     import db, TankerLog, DailyUsage, PredictionHistory, User, VacationMode

prediction_bp = Blueprint('prediction', __name__)


# ═════════════════════════════════════════════════════════════
#  INTERNAL: vacation adjustment
#  Returns multiplier 0.0–1.0 based on active vacation today
# ═════════════════════════════════════════════════════════════
def _vacation_multiplier(user_id: int) -> float:
    today   = date.today()
    vac     = VacationMode.query.filter(
        VacationMode.user_id    == user_id,
        VacationMode.start_date <= today,
        VacationMode.end_date   >= today,
        VacationMode.is_active  == True
    ).first()

    if vac:
        return round(vac.occupancy_percent / 100.0, 2)
    return 1.0   # no vacation → full usage


# ═════════════════════════════════════════════════════════════
#  STRATEGY 1 — Family Size Fallback
# ═════════════════════════════════════════════════════════════
def _strategy_family_size(user_id: int) -> dict:
    user      = User.query.get(user_id)
    family    = user.family_size if user and user.family_size else 4
    avg_daily = float(family * 50)

    return {
        'avg_daily_usage' : round(avg_daily, 1),
        'confidence'      : 22,
        'model_used'      : 'FamilySizeFallback',
        'data_points_used': 0,
        'trend'           : 'stable',
        'note'            : (
            f'Estimated from family size ({family} people × 50 L/day). '
            f'Log more tanker deliveries to improve accuracy.'
        )
    }


# ═════════════════════════════════════════════════════════════
#  STRATEGY 2 — Tanker Cycle Average
# ═════════════════════════════════════════════════════════════
def _strategy_tanker_cycle(user_id: int, logs: list) -> dict:
    total_litres = 0.0
    total_days   = 0
    cycles       = []

    for i in range(len(logs) - 1):
        days   = (logs[i + 1].delivery_date - logs[i].delivery_date).days
        litres = logs[i].litres
        if days > 0:
            total_litres += litres
            total_days   += days
            cycles.append(litres / days)

    if total_days == 0:
        return _strategy_family_size(user_id)

    avg_daily  = round(total_litres / total_days, 1)
    n_cycles   = len(cycles)
    confidence = min(40 + (n_cycles * 8), 65)

    return {
        'avg_daily_usage' : avg_daily,
        'confidence'      : confidence,
        'model_used'      : 'TankerCycleAverage',
        'data_points_used': n_cycles,
        'trend'           : 'stable',
        'note'            : (
            f'Based on {n_cycles} delivery cycle(s). '
            f'Log {max(0, 5 - len(logs))} more deliveries to enable ML prediction.'
        )
    }


# ═════════════════════════════════════════════════════════════
#  STRATEGY 3 — Linear Regression on tanker cycles
#  Pure Python — no external libraries needed
# ═════════════════════════════════════════════════════════════
def _strategy_linear_regression(user_id: int, logs: list) -> dict:
    # Build cycle data points
    cycles = []
    for i in range(len(logs) - 1):
        days   = (logs[i + 1].delivery_date - logs[i].delivery_date).days
        litres = logs[i].litres
        if days > 0:
            cycles.append({
                'index'    : i,
                'avg_daily': litres / days,
                'litres'   : litres,
                'days'     : days,
            })

    if len(cycles) < 2:
        return _strategy_tanker_cycle(user_id, logs)

    n      = len(cycles)
    x_vals = [c['index']     for c in cycles]
    y_vals = [c['avg_daily'] for c in cycles]

    x_mean = sum(x_vals) / n
    y_mean = sum(y_vals) / n

    # Slope and intercept
    numerator   = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
    denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        slope, intercept = 0.0, y_mean
    else:
        slope     = numerator / denominator
        intercept = y_mean - slope * x_mean

    # Predict for next cycle
    next_index      = cycles[-1]['index'] + 1
    predicted_daily = intercept + slope * next_index
    predicted_daily = max(predicted_daily, 10.0)   # floor — can't use negative water

    # R² score for confidence
    ss_res = sum((y_vals[i] - (intercept + slope * x_vals[i])) ** 2 for i in range(n))
    ss_tot = sum((y_vals[i] - y_mean) ** 2 for i in range(n))
    r2     = max(0.0, 1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    data_score = min(n / 10.0, 1.0)        # full score at 10+ cycles
    confidence = int(r2 * 60 + data_score * 30 + 10)
    confidence = max(30, min(92, confidence))

    # Trend direction
    recent_avg  = sum(c['avg_daily'] for c in cycles[-3:]) / min(3, n)
    earlier_avg = sum(c['avg_daily'] for c in cycles[:3])  / min(3, n)

    if   recent_avg > earlier_avg * 1.10: trend = 'increasing'
    elif recent_avg < earlier_avg * 0.90: trend = 'decreasing'
    else:                                 trend = 'stable'

    return {
        'avg_daily_usage' : round(predicted_daily, 1),
        'confidence'      : confidence,
        'model_used'      : 'TankerCycleLR',
        'data_points_used': n,
        'trend'           : trend,
        'r2_score'        : round(r2, 3),
        'note'            : (
            f'ML prediction from {n} delivery cycles. '
            f'R²={round(r2, 2)} — '
            + ('good fit.' if r2 >= 0.7 else 'improving with more data.')
        )
    }


# ═════════════════════════════════════════════════════════════
#  ALERT LEVEL — maps days remaining to status string
#  Must match the status values dashboard.html already uses
# ═════════════════════════════════════════════════════════════
def _alert_level(days) -> str:
    if   days is None: return 'unknown'
    elif days <= 2:    return 'critical'
    elif days <= 4:    return 'warning'
    else:              return 'safe'


# ═════════════════════════════════════════════════════════════
#  SAVE PREDICTION — write to PredictionHistory
# ═════════════════════════════════════════════════════════════
def _save_prediction(user_id: int, result: dict, current_level: float) -> int:
    record = PredictionHistory(
        user_id                  = user_id,
        prediction_date          = date.today(),
        predicted_daily_usage    = result['avg_daily_usage'],
        predicted_days_remaining = result['predicted_days'],
        confidence_score         = result['confidence'] / 100.0,  # store as 0.0–1.0
        model_used               = result['model_used'],
        tanker_capacity          = round(current_level, 1),
        data_points_used         = result['data_points_used'],
    )
    db.session.add(record)
    db.session.commit()
    return record.id


# ═════════════════════════════════════════════════════════════
#  MAIN PUBLIC FUNCTION
#  Called by dashboard route — returns full prediction dict
#
#  Parameters:
#    user_id           : current user's id
#    current_level     : estimated litres remaining in tank
#    avg_daily_override: pass the dashboard's already-computed
#                        avg so we don't recompute from scratch
# ═════════════════════════════════════════════════════════════
def run_prediction(user_id: int, current_level: float,
                   avg_daily_override: float = None) -> dict:

    # ── Pick strategy ──────────────────────────────────────────
    if avg_daily_override:
        logs      = TankerLog.query.filter_by(user_id=user_id).all()
        n_cycles  = max(0, len(logs) - 1)
        strategy  = {
            'avg_daily_usage' : round(avg_daily_override, 1),
            'confidence'      : min(40 + n_cycles * 8, 65) if n_cycles >= 2 else 22,
            'model_used'      : 'TankerCycleAverage',
            'data_points_used': n_cycles,
            'trend'           : 'stable',
            'note'            : f'Based on {n_cycles} delivery cycle(s).'
        }
    else:
        logs = (
            TankerLog.query
            .filter_by(user_id=user_id)
            .order_by(TankerLog.delivery_date.asc())
            .all()
        )
        if   len(logs) < 2:  strategy = _strategy_family_size(user_id)
        elif len(logs) < 5:  strategy = _strategy_tanker_cycle(user_id, logs)
        else:                strategy = _strategy_linear_regression(user_id, logs)

    avg_daily = strategy['avg_daily_usage']

    # ── Vacation mode adjustment ───────────────────────────────
    vac_multiplier  = _vacation_multiplier(user_id)
    adjusted_daily  = round(avg_daily * vac_multiplier, 1)
    on_vacation     = vac_multiplier < 1.0

    # ── Days remaining ─────────────────────────────────────────
    if adjusted_daily > 0 and current_level is not None:
        days_remaining  = int(current_level / adjusted_daily)
        exhaustion_date = (
            date.today() + timedelta(days=days_remaining)
        ).strftime('%d %b %Y')
    else:
        days_remaining  = None
        exhaustion_date = 'Unknown'

    result = {
        **strategy,
        'predicted_days'   : days_remaining,
        'adjusted_daily'   : adjusted_daily,
        'vacation_active'  : on_vacation,
        'vacation_factor'  : vac_multiplier,
        'current_level'    : round(current_level, 1) if current_level else 0,
        'exhaustion_date'  : exhaustion_date,
        'alert_level'      : _alert_level(days_remaining),
    }

    # ── Save to history ────────────────────────────────────────
    if days_remaining is not None:
        result['prediction_id'] = _save_prediction(user_id, result, current_level)

    return result


# ═════════════════════════════════════════════════════════════
#  API: GET /api/prediction/latest
#  Returns the most recent unconfirmed prediction
# ═════════════════════════════════════════════════════════════
@prediction_bp.route('/api/prediction/latest', methods=['GET'])
@login_required
def latest_prediction():
    record = (
        PredictionHistory.query
        .filter_by(user_id=current_user.id, user_confirmed=0)
        .order_by(PredictionHistory.created_on.desc())
        .first()
    )
    if not record:
        return jsonify({'message': 'No predictions yet'}), 200

    return jsonify({
        'prediction_id'  : record.id,
        'predicted_days' : record.predicted_days_remaining,
        'avg_daily'      : record.predicted_daily_usage,
        'confidence'     : round(record.confidence_score * 100),
        'model_used'     : record.model_used,
        'predicted_on'   : record.prediction_date.strftime('%d %b %Y'),
    }), 200


# ═════════════════════════════════════════════════════════════
#  API: POST /api/prediction/confirm
#  User tells us how many days water actually lasted
#  Body: { "prediction_id": int, "actual_days": int }
# ═════════════════════════════════════════════════════════════
@prediction_bp.route('/api/prediction/confirm', methods=['POST'])
@login_required
def confirm_prediction():
    data          = request.get_json(force=True) or {}
    prediction_id = data.get('prediction_id')
    actual_days   = data.get('actual_days')

    if not prediction_id or actual_days is None:
        return jsonify({'error': 'prediction_id and actual_days are required'}), 400

    try:
        actual_days = int(actual_days)
        if actual_days < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'actual_days must be a positive integer'}), 400

    record = PredictionHistory.query.filter_by(
        id      = prediction_id,
        user_id = current_user.id
    ).first()

    if not record:
        return jsonify({'error': 'Prediction not found'}), 404

    predicted     = record.predicted_days_remaining or 0
    error_pct     = abs(predicted - actual_days) / max(actual_days, 1) * 100
    accuracy      = max(0.0, round(100 - error_pct, 1))

    record.actual_days_lasted = actual_days
    record.error_percent      = round(error_pct, 1)
    record.user_confirmed     = 1
    record.confirmed_on       = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'status'       : 'success',
        'message'      : 'Feedback saved. This improves future predictions.',
        'predicted'    : int(predicted),
        'actual'       : actual_days,
        'accuracy_pct' : accuracy,
        'error_days'   : abs(int(predicted) - actual_days),
    }), 200


# ═════════════════════════════════════════════════════════════
#  API: GET /api/prediction/history
#  Returns last 10 predictions with accuracy where confirmed
# ═════════════════════════════════════════════════════════════
@prediction_bp.route('/api/prediction/history', methods=['GET'])
@login_required
def prediction_history():
    records = (
        PredictionHistory.query
        .filter_by(user_id=current_user.id)
        .order_by(PredictionHistory.created_on.desc())
        .limit(10)
        .all()
    )

    result = []
    for r in records:
        entry = {
            'prediction_id'  : r.id,
            'predicted_days' : r.predicted_days_remaining,
            'avg_daily'      : r.predicted_daily_usage,
            'confidence_pct' : round(r.confidence_score * 100),
            'model_used'     : r.model_used,
            'predicted_on'   : r.prediction_date.strftime('%d %b %Y') if r.prediction_date else '—',
            'confirmed'      : bool(r.user_confirmed),
            'actual_days'    : r.actual_days_lasted,
            'accuracy_pct'   : None,
        }
        if r.user_confirmed and r.actual_days_lasted:
            entry['accuracy_pct'] = max(0.0, round(100 - (r.error_percent or 0), 1))
        result.append(entry)

    return jsonify(result), 200