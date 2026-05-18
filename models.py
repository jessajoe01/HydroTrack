from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), nullable=False)
    email           = db.Column(db.String(100), unique=True, nullable=False)
    password        = db.Column(db.String(200), nullable=False)
    address         = db.Column(db.String(200))
    family_size     = db.Column(db.Integer, default=1)
    lat = db.Column(db.Float, default=12.9716)
    lng = db.Column(db.Float, default=77.5946)
    registered_on   = db.Column(db.DateTime, default=datetime.utcnow)


class TankerLog(db.Model):
    __tablename__ = 'tanker_logs'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'))
    delivery_date   = db.Column(db.Date, nullable=False)
    litres          = db.Column(db.Float, nullable=False)
    cost_per_litre  = db.Column(db.Float)
    total_cost      = db.Column(db.Float)
    supplier_name   = db.Column(db.String(100))
    notes           = db.Column(db.Text)
    status = db.Column(db.String(50), default='Pending')
    logged_on       = db.Column(db.DateTime, default=datetime.utcnow)


class DailyUsage(db.Model):
    __tablename__ = 'daily_usage'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'))
    usage_date      = db.Column(db.Date, nullable=False)
    litres_used     = db.Column(db.Float)


class Alert(db.Model):
    __tablename__ = 'alerts'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'))
    alert_type      = db.Column(db.String(20))
    message         = db.Column(db.Text)
    days_remaining  = db.Column(db.Float)
    is_read         = db.Column(db.Integer, default=0)
    created_on      = db.Column(db.DateTime, default=datetime.utcnow)


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(100), nullable=False)
    contact             = db.Column(db.String(20))
    area                = db.Column(db.String(100))
    price_per_litre     = db.Column(db.Float)
    min_order_litres    = db.Column(db.Float)
    avg_delivery_days   = db.Column(db.Integer)
    is_available        = db.Column(db.Integer, default=1)
    lat= db.Column(db.Float, default=12.9716)  # ← is this there?
    lng= db.Column(db.Float, default=77.5946)


class SpecialRequest(db.Model):
    __tablename__ = 'special_requests'
    id                      = db.Column(db.Integer, primary_key=True)
    user_id                 = db.Column(db.Integer, db.ForeignKey('users.id'))
    title                   = db.Column(db.String(100), nullable=False)
    reason                  = db.Column(db.String(100))
    start_date              = db.Column(db.Date, nullable=False)
    end_date                = db.Column(db.Date, nullable=False)
    extra_litres_per_day    = db.Column(db.Float, nullable=False)
    total_extra_litres      = db.Column(db.Float)
    status                  = db.Column(db.String(20), default='Pending')
    supplier_notified       = db.Column(db.Integer, default=0)
    created_on              = db.Column(db.DateTime, default=datetime.utcnow)

    # =========================================================
# SUPPLIER AGENT
# Separate login for supplier agents
# =========================================================
class SupplierAgent(db.Model):

    __tablename__ = 'supplier_agents'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(db.String(200), nullable=False)

    company_name = db.Column(db.String(100), nullable=False)

    contact = db.Column(db.String(20))

    area = db.Column(db.String(100))

    # Latitude and longitude for route map
    lat = db.Column(db.Float, default=12.9716)
    lng = db.Column(db.Float, default=77.5946)

    is_active = db.Column(db.Boolean, default=True)

    registered_on = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<SupplierAgent {self.company_name}>'


# =========================================================
# SPECIAL REQUEST RESPONSE
# Supplier agent response to special requests
# =========================================================
class SpecialRequestResponse(db.Model):

    __tablename__ = 'special_request_responses'

    id = db.Column(db.Integer, primary_key=True)

    special_request_id = db.Column(
        db.Integer,
        db.ForeignKey('special_requests.id'),
        nullable=False
    )

    supplier_agent_id = db.Column(
        db.Integer,
        db.ForeignKey('supplier_agents.id'),
        nullable=False
    )

    response_type = db.Column(
        db.String(20),
        default='Confirmed'
    )  # Confirmed / Partial

    available_litres = db.Column(db.Float)

    message = db.Column(db.Text)

    responded_on = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # Relationships
    special_request = db.relationship(
        'SpecialRequest',
        backref='responses'
    )

    supplier_agent = db.relationship(
        'SupplierAgent',
        backref='responses'
    )

    def __repr__(self):
        return f'<SpecialRequestResponse {self.response_type}>'