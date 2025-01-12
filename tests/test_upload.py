import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os
import tempfile
import time
import json
from pathlib import Path
from app import app, db, User, File
from selenium.common.exceptions import TimeoutException
import hashlib

@pytest.fixture(scope="module")
def chrome_driver():
    """Set up Chrome driver with headless mode"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')  # Set a larger window size
    
    # Use local chromedriver
    driver_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chromedriver/chromedriver-linux64/chromedriver')
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Set window size explicitly
    driver.set_window_size(1920, 1080)
    
    # Set an implicit wait for better reliability
    driver.implicitly_wait(10)
    
    yield driver
    driver.quit()

@pytest.fixture(scope="module")
def test_app():
    """Create a test Flask application"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost:5000'
    
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        
        # Create a test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        
        yield app
        
        # Clean up
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope="module")
def flask_server(test_app):
    """Start Flask server for testing"""
    from threading import Thread
    server = Thread(target=test_app.run, kwargs={'use_reloader': False})
    server.daemon = True
    server.start()
    
    # Give the server a moment to start
    time.sleep(2)
    
    yield

@pytest.fixture
def authenticated_driver(chrome_driver, flask_server):
    """Set up an authenticated browser session"""
    # First logout if already logged in
    chrome_driver.get('http://localhost:5000/logout')
    
    # Now try to login
    chrome_driver.get('http://localhost:5000/login')
    
    # Wait for login form elements to be present and visible
    wait = WebDriverWait(chrome_driver, 10)
    username_input = wait.until(EC.presence_of_element_located((By.ID, 'username')))
    password_input = wait.until(EC.presence_of_element_located((By.ID, 'password')))
    submit_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[type="submit"]')))
    
    username_input.send_keys('testuser')
    password_input.send_keys('testpass123')
    submit_button.click()
    
    # Wait for redirect to complete
    wait.until(lambda driver: driver.current_url.startswith('http://localhost:5000/profile'))
    
    return chrome_driver

