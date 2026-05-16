from flask import Blueprint, request, jsonify, session
from models import db, SupplierAgent, TankerLog, SpecialRequest, SpecialRequestResponse, User
from datetime import datetime

supplier_agent_bp = Blueprint('supplier_agent', __name__)


# ── Helper: check if supplier agent is logged in ──────
def get_current_agent():
    agent_id = session.get('supplier_agent_id')
    if not agent_id:
        return None
    return SupplierAgent.query.get(agent_id)


# ── Register ──────────────────────────────────────────
@supplier_agent_bp.route('/supplier-agent/register', methods=['POST'])
def agent_register():
    data = request.get_json()

    if not data.get('name') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Name, email and password are required'}), 400

    if not data.get('company_name'):
        return jsonify({'error': 'Company name is required'}), 400

    existing = SupplierAgent.query.filter_by(email=data['email']).first()
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    agent = SupplierAgent(
        name         = data['name'],
        email        = data['email'],
        company_name = data['company_name'],
        contact      = data.get('contact', ''),
        area         = data.get('area', ''),
        lat          = data.get('lat', 12.9716),
        lng          = data.get('lng', 77.5946)
    )
    agent.set_password(data['password'])
    db.session.add(agent)
    db.session.commit()

    return jsonify({
        'status' : 'success',
        'message': 'Supplier agent account created',
        'agent'  : {
            'id'          : agent.id,
            'name'        : agent.name,
            'company_name': agent.company_name
        }
    }), 201


# ── Login ─────────────────────────────────────────────
@supplier_agent_bp.route('/supplier-agent/login', methods=['POST'])
def agent_login():
    data = request.get_json()

    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    agent = SupplierAgent.query.filter_by(email=data['email']).first()

    if not agent or not agent.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    session['supplier_agent_id'] = agent.id
    session.permanent = True

    return jsonify({
        'status' : 'success',
        'message': 'Logged in successfully',
        'agent'  : {
            'id'          : agent.id,
            'name'        : agent.name,
            'company_name': agent.company_name,
            'area'        : agent.area
        }
    }), 200


# ── Logout ────────────────────────────────────────────
@supplier_agent_bp.route('/supplier-agent/logout', methods=['POST'])
def agent_logout():
    session.pop('supplier_agent_id', None)
    return jsonify({'status': 'success', 'message': 'Logged out'}), 200


# ── Get current agent info ────────────────────────────
@supplier_agent_bp.route('/supplier-agent/me', methods=['GET'])
def agent_me():
    agent = get_current_agent()
    if not agent:
        return jsonify({'error': 'Not logged in'}), 401

    return jsonify({
        'id'          : agent.id,
        'name'        : agent.name,
        'email'       : agent.email,
        'company_name': agent.company_name,
        'contact'     : agent.contact,
        'area'        : agent.area,
        'lat'         : agent.lat,
        'lng'         : agent.lng
    }), 200


# ── Get all users who used this supplier ──────────────
@supplier_agent_bp.route('/supplier-agent/users', methods=['GET'])
def agent_users():
    agent = get_current_agent()
    if not agent:
        return jsonify({'error': 'Not logged in'}), 401

    logs = TankerLog.query.filter(
        db.func.lower(TankerLog.supplier_name) == agent.company_name.lower()
    ).all()

    user_ids = list(set(log.user_id for log in logs))
    users    = User.query.filter(User.id.in_(user_ids)).all()

    result = []
    for user in users:
        user_logs = [l for l in logs if l.user_id == user.id]
        result.append({
            'id'            : user.id,
            'name'          : user.name,
            'email'         : user.email,
            'address'       : user.address,
            'family_size'   : user.family_size,
            'total_orders'  : len(user_logs),
            'last_delivery' : str(max(l.delivery_date for l in user_logs))
        })

    return jsonify(result), 200


# ── Get delivery orders ───────────────────────────────
@supplier_agent_bp.route('/supplier-agent/deliveries', methods=['GET'])
def agent_deliveries():
    agent = get_current_agent()
    if not agent:
        return jsonify({'error': 'Not logged in'}), 401

    logs = TankerLog.query.filter(
        db.func.lower(TankerLog.supplier_name) == agent.company_name.lower()
    ).order_by(TankerLog.delivery_date.desc()).all()

    result = []
    for log in logs:
        user = User.query.get(log.user_id)
        result.append({
            'id'            : log.id,
            'user_name'     : user.name if user else '—',
            'user_address'  : user.address if user else '—',
            'user_lat'      : user.lat if user else 12.9716,   # ← ADD THIS
            'user_lng'      : user.lng if user else 77.5946, 
            'delivery_date' : str(log.delivery_date),
            'litres'        : log.litres,
            'cost_per_litre': log.cost_per_litre,
            'total_cost'    : log.total_cost,
            'notes'         : log.notes,
            'status'        : log.status or 'Pending'
        })

    return jsonify(result), 200


# ── Update delivery status ────────────────────────────
@supplier_agent_bp.route('/supplier-agent/deliveries/<int:id>/status', methods=['PUT'])
def update_delivery_status(id):
    agent = get_current_agent()
    if not agent:
        return jsonify({'error': 'Not logged in'}), 401

    data   = request.get_json()
    status = data.get('status')

    if status not in ['Pending', 'Confirmed', 'Out for Delivery', 'Delivered']:
        return jsonify({'error': 'Invalid status'}), 400

    log = TankerLog.query.filter_by(id=id).first()
    if not log:
        return jsonify({'error': 'Delivery not found'}), 404

    log.status = status
    db.session.commit()

    return jsonify({'status': 'success', 'message': f'Status updated to {status}'}), 200


# ── Get special requests ──────────────────────────────
@supplier_agent_bp.route('/supplier-agent/special-requests', methods=['GET'])
def agent_special_requests():
    agent = get_current_agent()
    if not agent:
        return jsonify({'error': 'Not logged in'}), 401

    requests = SpecialRequest.query.order_by(
        SpecialRequest.created_on.desc()
    ).all()

    result = []
    for req in requests:
        user = User.query.get(req.user_id)
        result.append({
            'id'                  : req.id,
            'user_name'           : user.name if user else '—',
            'user_address'        : user.address if user else '—',
            'user_lat'      : user.lat if user else 12.9716,   # ← ADD THIS
            'user_lng'      : user.lng if user else 77.5946,
            'title'               : req.title,
            'reason'              : req.reason,
            'start_date'          : str(req.start_date),
            'end_date'            : str(req.end_date),
            'extra_litres_per_day': req.extra_litres_per_day,
            'total_extra_litres'  : req.total_extra_litres,
            'status'              : req.status
        })

    return jsonify(result), 200


# ── Respond to special request ────────────────────────
@supplier_agent_bp.route('/supplier-agent/special-requests/<int:id>/respond', methods=['POST'])
def respond_special_request(id):
    agent = get_current_agent()
    if not agent:
        return jsonify({'error': 'Not logged in'}), 401

    data          = request.get_json()
    response_type = data.get('response_type', 'Confirmed')
    available     = data.get('available_litres')
    message       = data.get('message', '')

    req = SpecialRequest.query.get(id)
    if not req:
        return jsonify({'error': 'Request not found'}), 404

    response = SpecialRequestResponse(
        special_request_id = id,
        supplier_agent_id  = agent.id,
        response_type      = response_type,
        available_litres   = available,
        message            = message
    )
    db.session.add(response)

    req.status = response_type
    db.session.commit()

    return jsonify({
        'status' : 'success',
        'message': f'Response recorded as {response_type}'
    }), 200