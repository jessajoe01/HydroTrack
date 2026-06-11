from flask_sqlalchemy import SQLAlchemy
from flask_login      import UserMixin
from datetime         import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ═════════════════════════════════════════════════════════════
# USER
# ═════════════════════════════════════════════════════════════
class User(UserMixin, db.Model):

    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password      = db.Column(db.String(200), nullable=False)
    address       = db.Column(db.String(200))
    family_size   = db.Column(db.Integer, default=4)

    # ── GPS — required by auth.py, supplier.html, register.html ──
    lat           = db.Column(db.Float, default=12.9716)
    lng           = db.Column(db.Float, default=77.5946)

    # ── New columns (added safely by migrate.py) ──────────────
    sump_capacity = db.Column(db.Float, default=6000.0)        # litres
    house_type    = db.Column(db.String(50), default='apartment')  # apartment/villa/independent_house
    updated_on    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    registered_on = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────
    tanker_logs        = db.relationship('TankerLog',        backref='user', lazy='dynamic', cascade='all, delete-orphan')
    daily_usage        = db.relationship('DailyUsage',       backref='user', lazy='dynamic', cascade='all, delete-orphan')
    alerts             = db.relationship('Alert',            backref='user', lazy='dynamic', cascade='all, delete-orphan')
    special_requests   = db.relationship('SpecialRequest',   backref='user', lazy='dynamic', cascade='all, delete-orphan')
    vacation_modes     = db.relationship('VacationMode',     backref='user', lazy='dynamic', cascade='all, delete-orphan')
    prediction_history = db.relationship('PredictionHistory',backref='user', lazy='dynamic', cascade='all, delete-orphan')
    user_confirmations = db.relationship('UserConfirmation', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # ── Password helpers ──────────────────────────────────────
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.name}>'


# ═════════════════════════════════════════════════════════════
# TANKER LOG
# ═════════════════════════════════════════════════════════════
class TankerLog(db.Model):

    __tablename__ = 'tanker_logs'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    delivery_date  = db.Column(db.Date,    nullable=False)
    litres         = db.Column(db.Float,   nullable=False)
    cost_per_litre = db.Column(db.Float,   default=0)
    total_cost     = db.Column(db.Float,   default=0)
    supplier_name  = db.Column(db.String(100))
    notes          = db.Column(db.Text)

    # ── Required by supplier_agent.py (update delivery status) ─
    status         = db.Column(db.String(50), default='Pending')

    # ── New: FK link to Supplier table (optional, can be null) ─
    supplier_id    = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)

    logged_on      = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────
    supplier       = db.relationship('Supplier', backref='tanker_logs')

    def __repr__(self):
        return f'<TankerLog {self.user_id} - {self.litres}L>'


# ═════════════════════════════════════════════════════════════
# DAILY USAGE
# ═════════════════════════════════════════════════════════════
class DailyUsage(db.Model):

    __tablename__ = 'daily_usage'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    usage_date  = db.Column(db.Date,    nullable=False)
    litres_used = db.Column(db.Float,   nullable=False)

    # ── New columns ───────────────────────────────────────────
    guests_count = db.Column(db.Integer, default=0)
    notes        = db.Column(db.Text)
    created_on   = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Prevent duplicate entries for same user + date ────────
    __table_args__ = (
        db.UniqueConstraint('user_id', 'usage_date', name='unique_user_usage_date'),
    )

    def __repr__(self):
        return f'<DailyUsage {self.user_id} {self.usage_date}>'


# ═════════════════════════════════════════════════════════════
# ALERT
# ═════════════════════════════════════════════════════════════
class Alert(db.Model):

    __tablename__ = 'alerts'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    alert_type     = db.Column(db.String(50),  nullable=False)
    message        = db.Column(db.Text,        nullable=False)
    days_remaining = db.Column(db.Float)

    # ── is_read kept as Integer (0/1) for compatibility ───────
    # alerts.py and dashboard.py both use is_read=0 and is_read=1
    is_read        = db.Column(db.Integer, default=0)

    # ── New columns ───────────────────────────────────────────
    title            = db.Column(db.String(200))
    severity         = db.Column(db.String(20), default='medium')  # low / medium / high / critical
    confidence_level = db.Column(db.Float, default=0.5)

    created_on     = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Alert {self.alert_type}>'


# ═════════════════════════════════════════════════════════════
# SUPPLIER
# ═════════════════════════════════════════════════════════════
class Supplier(db.Model):

    __tablename__ = 'suppliers'

    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(100), nullable=False)
    contact          = db.Column(db.String(20))
    area             = db.Column(db.String(100))
    price_per_litre  = db.Column(db.Float, nullable=False)
    min_order_litres = db.Column(db.Float, default=1000)

    # ── avg_delivery_days kept for supplier.py compatibility ──
    avg_delivery_days  = db.Column(db.Integer, default=1)

    # ── New: hours-based field for more precise tracking ──────
    avg_delivery_hours = db.Column(db.Integer, default=24)

    # ── New: rating ───────────────────────────────────────────
    rating           = db.Column(db.Float, default=3.0)

    # ── is_available kept as Integer for supplier.py compat ──
    is_available     = db.Column(db.Integer, default=1)

    # ── GPS — required by supplier.html map ──────────────────
    lat              = db.Column(db.Float, default=12.9716)
    lng              = db.Column(db.Float, default=77.5946)

    added_on         = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Supplier {self.name}>'


