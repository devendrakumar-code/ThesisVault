<div align="center">

# 🎓 ThesisVault

**A Production-Grade Multi-Tenant SaaS Platform**
*Subscription & Feature Entitlement System*

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-thesisvault.live-4f46e5?style=for-the-badge)](https://thesisvault.live)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.x-42b883?style=for-the-badge&logo=vue.js)](https://vuejs.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![Redis](https://img.shields.io/badge/Redis-Celery-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)

> Built as part of the **Migri Technologies Full Stack Development Apprentice Assessment**

</div>

---

## 🚀 What is ThesisVault?

ThesisVault is a **thesis project management platform** that demonstrates a complete
subscription-driven feature entitlement system. Organizations subscribe to plans,
and every API action is gated by:

| Check | What it validates |
|---|---|
| 🔐 Auth | Valid, non-revoked token |
| 📋 Subscription | Plan is active and not expired |
| ✨ Feature | Plan includes the requested feature |
| 📊 Usage Limit | Org is within plan quota |

> **All enforcement happens at the API level — never just the frontend.**

---

## 🏗️ Architecture


---

## 🗄️ Database Schema

> 14 tables · UUID v7 PKs · Multi-tenant scoped · Soft deletes on all models

![Database ER Diagram](/thesis_vault.png)

**Core relationships:**
- `Plan` → `Organization` (1:N) — org subscribes to a plan
- `Organization` → `User` → `Project` → `Milestone` → `Submission`
- `SubscriptionHistory` — immutable audit log of every plan change
- `ActivityLog` — tracks all admin actions with timestamps

  
Vue 3 SPA → Nginx (HTTPS) → Flask API → MySQL
↓
Celery Worker → Redis
↓
Gemini 2.5 Flash (AI)


**Three middleware decorators enforce every rule:**
```python
@subscription_required                              # Is org active?
@requires_feature('ai_analysis')                    # Plan includes AI?
@limit_check('active_projects', 'max_active_projects')  # Within quota?
```

---

## 💎 Subscription Plans

| Feature | 🆓 Free | ⚡ Pro | 🏢 Enterprise |
|---|---|---|---|
| Active Projects | 3 | 50 | Unlimited |
| Students | 50 | 500 | Unlimited |
| AI Evaluations/month | ❌ | 100 | Unlimited |
| Grace Period | ❌ | ✅ | ✅ |

Plans are **fully database-driven** — add a new plan without touching business logic.

---

## 🛠️ Tech Stack

**Backend:** Flask · SQLAlchemy · Flask-Security-Too · MySQL · Celery · Redis  
**Frontend:** Vue 3 · Vite · Tailwind CSS · Pinia  
**AI:** Google Gemini 2.5 Flash  
**Infrastructure:** Ubuntu VPS · Nginx · Gunicorn · Let's Encrypt SSL  
**Email:** Flask-Mailman · Gmail SMTP  

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd thesisvault

# 2. Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config-template.py config.py   # add your DB, Gemini API key, mail config
flask db upgrade && python seed.py
python app.py

# 3. Frontend
cd ../frontend && npm install && npm run dev

# 4. Celery worker (for AI evaluation)
celery -A app:celery worker --loglevel=info -Q ai,default
```

---

## 🔑 Key Implementation Highlights

- **Race condition prevention** — atomic SQL increments (`UPDATE ... SET count = count + 1`)
- **Token revocation** — `RevokedToken` table checked on every request
- **Cross-tenant isolation** — global `@before_flush` hook blocks cross-org writes
- **Soft deletes** — all models use `deleted_at` with automatic query filtering
- **Audit trail** — every plan change and admin action logged immutably

---

## 📦 Deliverables

- ✅ Live deployment → [thesisvault.live](https://thesisvault.live)
- ✅ Multi-tenant SaaS with full subscription enforcement
- ✅ API-level feature + usage limit gating
- ✅ AI-powered thesis evaluation pipeline (Gemini + Celery)
- ✅ Subscription lifecycle + grace period + maintenance mode
- ✅ Full audit trail

---

<div align="center">

Made with ❤️ by **Devendra Kumar**

</div>
