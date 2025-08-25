from flask import Blueprint, render_template,request,redirect,url_for,flash
from models import db, User, Parking_lot,Parking_spot,ReserveParkingSpot
from flask_login import login_required, current_user
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
import re
from flask_bcrypt import Bcrypt
user_bp = Blueprint('user_bp', __name__, url_prefix='/user')
bcrypt=Bcrypt()

@user_bp.route('/register',methods=['GET','POST'])
def register():
     if request.method == 'POST':
        email = request.form.get('email')
        password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        full_name = request.form.get('fullname')
        address = request.form.get('address')
        pincode = request.form.get('pincode')

        
        if not all([email, password, full_name, address, pincode]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('user_bp.register'))
        
        if not len(password)>=8:
            flash('Password length should be atleast 8')
            return redirect(url_for('user_bp.register'))
        
        if not re.search(r"[A-Z]",password):
                flash('Password should contain a uppercase letter')
                return redirect(url_for('user_bp.register'))
        if not re.search(r"[a-z]",password):
                flash('Password should contain a lowercase letter')
                return redirect(url_for('user_bp.register'))
        if not re.search(r"\W",password):
                flash('Password should contain a special character')
                return redirect(url_for('user_bp.register'))
        if not re.search(r"\d",password):
                flash('Password should contain a digit')
                return redirect(url_for('user_bp.register'))
            
        if  not len(pincode)==6:
                 flash('Pincode should contain 6 digits')
                 return redirect(url_for('user_bp.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('user_bp.register'))


        new_user = User(
            email=email,
            password=password, 
            full_name=full_name,
            address=address,
            pincode=pincode,
        )
        db.session.add(new_user)
        db.session.commit()

       
        return redirect('/')
     return render_template('user/register.html')

@user_bp.route('/dashboard',methods=['GET','POST'])
@login_required
def user_dashboard():
    ParkingLot = Parking_lot.query.filter_by(address=current_user.address).all()
    location=current_user.address
    history = ReserveParkingSpot.query.filter_by(user_id=current_user.id).all()
    if not history:
        history=""
    if request.method == 'POST':
        search = request.form.get('search') 
        location =search
        if search:
            ParkingLot = Parking_lot.query.filter(Parking_lot.prime_location.ilike(f"%{search}%")).all()
            if not ParkingLot:
                ParkingLot = Parking_lot.query.filter_by(address=search).all()
        else:
            ParkingLot=""
           
    return render_template('user/dashboard.html', user=current_user, parking_lots=ParkingLot,location=location,history=history)


@user_bp.route('/reserve/<int:lot_id>', methods=['GET','POST'])
@login_required
def reserve_parking(lot_id):
    parking_lot = Parking_lot.query.get_or_404(lot_id)
    spots = Parking_spot.query.filter_by(lot_id=lot_id,status="A").first()
    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number')
        reservation = ReserveParkingSpot(
            spot_id=spots.id,
            user_id=current_user.id,
            vehicle_number=vehicle_number,
            location=parking_lot.prime_location,
            parking_cost_per_unit_time=parking_lot.price,
            parking_timestamp=datetime.now(ZoneInfo("Asia/Kolkata"))
        )
        db.session.add(reservation)
        db.session.commit()
        spots.status="O"
        db.session.commit()
        parking_lot.occupied_spots=parking_lot.occupied_spots+1
        db.session.commit()
        return redirect(url_for('user_bp.user_dashboard'))
        
    return render_template('user/reserve.html', user=current_user, parking_lot=parking_lot, spot=spots)
    
   
@user_bp.route('/release/<int:reservation_id>',methods=['GET','POST'])
def release_parking(reservation_id):
    reservation = ReserveParkingSpot.query.get_or_404(reservation_id)
    parking_spot = Parking_spot.query.get(reservation.spot_id)
    parking_lot = Parking_lot.query.get(parking_spot.lot_id)
    leavetime = datetime.now(ZoneInfo("Asia/Kolkata"))
    ist= ZoneInfo("Asia/Kolkata")
    if reservation.parking_timestamp.tzinfo is None:
        reservation.parking_timestamp = reservation.parking_timestamp.replace(tzinfo=ist)

    duration = leavetime - reservation.parking_timestamp
    duration_in_hours = duration.total_seconds() / 3600
    total_cost = duration_in_hours * reservation.parking_cost_per_unit_time
    total_cost = round(total_cost, 2)
    if request.method == 'POST':
        reservation.leaving_timestamp = leavetime
        parking_spot.status="A"
        parking_lot.occupied_spots=parking_lot.occupied_spots-1
        reservation.status="I"
        reservation.total_cost = total_cost
        db.session.commit()
        
        return redirect(url_for('user_bp.user_dashboard'))
    
    return render_template('user/release.html', user=current_user, reservation=reservation,total_cost=total_cost, leavetime=leavetime)




def get_user_lot_durations(user_id):
    ist = ZoneInfo("Asia/Kolkata")
    reservations = (
        db.session.query(ReserveParkingSpot)
        .join(Parking_spot)
        .join(Parking_lot)
        .filter(ReserveParkingSpot.user_id == user_id)
        .filter(ReserveParkingSpot.leaving_timestamp.isnot(None))
        .all()
    )

    lot_hours = defaultdict(float)

    for r in reservations:
        start = r.parking_timestamp
        end = r.leaving_timestamp

        if start and end:
            # Ensure timezone awareness
            if start.tzinfo is None:
                start = start.replace(tzinfo=ist)
            if end.tzinfo is None:
                end = end.replace(tzinfo=ist)

            if end > start:
                hours = (end - start).total_seconds() / 3600
                lot_name = r.parking_spot.parking_lot.name
                lot_hours[lot_name] += hours

    return [{'lot': name, 'hours': round(hours, 2)} for name, hours in lot_hours.items()]


@user_bp.route('/summary', methods=['GET'])
@login_required
def summary():
    user_id = current_user.id
    lot_data = get_user_lot_durations(user_id)
    return render_template('user/summary.html',lot_data=lot_data)

@user_bp.route('/profile',methods=['GET', 'POST'])
@login_required
def user_profile():
    user = User.query.get(current_user.id)
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_bp.user_profile'))
    return render_template('user/profile.html', user=user)

@user_bp.route('/reset',methods=['GET','POST'])
def reset():
    if request.method=='POST':
        oldE=request.form.get('oldE')
        newE=request.form.get('newE')
        oldP=request.form.get('oldP')
        newP=request.form.get('newP')
        
        user=User.query.filter_by(email=oldE).first()
        if(oldP==user.password):
            user.email=newE
            user.password=newP
            db.session.commit()
            return redirect('/')
        
        
    return render_template('user/reset.html')