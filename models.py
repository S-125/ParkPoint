from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, record):
    if isinstance(dbapi_conn, SQLite3Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.close()


db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    
    reservations = db.relationship('ReserveParkingSpot', backref='user', lazy=True , cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<User {self.email}>'
    
class Admin(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f'<Admin {self.email}>'

class Parking_lot(db.Model):
    __tablename__ = 'parking_lots'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=True)
    prime_location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    max_spots = db.Column(db.Integer, nullable=False)
    occupied_spots = db.Column(db.Integer, nullable=False)
    spots = db.relationship('Parking_spot', backref='parking_lot', lazy=True,  cascade='all, delete-orphan',
        passive_deletes=True)



class Parking_spot(db.Model):
    __tablename__ = 'parking_spots'
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id',ondelete='CASCADE'), nullable=True)
    status = db.Column(db.String(1), default="A") 
    reservations = db.relationship(
        'ReserveParkingSpot',
        backref='parking_spot',
        lazy=True,
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class ReserveParkingSpot(db.Model):
    __tablename__ = 'reserve_parking_spots'
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id',ondelete='CASCADE'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id',ondelete='CASCADE'), nullable=True)
    vehicle_number = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    parking_timestamp = db.Column(db.DateTime, nullable=False)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost_per_unit_time = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(1), default="A")  
