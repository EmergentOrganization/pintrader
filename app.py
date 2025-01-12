from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    files = db.relationship('File', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    multihash = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect(url_for('profile'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if not request.is_json:
            return 'Request must be JSON', 400
            
        data = request.get_json()
        
        if not data.get('multihash'):
            return 'Multihash is required', 400
            
        if not data.get('filename'):
            return 'Filename is required', 400
            
        # Check if multihash already exists
        existing_file = File.query.filter_by(multihash=data['multihash']).first()
        if existing_file:
            return 'File with this hash already exists', 400
            
        # Create file record in database
        new_file = File(
            filename=data['filename'],
            multihash=data['multihash'],
            description=data.get('description', ''),
            user_id=current_user.id
        )
        
        db.session.add(new_file)
        db.session.commit()
        
        return jsonify({'message': 'File hash registered successfully'})
            
    return render_template('upload.html')

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    users = []
    if query:
        # Search for users whose username contains the query (case-insensitive)
        users = User.query.filter(User.username.ilike(f'%{query}%')).all()
    return render_template('search.html', users=users, query=query)

@app.route('/profile/<username>')
@login_required
def public_profile(username):
    profile_user = User.query.filter_by(username=username).first_or_404()
    return render_template('public_profile.html', profile_user=profile_user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
