# Mendora AI — Backend

Python + FastAPI + PostgreSQL + Gemini AI backend for the Mendora university wellness platform.

## Quick Start (Local)

### 1. PostgreSQL Setup
```bash
psql -U postgres
CREATE DATABASE mendora_db;
CREATE USER mendora_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE mendora_db TO mendora_user;
\q
```

### 2. Python Environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
```bash
cp .env.example .env
# Edit .env with your values:
# - DATABASE_URL
# - SECRET_KEY (generate: python -c "import secrets; print(secrets.token_hex(32))")
# - GEMINI_API_KEY  (from https://aistudio.google.com/app/apikey)
# - MAIL_USERNAME + MAIL_PASSWORD (Gmail App Password)
```

### 4. Run Migrations
```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

### 5. Start Server
```bash
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

---

## API Prefix: `/api/v1`

| Module | Prefix | Auth Required |
|--------|--------|--------------|
| Auth | `/auth` | No (except /me) |
| Wellness | `/wellness` | Yes |
| Chat | `/chat` | Yes |
| Focus | `/focus` | Yes |
| Admin | `/admin` | Yes (admin role) |
| Counselor | `/counselor` | Yes (counselor/admin) |

---

## Deploy to Railway (Recommended)

```bash
npm install -g @railway/cli
railway login
railway init
# Add PostgreSQL plugin from Railway dashboard
# Set env vars in Railway dashboard (GEMINI_API_KEY, SECRET_KEY, MAIL_*, FRONTEND_URL)
railway up
```

## Deploy to Render

1. Push to GitHub
2. New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add PostgreSQL → set env vars → Deploy

## Deploy to VPS (Ubuntu)

```bash
sudo apt install python3.11 python3.11-venv postgresql nginx -y
git clone <your-repo> && cd mendora-backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt gunicorn
cp .env.example .env  # fill in values
alembic upgrade head
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Getting Free API Keys

**Gemini API:** https://aistudio.google.com/app/apikey  
**Gmail App Password:** Google Account → Security → 2-Step Verification → App Passwords
