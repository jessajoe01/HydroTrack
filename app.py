import os
from flask import Flask, jsonify, render_template
from flask_login import LoginManager, login_required
from flask_cors import CORS
from flask_mail import Mail
from config import Config
from models import db, User

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    static_url_path='/static'
)

app.config.from_object(Config)

# ── Extensions ─────────────────────────────────────────
db.init_app(app)
CORS(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Register blueprints ────────────────────────────────
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.tanker import tanker_bp
from routes.alerts import alerts_bp
from routes.cost import cost_bp
from routes.supplier import supplier_bp
from routes.special_request import special_request_bp
from routes.supplier_agent import supplier_agent_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(tanker_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(cost_bp)
app.register_blueprint(supplier_bp)
app.register_blueprint(special_request_bp)
app.register_blueprint(supplier_agent_bp)
from flask_login import current_user

@app.route('/me')
def get_current_user():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not logged in'}), 401
    return jsonify({
        'user_id'    : current_user.id,
        'name'       : current_user.name,
        'email'      : current_user.email,
        'address'    : current_user.address,
        'family_size': current_user.family_size,
        'lat'        : current_user.lat,
        'lng'        : current_user.lng
    }), 200

# ── Page routes (HTML) ─────────────────────────────────
@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard_page():
    return render_template('dashboard.html')


@app.route('/tanker-log')
@login_required
def tanker_log_page():
    return render_template('tanker_log.html')


@app.route('/alerts')
@login_required
def alerts_page():
    return render_template('alerts.html')


@app.route('/cost')
@login_required
def cost_page():
    return render_template('cost.html')


@app.route('/supplier')
@login_required
def supplier_page():
    return render_template('supplier.html')


@app.route('/special-request')
@login_required
def special_request_page():
    return render_template('special_request.html')

# ── Supplier Agent Portal ──────────────────────────────
@app.route('/supplier-portal')
def supplier_portal_page():
    return render_template('login.html')

@app.route('/supplier-portal/dashboard')
def supplier_dashboard_page():
    return render_template('supplier_dashboard.html')


# ── Debug/Test route (optional) ────────────────────────
@app.route('/ping')
def ping():
    return jsonify({'status': 'ok'})


# ── Run app ────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('✅ Database tables created successfully')

    app.run(debug=True)