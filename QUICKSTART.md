# Quickstart

This quick guide gets ReadWise running locally.

1. Create/activate a virtual environment
   - `python -m venv venv`
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Copy environment variables: `cp .env.example .env` (or create `.env` manually) and update values.
4. Apply migrations: `python manage.py migrate`
5. Run the development server: `python manage.py runserver`

