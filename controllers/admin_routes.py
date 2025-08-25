from flask import Blueprint, render_template,request,flash,redirect,url_for
from flask_login import login_required, current_user
from models import db, Parking_lot, ReserveParkingSpot,Parking_spot,User,Admin
from sqlalchemy.orm import joinedload
from sqlalchemy import func

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

@admin_bp.route('/profile',methods=['GET', 'POST'])
@login_required
def admin_profile():
    admin = Admin.query.get(current_user.id)
    if request.method == 'POST':
        admin.username = request.form.get('username')
        admin.email = request.form.get('email')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('admin_bp.admin_profile'))
    return render_template('admin/profile.html', admin=admin)

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    lots = Parking_lot.query.all()
    return render_template('admin/dashboard.html', lots=lots)

@admin_bp.route('/add_lot', methods=['GET', 'POST'])
def add_lot():
    if request.method == 'POST':
        name = request.form.get('name')
        prime_location = request.form.get('prime_location')
        price = request.form.get('price')
        address = request.form.get('address')
        pincode = request.form.get('pincode')
        max_spots = request.form.get('max_spots')

        new_lot = Parking_lot(
            name=name,
            prime_location=prime_location,
            price=price,
            address=address,
            pincode=pincode,
            max_spots=max_spots,
            occupied_spots=0,  
        )
        db.session.add(new_lot)
        db.session.commit()
        
        new_spots=[Parking_spot(lot_id=new_lot.id, status="A") for _ in range (new_lot.max_spots)]
        
        db.session.add_all(new_spots)
        db.session.commit();
    
        return redirect(url_for('admin_bp.admin_dashboard'))
    else:
        return render_template('admin/add_lot.html')

@admin_bp.route('/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    lot = Parking_lot.query.get(lot_id)

    if request.method == 'POST':
        lot.name = request.form.get('name')
        lot.prime_location = request.form.get('prime_location')
        lot.price = request.form.get('price')
        lot.address = request.form.get('address')
        lot.pincode = request.form.get('pincode')
        
        new_max_spots = int(request.form.get('max_spots'))  # Convert to integer
        old_max_spots = lot.max_spots

        lot.max_spots = new_max_spots

        if new_max_spots > old_max_spots:
            # Add new Parking_spots
            new_spots = [Parking_spot(lot_id=lot.id, status="A") for _ in range(new_max_spots - old_max_spots)]
            db.session.add_all(new_spots)
        
        elif new_max_spots < old_max_spots:
            # Remove excess Parking_spots
            spots_to_remove = Parking_spot.query.filter(Parking_spot.lot_id == lot.id).limit(old_max_spots - new_max_spots).all()
            for spot in spots_to_remove:
                db.session.delete(spot)

        db.session.commit()

        
        return redirect(url_for('admin_bp.admin_dashboard'))

    return render_template('admin/edit_lot.html', lot=lot)


@admin_bp.route('/delete_lot/<int:lot_id>', methods=['GET','POST']) 
def delete_lot(lot_id):
    lot = Parking_lot.query.get(lot_id)
    for spot in lot.spots:
        if spot.status == "O":
            return redirect(url_for('admin_bp.admin_dashboard'))
    
    db.session.delete(lot)
    db.session.commit()
    return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/details/<int:spot_id>')
def spot_details(spot_id):
    spot=Parking_spot.query.get(spot_id)
    return render_template('admin/spot_details.html', spot=spot)

@admin_bp.route('/delete_spot/<int:spot_id>', methods=['GET','POST'])
def delete_spot(spot_id):
    spot = Parking_spot.query.get(spot_id)
    if spot.status == "O":
        return redirect(url_for('admin_bp.admin_dashboard'))
   
    db.session.delete(spot)
    db.session.commit()
    lot = Parking_lot.query.get(spot.lot_id)
    lot.max_spots -= 1
    db.session.commit()
    return redirect(url_for('admin_bp.admin_dashboard'))

@admin_bp.route('/user_details')
def user_details():
    users = User.query.all()
    return render_template('admin/user_details.html', users=users)

@admin_bp.route('/occupied_details/<int:spot_id>', methods=['GET','POST'])
def occupied_details(spot_id):
    spot = Parking_spot.query.get(spot_id)
    if spot.status == "A":
        return redirect(url_for('admin_bp.spot_details', spot_id=spot_id))
    reservation = ReserveParkingSpot.query.filter_by(spot_id=spot_id).first()
    return render_template('admin/occupied_details.html', reservation=reservation)

@admin_bp.route('/summary', methods=['GET','POST'])
def summary():
    reservations = ReserveParkingSpot.query.all()

    total_revenue = round(sum(
        reservation.total_cost for reservation in reservations if reservation.total_cost is not None
    ),2)

    
    revenue_per_lot = db.session.query(
        Parking_lot.name,
        func.sum(ReserveParkingSpot.total_cost).label('lot_revenue')
    ).join(Parking_spot, Parking_spot.lot_id == Parking_lot.id
    ).join(ReserveParkingSpot, ReserveParkingSpot.spot_id == Parking_spot.id
    ).group_by(Parking_lot.id).all()

    
    labels = [lot_name for lot_name, _ in revenue_per_lot]
    values = [lot_revenue for _, lot_revenue in revenue_per_lot]

    
    lot_status = db.session.query(
        Parking_lot.name,
        Parking_lot.max_spots,
        Parking_lot.occupied_spots
    ).all()

    status_labels = [lot.name for lot in lot_status]
    occupied = [lot.occupied_spots for lot in lot_status]
    available = [lot.max_spots - lot.occupied_spots for lot in lot_status]

    return render_template(
        'admin/summary.html',
        reservations=reservations,
        total_revenue=total_revenue,
        revenue_per_lot=revenue_per_lot,
        labels=labels,
        values=values,
        status_labels=status_labels,
        occupied=occupied,
        available=available
    )


@admin_bp.route("/search", methods=["GET","POST"])
def search_parking():
    search_by = request.args.get("search_by", "")
    query = request.args.get("query", "")

    parking_lots = []

    if search_by == "location":
        parking_lots = Parking_lot.query.filter(
            Parking_lot.prime_location.ilike(f"%{query}%")
        ).options(joinedload(Parking_lot.spots)).all()
    elif search_by == "user_id":
        subq = db.session.query(ReserveParkingSpot.spot_id).filter_by(user_id=query).subquery()
        spot_ids = [sid[0] for sid in db.session.query(subq).all()]
        parking_lots = Parking_lot.query.join(Parking_lot.spots).filter(
            Parking_spot.id.in_(spot_ids)
        ).options(joinedload(Parking_lot.spots)).all()
    elif search_by == "spot_id":
        parking_lots = Parking_lot.query.join(Parking_lot.spots).filter(
            Parking_spot.id == query
        ).options(joinedload(Parking_lot.spots)).all()

    return render_template("admin/search.html", parking_lots=parking_lots)


@admin_bp.route('/delete_all')
def delete_all():
    Parking_lot.query.delete()
    db.session.commit()
    return redirect(url_for('admin_bp.admin_dashboard'))


@admin_bp.route('/delete_user/<int:id>')
def delete_user(id):
    user=User.query.get(id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_bp.user_details'))
    