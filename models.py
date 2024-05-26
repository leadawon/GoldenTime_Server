from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Users(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    station = db.relationship('Station', backref='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.id}>'

class Station(db.Model):
    __tablename__ = 'stations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    plugs = db.relationship('Plug', backref='station')

    def __repr__(self):
        return f'<Station {self.id}>'

class Plug(db.Model):
    __tablename__ = 'plugs'

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    device_id = db.Column(db.String(80), nullable=False)
    device_type = db.Column(db.String(80), nullable=False)
    golden_time = db.Column(db.Integer, nullable=False, default=0)
    golden_power = db.Column(db.Float, nullable=False, default=0)
    plug_raws = db.relationship('Plug_Raw', backref='plug')
    storages = db.relationship('Storage', backref='plug')

    def __repr__(self):
        return f'<Plug {self.id}>'

class Plug_Raw(db.Model):
    __tablename__ = 'plug_raws'

    id = db.Column(db.Integer, primary_key=True)
    plug_id = db.Column(db.Integer, db.ForeignKey('plugs.id'), nullable=False)
    power_state = db.Column(db.String(80), nullable=False)
    current_power = db.Column(db.Float, nullable=False)
    total_power_usage = db.Column(db.Float, nullable=False)
    
    current_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    start_date = db.Column(db.DateTime, nullable=False)
    def __repr__(self):
        return f'<Plug_Raw {self.id}>'

class Storage(db.Model):
    __tablename__ = 'storages'

    id = db.Column(db.Integer, primary_key=True)
    plug_id = db.Column(db.Integer, db.ForeignKey('plugs.id'), nullable=False)
    register_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    daily_usage_time = db.Column(db.Integer, nullable=False, default=0)
    daily_power_usage = db.Column(db.Float, nullable=False, default=0)

    def __repr__(self):
        return f'<Storage {self.id}>'