# ═════════════════════════════════════════════════════════════
# SPECIAL REQUEST
# ═════════════════════════════════════════════════════════════
class SpecialRequest(db.Model):

    __tablename__ = 'special_requests'

    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title                = db.Column(db.String(100), nullable=False)
    reason               = db.Column(db.String(100))
    start_date           = db.Column(db.Date,  nullable=False)
    end_date             = db.Column(db.Date,  nullable=False)

    # ── Both kept: routes use extra_litres_per_day directly ───
    expected_guests      = db.Column(db.Integer, default=0)
    extra_litres_per_day = db.Column(db.Float,   default=0)
    total_extra_litres   = db.Column(db.Float,   default=0)

    status               = db.Column(db.String(20), default='Pending')

    # ── supplier_notified kept for supplier_agent.py compat ───
    supplier_notified    = db.Column(db.Integer, default=0)

    created_on           = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SpecialRequest {self.title}>'


# ═════════════════════════════════════════════════════════════
# SUPPLIER AGENT
# ── MUST stay — entire supplier portal depends on this ───────
# ═════════════════════════════════════════════════════════════
class SupplierAgent(db.Model):

    __tablename__ = 'supplier_agents'

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(100), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    contact      = db.Column(db.String(20))
    area         = db.Column(db.String(100))
    lat          = db.Column(db.Float, default=12.9716)
    lng          = db.Column(db.Float, default=77.5946)
    is_active    = db.Column(db.Boolean, default=True)
    registered_on = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<SupplierAgent {self.company_name}>'


# ═════════════════════════════════════════════════════════════
# SPECIAL REQUEST RESPONSE
# ═════════════════════════════════════════════════════════════
class SpecialRequestResponse(db.Model):

    __tablename__ = 'special_request_responses'

    id                 = db.Column(db.Integer, primary_key=True)
    special_request_id = db.Column(db.Integer, db.ForeignKey('special_requests.id'), nullable=False)
    supplier_agent_id  = db.Column(db.Integer, db.ForeignKey('supplier_agents.id'),  nullable=False)
    response_type      = db.Column(db.String(20), default='Confirmed')  # Confirmed / Partial
    available_litres   = db.Column(db.Float)
    message            = db.Column(db.Text)
    responded_on       = db.Column(db.DateTime, default=datetime.utcnow)

    special_request    = db.relationship('SpecialRequest', backref='responses')
    supplier_agent     = db.relationship('SupplierAgent',  backref='responses')

    def __repr__(self):
        return f'<SpecialRequestResponse {self.response_type}>'


# ═════════════════════════════════════════════════════════════
# VACATION MODE  ← NEW TABLE
# Temporarily reduces daily usage estimate when family is away
# ═════════════════════════════════════════════════════════════
class VacationMode(db.Model):

    __tablename__ = 'vacation_modes'

    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    start_date        = db.Column(db.Date,    nullable=False)
    end_date          = db.Column(db.Date,    nullable=False)

    # 0 = nobody home, 50 = half the family, 100 = full occupancy
    occupancy_percent = db.Column(db.Float,   default=0)

    is_active         = db.Column(db.Boolean, default=True)
    created_on        = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<VacationMode {self.user_id} {self.start_date}→{self.end_date}>'


# ═════════════════════════════════════════════════════════════
# PREDICTION HISTORY  ← NEW TABLE
# Stores every ML prediction so accuracy can be tracked
# and the model can improve over time
# ═════════════════════════════════════════════════════════════
class PredictionHistory(db.Model):

    __tablename__ = 'prediction_history'

    id                       = db.Column(db.Integer, primary_key=True)
    user_id                  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # What the model predicted
    predicted_daily_usage    = db.Column(db.Float,   nullable=False)
    predicted_days_remaining = db.Column(db.Float)
    confidence_score         = db.Column(db.Float,   default=0.5)   # 0.0 – 1.0
    model_used               = db.Column(db.String(50), default='TankerCycleLR')
    tanker_capacity          = db.Column(db.Float)                  # litres in tank at prediction time
    data_points_used         = db.Column(db.Integer, default=0)

    # Filled in when user confirms actual outcome
    actual_daily_usage       = db.Column(db.Float)
    actual_days_lasted       = db.Column(db.Float)
    error_percent            = db.Column(db.Float)
    user_confirmed           = db.Column(db.Integer, default=0)     # 0/1

    prediction_date          = db.Column(db.Date,     nullable=False, default=lambda: __import__('datetime').date.today())
    created_on               = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_on             = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<PredictionHistory {self.user_id} {self.prediction_date}>'


# ═════════════════════════════════════════════════════════════
# USER CONFIRMATION  ← NEW TABLE
# Stores user feedback on predictions (adaptive learning loop)
# ═════════════════════════════════════════════════════════════
class UserConfirmation(db.Model):

    __tablename__ = 'user_confirmations'

    id                       = db.Column(db.Integer, primary_key=True)
    user_id                  = db.Column(db.Integer, db.ForeignKey('users.id'),     nullable=False, index=True)
    alert_id                 = db.Column(db.Integer, db.ForeignKey('alerts.id'),    nullable=True)
    tanker_delivery_id       = db.Column(db.Integer, db.ForeignKey('tanker_logs.id'), nullable=True)

    estimated_days_remaining = db.Column(db.Float)
    actual_days_lasted       = db.Column(db.Float)
    user_note                = db.Column(db.Text)
    used_for_training        = db.Column(db.Boolean, default=False)

    confirmed_on             = db.Column(db.DateTime, default=datetime.utcnow)

    alert  = db.relationship('Alert',     backref='confirmations')
    tanker = db.relationship('TankerLog', backref='confirmations')

    def __repr__(self):
        return f'<UserConfirmation {self.user_id}>'