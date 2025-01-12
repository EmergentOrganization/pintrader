# PinTrader

A web application for users to save IPFS CID hashes and create pin agreements. 

## Project Structure

```
pintrader/
├── frontend/               # Flask web application
│   ├── app.py             # Main Flask application
│   ├── requirements.txt   # Python dependencies
│   ├── Dockerfile        # Frontend container configuration
│   ├── templates/        # HTML templates
│   ├── tests/           # Test files
│   └── uploads/         # Directory for uploaded files
├── docker-compose.yml    # Docker services configuration
└── README.md
```

## Features
- User authentication with secure password hashing
- File upload to IPFS network
- PostgreSQL database for persistent storage
- Docker containerization for easy deployment
- Responsive design using Bootstrap 5
- Flash messages for user feedback

## Setup with Docker

```bash
# Build and start all services
docker-compose up --build

# The application will be available at `http://localhost:5000`
```

This will start three containers:
- Web application (Flask)
- PostgreSQL database
- IPFS node

To stop the services:
```bash
docker-compose down
```

To reset the database:
```bash
docker-compose down -v  # Remove volumes
docker-compose up --build  # Rebuild and start
```

## Development Setup

If you want to run the application locally for development:

```bash
# Create a virtual environment:
python -m venv venv
source venv/bin/activate 

# Install dependencies:
cd frontend
pip install -r requirements.txt

# Initialize the database and run the application:
python init_db.py  # Create database tables
python app.py      # Start the application
```

## Tests
```bash
# Run tests with Docker
docker-compose exec web pytest -v tests/

# Or run locally
cd frontend
python -m pytest tests/ -v
```

## Usage

- Register a new account at `/register`
- Log in with your credentials at `/login`
- Upload files to IPFS from your profile page at `/profile`
- View your uploaded files and their IPFS hashes
- Log out using the navigation menu

## Technical Details

The application uses:
- Flask for the web framework
- PostgreSQL for the database
- IPFS for distributed file storage
- Docker for containerization and service orchestration
- Flask-Login for user authentication
- Werkzeug's security features for password hashing
