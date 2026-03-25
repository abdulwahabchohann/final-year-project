# ReadWise — AI-Powered Book Recommendation System

## About
ReadWise is an AI-powered book recommendation system that matches what you want to read with how you feel right now. It uses transformer-based sentiment/emotion detection and semantic similarity to recommend relevant books. It also supports Google OAuth authentication and a REST API for integration.

## Features
- Mood-based book recommendations using NLP
- Sentiment analysis with transformer models
- Google OAuth authentication
- Collaborative filtering algorithm
- Admin panel
- REST API

## Tech Stack
- Backend: Django 5.2, Django REST Framework
- AI/ML: HuggingFace Transformers, Sentence Transformers, Scikit-learn
- Auth: Google OAuth via django-allauth
- Database: SQLite (dev), PostgreSQL (production)
- Deployment: Render / PythonAnywhere

## Setup Instructions
1. Clone the repo
2. Create virtual environment: python -m venv venv
3. Activate: source venv/bin/activate (Linux/Mac) or venv\Scripts\activate (Windows)
4. Install dependencies: pip install -r requirements.txt
5. Copy .env.example to .env and fill in values
6. Run migrations: python manage.py migrate
7. Run server: python manage.py runserver

## Environment Variables
Create a .env file with:
SECRET_KEY=your_django_secret_key
DEBUG=True
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
DATABASE_URL=your_database_url

## Project Structure
readwise/          - Main Django app
accounts/          - User authentication
data/              - Dataset files
scripts/           - Utility and data processing scripts
tests/             - Test files

