# PinTrader

A web application for users to save IPFS CID hashes and create pin agreements. 

## Project Structure

- `requirements.txt`: Contains all necessary Python dependencies
- `app.py`: Main Flask application with user authentication logic
- `templates/`: Directory containing all HTML templates

## Features
- Secure password hashing
- Responsive design using Bootstrap 5
- Flash messages for user feedback
- SQLite database for user data

## Setup

```bash
# Create a virtual environment:
python -m venv venv
source venv/bin/activate 

# Install dependencies:
pip install -r requirements.txt

# Initialize the database and run the application:
python init_db.py  # Create database tables
python app.py      # Start the application

# The application will be available at `http://localhost:5000`. 
```

## Tests
```bash
python -m pytest tests/test_upload.py -v
python -m pytest tests/test_search.py -v
```

## Usage

- Register a new account at `/register`
- Log in with your credentials at `/login`
- View your profile page at `/profile`
- Log out using the navigation menu

## Technical Details

The application uses SQLite as the database, which will be automatically created when you first run the application. All user data is stored securely with password hashing using Werkzeug's security features.
