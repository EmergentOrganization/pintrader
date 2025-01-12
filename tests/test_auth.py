import pytest
from app import app, db, User, File
import os
from io import BytesIO
import json

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

def test_file_upload(client):
    """Test file registration functionality"""
    # First create and login a user
    with app.app_context():
        user = User(username='testuser2', email='test2@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
    
    # Login
    client.post('/login', data={
        'username': 'testuser2',
        'password': 'testpass123'
    })
    
    # Test file registration
    test_data = {
        'filename': 'test.txt',
        'multihash': 'QmTest456',
        'description': 'Test file description'
    }
    
    # Try to register the file
    response = client.post('/upload',
                          data=json.dumps(test_data),
                          content_type='application/json')
    
    assert response.status_code == 200
    
    # Verify the file was registered in the database
    with app.app_context():
        file = File.query.filter_by(multihash='QmTest456').first()
        assert file is not None
        assert file.filename == 'test.txt'
        assert file.description == 'Test file description'

def test_file_upload_api():
    """Test the file upload API endpoint"""
    # First create and login a user
    with app.app_context():
        user = User(username='testuser3', email='test3@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
    
    # Login
    client = app.test_client()
    client.post('/login', data={
        'username': 'testuser3',
        'password': 'testpass123'
    })
    
    # Test file registration
    test_data = {
        'filename': 'test.txt',
        'multihash': 'QmTest789',
        'description': 'Test file description'
    }
    
    response = client.post('/upload',
                          data=json.dumps(test_data),
                          content_type='application/json')
    
    assert response.status_code == 200
    
    # Verify the file was registered in the database
    with app.app_context():
        file = File.query.filter_by(multihash='QmTest789').first()
        assert file is not None
        assert file.filename == 'test.txt'
        assert file.description == 'Test file description'
        
        # Test duplicate multihash
        response = client.post('/upload',
                             data=json.dumps(test_data),
                             content_type='application/json')
        assert response.status_code == 400  # Should fail with duplicate multihash

def test_database_schema():
    """Test that the database schema is correct and includes all necessary columns"""
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Get table information
        inspector = db.inspect(db.engine)
        
        # Check File table columns
        file_columns = {column['name'] for column in inspector.get_columns('file')}
        required_columns = {'id', 'filename', 'multihash', 'description', 'upload_date', 'user_id'}
        
        assert required_columns.issubset(file_columns), f"Missing columns in File table. Required: {required_columns}, Found: {file_columns}"
        
        # Create a test user and file
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        
        # Try to create a file record
        file = File(
            filename='test.txt',
            multihash='QmTest123',
            description='Test file',
            user_id=user.id
        )
        db.session.add(file)
        db.session.commit()
        
        # Try to query the file
        saved_file = File.query.filter_by(multihash='QmTest123').first()
        assert saved_file is not None
        assert saved_file.filename == 'test.txt'
        assert saved_file.multihash == 'QmTest123'
