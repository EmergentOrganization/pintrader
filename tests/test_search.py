import pytest
from app import app, db, User
from flask_login import current_user
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create test users
            users = [
                User(username='testuser1', email='test1@test.com', password_hash=generate_password_hash('password')),
                User(username='testuser2', email='test2@test.com', password_hash=generate_password_hash('password')),
                User(username='otheruser', email='other@test.com', password_hash=generate_password_hash('password'))
            ]
            for user in users:
                db.session.add(user)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def login(client, username):
    return client.post('/login', data={
        'username': username,
        'password': 'password'
    }, follow_redirects=True)

def test_search_requires_login(client):
    """Test that search page requires login"""
    response = client.get('/search')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

def test_search_accessible_when_logged_in(client):
    """Test that search page is accessible when logged in"""
    login(client, 'testuser1')
    response = client.get('/search')
    assert response.status_code == 200
    assert b'Search Users' in response.data

def test_search_results(client):
    """Test that search returns correct results"""
    login(client, 'testuser1')
    
    # Search for 'testuser'
    response = client.get('/search?q=testuser')
    assert response.status_code == 200
    assert b'testuser1' in response.data
    assert b'testuser2' in response.data
    assert b'otheruser' not in response.data
    
    # Search for specific user
    response = client.get('/search?q=testuser1')
    assert response.status_code == 200
    assert b'testuser1' in response.data
    assert b'testuser2' not in response.data
    
    # Search with no results
    response = client.get('/search?q=nonexistent')
    assert response.status_code == 200
    assert b'No users found' in response.data

def test_public_profile_requires_login(client):
    """Test that public profile page requires login"""
    response = client.get('/profile/testuser1')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

def test_public_profile_accessible_when_logged_in(client):
    """Test that public profile page is accessible when logged in"""
    login(client, 'testuser1')
    response = client.get('/profile/testuser2')
    assert response.status_code == 200
    assert b'testuser2\'s Files' in response.data

def test_public_profile_404_for_nonexistent_user(client):
    """Test that public profile returns 404 for nonexistent user"""
    login(client, 'testuser1')
    response = client.get('/profile/nonexistent')
    assert response.status_code == 404
