# StudentBrand Hub

A web app where student entrepreneurs build a brand, plan social media posts,
track growth and record sales. BCA project (Flask + SQLite).

## Features
- Register / Login (hashed passwords, Flask sessions)
- Brand profile with logo upload and social links
- Post planner (Instagram / LinkedIn / YouTube) with status and filter
- Rule-based caption and hashtag generator
- Analytics dashboard (followers, likes, clicks) with Chart.js graphs
- Sales tracker: products, orders, revenue, and best-selling posts
- Public shareable brand page at `/b/<brand-slug>`

## Run it
```bash
python -m venv venv
venv\Scripts\activate        # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python seed.py               # optional demo data
python app.py
```
Open http://127.0.0.1:5000  
Demo login (after seed.py): `demo@student.com` / `demo1234`

## Structure
```
app.py          routes and logic
schema.sql      database tables
seed.py         demo data
templates/      HTML pages (Jinja2)
static/css      styling
static/js       Chart.js code
static/uploads  uploaded logos
```

## Database tables
users, brands, posts, metrics, products, orders

## Future improvements
- AI caption generation (Claude / OpenAI API)
- CSRF protection (Flask-WTF) and email verification
- Auto-fetch analytics from social media APIs
- Deploy on Render / PythonAnywhere

Set a real secret key before deploying: `SECRET_KEY=your-random-string`
