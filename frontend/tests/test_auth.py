import pytest
from app import db, User, File
import os
from io import BytesIO
import json
from unittest.mock import patch
from sqlalchemy.exc import DataError

def test_index_page(client):
    """Test if the index page loads correctly"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome to PinTrader' in response.data

def test_registration(client, app):
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

def test_login_success(client, app):
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

def test_profile_access(client, app):
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

def test_file_upload(client, app):
    """Test file upload functionality"""
    user_id = None
    # First create and login a user
    with app.app_context():
        user = User(username='testuser2', email='test2@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    # Login
    client.post('/login', data={
        'username': 'testuser2',
        'password': 'testpass123'
    })
    
    # Create a test file
    data = {'file': (BytesIO(b'test file content'), 'test.txt')}
    
    # Mock IPFS client
    mock_ipfs_result = {'Hash': 'QmTestHash123'}
    with patch('app.get_ipfs_client') as mock_client:
        # Configure the mock
        mock_instance = mock_client.return_value
        mock_instance.add.return_value = mock_ipfs_result
        
        # Test file upload
        response = client.post('/upload_file', 
            data=data,
            follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify file was saved in database
        with app.app_context():
            file = File.query.filter_by(filename='test.txt').first()
            assert file is not None
            assert file.user_id == user_id
            assert file.multihash == 'QmTestHash123'

def test_password_hash_length(app):
    """Test that long passwords can be stored correctly"""
    with app.app_context():
        # Create a user with a long password
        user = User(username='testuser_long', email='test_long@example.com')
        # Use a long password (50 characters)
        long_password = 'x' * 50
        user.set_password(long_password)
        
        # Verify the hash is created and can be stored
        db.session.add(user)
        db.session.commit()
        
        # Retrieve the user and verify the password still works
        saved_user = User.query.filter_by(username='testuser_long').first()
        assert saved_user is not None
        assert saved_user.check_password(long_password)
        assert len(saved_user.password_hash) > 128  # Verify hash is longer than the original field size
