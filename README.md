# PinTrader

A web application with user authentication and profile management.

## Project Structure

- `requirements.txt`: Contains all necessary Python dependencies
- `app.py`: Main Flask application with user authentication logic
- `templates/`: Directory containing all HTML templates
  - `base.html`: Base template with navigation and common elements
  - `index.html`: Homepage
  - `login.html`: Login page
  - `register.html`: Registration page
  - `profile.html`: User profile page

## Features

- User registration with username, email, and password
- Secure password hashing
- User login/logout functionality
- Protected profile page
- Responsive design using Bootstrap 5
- Flash messages for user feedback
- SQLite database for user data

## Setup Instructions

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`. 

## Usage

- Register a new account at `/register`
- Log in with your credentials at `/login`
- View your profile page at `/profile`
- Log out using the navigation menu

## Technical Details

The application uses SQLite as the database, which will be automatically created when you first run the application. All user data is stored securely with password hashing using Werkzeug's security features.
