from flask import Flask, render_template, redirect, url_for, request, flash,session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Admin
from controllers.admin_routes import admin_bp
from controllers.user_routes import user_bp
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
bcrypt=Bcrypt(app)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home'  

@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')
    if user_type == 'admin':
        return Admin.query.get(int(user_id))
    elif user_type == 'user':
        return User.query.get(int(user_id))
    return None


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # admin = Admin.query.filter_by(email=email).first()
        # if admin and admin.password == password:
        #     login_user(admin)
        #     session['user_type'] = 'admin' 
        #     return redirect(url_for('admin_bp.admin_dashboard'))
        
        
        # user = User.query.filter_by(email=email).first()

        # if user and user.password == password:
        #     login_user(user)
        #     session['user_type'] = 'user'
        #     return redirect(url_for('user_bp.user_dashboard'))
        
        role=request.form.get('role')
        
        if role=='admin':
            admin=Admin.query.filter_by(email=email).first()
            if admin and admin.password==password:
                login_user(admin)
                session['user_type']='admin'
                return redirect(url_for('admin_bp.admin_dashboard'))
        elif role=='user':
             user=User.query.filter_by(email=email).first()
             if user and bcrypt.check_password_hash(user.password,password):
                login_user(user)
                session['user_type']='user'
                return redirect(url_for('user_bp.user_dashboard'))
        
        flash('Invalid email or password', 'danger')
        return redirect(url_for('home'))

    return render_template('login.html',error=None)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)

with app.app_context():
    db.create_all()  


    if not Admin.query.filter_by(email='admin@example.com').first():
        admin = Admin(
            username='admin',
            email='admin@example.com',
            password='admin123',  
        )
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