def create_test_file(content="Test file content"):
    """Create a temporary test file with specified content"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(content)
    return f.name

def test_upload_page_requires_login(chrome_driver, flask_server):
    """Test that the upload page redirects to login when not authenticated"""
    chrome_driver.get('http://localhost:5000/upload')
    
    # Should be redirected to login with next parameter
    assert chrome_driver.current_url.startswith('http://localhost:5000/login')
    assert 'next=%2Fupload' in chrome_driver.current_url

def test_upload_page_accessible_when_logged_in(authenticated_driver):
    """Test that authenticated users can access the upload page"""
    authenticated_driver.get('http://localhost:5000/upload')
    
    # Should stay on upload page
    assert authenticated_driver.current_url == 'http://localhost:5000/upload'
    
    # Check for form elements
    assert authenticated_driver.find_element(By.ID, 'file')
    assert authenticated_driver.find_element(By.ID, 'description')

def test_file_hash_computation(authenticated_driver):
    """Test that file hash is computed correctly when a file is selected"""
    authenticated_driver.get('http://localhost:5000/upload')
    
    # Create a test file
    test_file_path = create_test_file()
    try:
        # Find the file input and upload the test file
        file_input = authenticated_driver.find_element(By.ID, 'file')
        file_input.send_keys(test_file_path)
        
        # Wait for the hash to be computed
        multihash_input = WebDriverWait(authenticated_driver, 10).until(
            lambda driver: driver.find_element(By.ID, 'multihash').get_attribute('value') != ''
        )
        
        # Get the computed hash
        computed_hash = authenticated_driver.find_element(By.ID, 'multihash').get_attribute('value')
        
        # Verify the hash format (should be a CIDv1)
        assert computed_hash.startswith('b')  # CIDv1 in base32 starts with 'b'
        assert len(computed_hash) > 40  # CIDv1 should be fairly long
        
    finally:
        os.remove(test_file_path)

def test_complete_upload_process(authenticated_driver):
    """Test the complete file upload process"""
    # Create a test file
    test_file_path = create_test_file()
    
    try:
        # Clean up any existing files with the same content
        with app.app_context():
            # First compute the hash that will be used
            test_file = Path(test_file_path).read_bytes()
            hash_obj = hashlib.sha256()
            hash_obj.update(test_file)
            hash_hex = hash_obj.hexdigest()
            
            # Convert hex to CIDv1
            multicodec_prefix = bytes([0x12, 0x20])  # sha2-256 with 32 bytes length
            hash_bytes = bytes.fromhex(hash_hex)
            full_bytes = multicodec_prefix + hash_bytes
            cid_bytes = bytes([0x01, 0x55]) + full_bytes
            multihash = 'b' + cid_bytes.hex().upper()
            
            # Delete any files with this hash
            File.query.filter_by(multihash=multihash).delete()
            db.session.commit()
        
        authenticated_driver.get('http://localhost:5000/upload')
        
        # Upload file
        file_input = authenticated_driver.find_element(By.ID, 'file')
        file_input.send_keys(test_file_path)
        
        # Wait for hash computation
        WebDriverWait(authenticated_driver, 10).until(
            lambda driver: driver.find_element(By.ID, 'multihash').get_attribute('value') != ''
        )
        
        # Add description
        description_input = authenticated_driver.find_element(By.ID, 'description')
        description_input.send_keys('Test upload description')
        
        # Submit form
        submit_button = authenticated_driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        authenticated_driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        time.sleep(1)  # Wait for scroll to complete
        submit_button.click()
        
        # Check if there's an alert (in case of error)
        try:
            alert = WebDriverWait(authenticated_driver, 3).until(EC.alert_is_present())
            alert_text = alert.text
            alert.accept()
            pytest.fail(f"Unexpected alert: {alert_text}")
        except TimeoutException:
            pass  # No alert, which is good
        
        # Wait for redirect to profile page
        WebDriverWait(authenticated_driver, 10).until(
            lambda driver: driver.current_url == 'http://localhost:5000/profile'
        )
        
        # Verify file appears in profile
        WebDriverWait(authenticated_driver, 10).until(
            lambda driver: len(driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')) > 0
        )
        
    finally:
        os.remove(test_file_path)
        # Clean up the test file from database
        with app.app_context():
            File.query.filter_by(multihash=multihash).delete()
            db.session.commit()

def test_duplicate_file_upload(authenticated_driver):
    """Test that uploading the same file twice is handled properly"""
    # Create a test file
    test_file_path = create_test_file()
    
    try:
        # Clean up any existing files with the same content
        with app.app_context():
            # First compute the hash that will be used
            test_file = Path(test_file_path).read_bytes()
            hash_obj = hashlib.sha256()
            hash_obj.update(test_file)
            hash_hex = hash_obj.hexdigest()
            
            # Convert hex to CIDv1
            multicodec_prefix = bytes([0x12, 0x20])  # sha2-256 with 32 bytes length
            hash_bytes = bytes.fromhex(hash_hex)
            full_bytes = multicodec_prefix + hash_bytes
            cid_bytes = bytes([0x01, 0x55]) + full_bytes
            multihash = 'b' + cid_bytes.hex().upper()
            
            # Delete any files with this hash
            File.query.filter_by(multihash=multihash).delete()
            db.session.commit()
        
        authenticated_driver.get('http://localhost:5000/upload')
        
        # First upload
        file_input = authenticated_driver.find_element(By.ID, 'file')
        file_input.send_keys(test_file_path)
        
        # Wait for hash computation
        WebDriverWait(authenticated_driver, 10).until(
            lambda driver: driver.find_element(By.ID, 'multihash').get_attribute('value') != ''
        )
        
        # Submit form
        submit_button = authenticated_driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        authenticated_driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        time.sleep(1)  # Wait for scroll to complete
        submit_button.click()
        
        # Check if there's an alert (in case of error)
        try:
            alert = WebDriverWait(authenticated_driver, 3).until(EC.alert_is_present())
            alert_text = alert.text
            alert.accept()
            pytest.fail(f"Unexpected alert on first upload: {alert_text}")
        except TimeoutException:
            pass  # No alert, which is good
        
        # Wait for redirect to profile page
        WebDriverWait(authenticated_driver, 10).until(
            lambda driver: driver.current_url == 'http://localhost:5000/profile'
        )
        
        # Try uploading the same file again
        authenticated_driver.get('http://localhost:5000/upload')
        file_input = authenticated_driver.find_element(By.ID, 'file')
        file_input.send_keys(test_file_path)
        
        # Wait for hash computation
        WebDriverWait(authenticated_driver, 10).until(
            lambda driver: driver.find_element(By.ID, 'multihash').get_attribute('value') != ''
        )
        
        # Submit form
        submit_button = authenticated_driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        authenticated_driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        time.sleep(1)  # Wait for scroll to complete
        submit_button.click()
        
        # Wait for and handle the alert
        alert = WebDriverWait(authenticated_driver, 10).until(EC.alert_is_present())
        assert "File with this hash already exists" in alert.text
        alert.accept()
        
        # After accepting the alert, we should still be on the upload page
        assert authenticated_driver.current_url == 'http://localhost:5000/upload'
        
    finally:
        os.remove(test_file_path)
        # Clean up the test file from database
        with app.app_context():
            File.query.filter_by(multihash=multihash).delete()
            db.session.commit()
