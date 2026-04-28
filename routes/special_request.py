from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, SpecialRequest, User
from datetime import date

special_request_bp = Blueprint('special_request', __name__)

# 50 litres per person per day — same as family size estimate
LITRES_PER_PERSON_PER_DAY = 50


# ── Create special request ───────────────────────────────
@special_request_bp.route('/special-request/create', methods=['POST'])
@login_required
def create():
    data = request.get_json()

    required = ['title', 'reason', 'start_date', 'end_date', 'extra_people']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    extra_people = int(data['extra_people'])
    if extra_people <= 0:
        return jsonify({'error': 'extra_people must be greater than 0'}), 400

    start     = date.fromisoformat(data['start_date'])
    end       = date.fromisoformat(data['end_date'])

    if end < start:
        return jsonify({'error': 'end_date cannot be before start_date'}), 400

    days_span            = (end - start).days + 1
    extra_litres_per_day = extra_people * LITRES_PER_PERSON_PER_DAY
    total_extra_litres   = extra_litres_per_day * days_span

    req = SpecialRequest(
        user_id              = current_user.id,
        title                = data['title'],
        reason               = data.get('reason', ''),
        start_date           = start,
        end_date             = end,
        extra_litres_per_day = extra_litres_per_day,
        total_extra_litres   = total_extra_litres,
        status               = 'Pending'
    )
    db.session.add(req)
    db.session.commit()

    return jsonify({
        'status'              : 'success',
        'message'             : 'Special request submitted successfully',
        'summary'             : {
            'extra_people'        : extra_people,
            'duration_days'       : days_span,
            'extra_litres_per_day': extra_litres_per_day,
            'total_extra_litres'  : total_extra_litres,
            'calculation'         : (
                f'{extra_people} people × '
                f'{LITRES_PER_PERSON_PER_DAY}L × '
                f'{days_span} days = '
                f'{total_extra_litres}L total'
            )
        }
    }), 201


# ── List all special requests ────────────────────────────
@special_request_bp.route('/special-request/list', methods=['GET'])
@login_required
def list_requests():
    requests = SpecialRequest.query.filter_by(
        user_id=current_user.id
    ).order_by(SpecialRequest.created_on.desc()).all()

    return jsonify([{
        'id'                  : r.id,
        'title'               : r.title,
        'reason'              : r.reason,
        'start_date'          : str(r.start_date),
        'end_date'            : str(r.end_date),
        'extra_litres_per_day': r.extra_litres_per_day,
        'total_extra_litres'  : r.total_extra_litres,
        'duration_days'       : (r.end_date - r.start_date).days + 1,
        'status'              : r.status
    } for r in requests]), 200


# ── Cancel a pending request ─────────────────────────────
@special_request_bp.route('/special-request/<int:id>/cancel', methods=['PUT'])
@login_required
def cancel(id):
    req = SpecialRequest.query.filter_by(
        id=id, user_id=current_user.id
    ).first()

    if not req:
        return jsonify({'error': 'Request not found'}), 404
    if req.status != 'Pending':
        return jsonify({'error': 'Only pending requests can be cancelled'}), 400

    req.status = 'Cancelled'
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Request cancelled'}), 200