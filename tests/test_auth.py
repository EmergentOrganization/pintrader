import pytest
from app import app, db, User
import os
from io import BytesIO

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['UPLOAD_FOLDER'] = 'test_uploads'
    
    # Create test uploads directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()
            
    # Clean up test database and uploads
    if os.path.exists('test.db'):
        os.remove('test.db')
    if os.path.exists('test_uploads'):
        import shutil
        shutil.rmtree('test_uploads')

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

def test_file_upload(client):
    """Test file upload functionality"""
    # First create and login a user
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
    
    # Login
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Create a test file
    data = {
        'file': (BytesIO(b'Test file content'), 'test.txt'),
        'description': 'Test file description'
    }
    
    # Try to upload
    response = client.post('/upload', 
                         data=data,
                         content_type='multipart/form-data')
    
    assert response.status_code == 302  # Should redirect after successful upload
    
    # Check if file was saved
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        assert len(user.files) == 1
        assert user.files[0].filename == 'test.txt'
        assert user.files[0].description == 'Test file description'
        
    # Check if file exists in upload directory
    assert os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], 'test.txt'))
