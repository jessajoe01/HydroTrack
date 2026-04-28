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