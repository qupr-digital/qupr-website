# Qupr Digital - Invoice Management Platform

A Flask-based fintech platform for invoice management.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
copy .env.example .env
# Edit .env with your settings
```

4. Run application:
```bash
python run.py
```

## Production Deployment

Using Gunicorn + Nginx:
```bash
gunicorn -c gunicorn_config.py wsgi:application
```

## Tech Stack

- Flask 3.0
- MongoDB (PyMongo)
- Flask-Session
- Jinja2
- Nginx + Gunicorn
