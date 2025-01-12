import pytest
from app import app, db, User
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()
            
    # Clean up test database
    if os.path.exists('test.db'):
        os.remove('test.db')

def test_index_page(client):
    """Test if the index page loads correctly"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome to PinTrader' in response.data

def test_registration(client):
    """Test user registration"""
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data  # Should redirect to login page
    
    # Check if user was created
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        assert user is not None
        assert user.email == 'test@example.com'

def test_login_success(client):
    """Test successful login"""
    # First create a user
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
    
    # Try to login
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Profile' in response.data

def test_login_failure(client):
    """Test login with wrong credentials"""
    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data

def test_profile_access(client):
    """Test profile page access"""
    # Test unauthorized access
    response = client.get('/profile', follow_redirects=True)
    assert b'Please log in to access this page' in response.data
    
    # Create and login user
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
    
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Test authorized access
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Profile' in response.data
