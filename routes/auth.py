from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data.get('name') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Name, email and password are required'}), 400
    existing = User.query.filter_by(email=data['email']).first()
    if existing:
        return jsonify({'error': 'Email already registered'}), 409
    user = User(
        name        = data['name'],
        email       = data['email'],
        password    = generate_password_hash(data['password']),
        address     = data.get('address', ''),
        family_size = data.get('family_size', 1)
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({
        'status'  : 'success',
        'message' : 'Account created successfully',
        'user_id' : user.id,
        'name'    : user.name
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    login_user(user)
    return jsonify({
        'status'  : 'success',
        'message' : 'Logged in successfully',
        'user_id' : user.id,
        'name'    : user.name
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'status': 'success', 'message': 'Logged out successfully'}), 200

@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    return jsonify({
        'user_id'     : current_user.id,
        'name'        : current_user.name,
        'email'       : current_user.email,
        'address'     : current_user.address,
        'family_size' : current_user.family_size
    }), 200