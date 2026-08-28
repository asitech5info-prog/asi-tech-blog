# ASI TECH — Next-Gen AI & Technology Publishing Platform

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)

**ASI TECH** is an enterprise-grade, high-performance technology publication and AI research blogging platform. Engineered with a responsive modern UI, interactive AI Assistant (Gemini Engine & local cognitive fallback), dual reading modes (ELI5 toggle), user authentication, admin analytics dashboard, and automated verification suites.

---

## 🚀 Key Features

- 🧠 **ASI Enterprise AI Assistant**: Floating contextual research chatbot with code copy controls, markdown parsing, and Gemini AI integration.
- 👶 **Interactive ELI5 Mode**: One-click "Explain Like I'm 5" toggle on all technical articles for simplified conceptual learning.
- 🎨 **Modern Design System**:
  - Dark / Light theme toggle with persistent user preference.
  - Glassmorphic card design, smooth micro-animations, and fluid responsive typography.
  - Hero carousel with featured articles and category pills.
- 🔐 **Authentication Suite**:
  - Modal-based User Signup and Login (Email / Password).
  - One-Click Google / Gmail authentication simulation.
- ✍️ **Admin Content Suite**:
  - Dedicated secret portal (`/admin-portal-secret`).
  - Rich Markdown / easy-syntax article composer with live preview and custom image uploads.
  - Interactive management dashboard for articles, reader comments, and contact inquiries.
- ⚡ **Full SEO & Analytics**:
  - Dynamic meta tags, reading time calculation, live search with instant filtering, view & like metrics.
  - Fully responsive error handlers (404 and 500 error pages).

---

## 📂 Project Structure

```
asi-tech-blog/
├── app.py                      # Core Flask application, routes, AI engine, and database schema
├── requirements.txt            # Python dependencies (Flask, Werkzeug, gunicorn)
├── Procfile                    # Deployment configuration for PaaS (Render / Railway / Heroku)
├── .gitignore                  # Git ignore rules
├── README.md                   # Documentation
├── static/
│   ├── css/
│   │   └── style.css           # Modern design system, theme tokens, and animations
│   ├── js/
│   │   └── script.js           # Client interactions, AI chat widget, auth modals, theme toggler
│   └── uploads/                # Curated SVG article cover assets and media
├── templates/
│   ├── base.html               # Base layout with navbar, footer, auth modal, and AI assistant
│   ├── index.html              # Home page with hero, featured posts, and category grids
│   ├── blog.html               # Article reading view with ELI5 toggle, reviews, and share tools
│   ├── category.html           # Category-filtered articles list
│   ├── search.html             # Real-time search results page
│   ├── contact.html            # Contact us page with inquiry form
│   ├── admin_login.html        # Admin portal secure login
│   ├── admin_dashboard.html    # Admin management center and analytics
│   ├── admin_create.html       # Article composer with syntax tools
│   ├── admin_contacts.html     # Reader inquiries and message inbox
│   ├── 404.html                # Custom Not Found error page
│   └── 500.html                # Custom Internal Server Error page
└── tests/
    ├── test_all_features.py    # Comprehensive automated test suite
    └── verify_ui_rendering.py  # UI & AI widget rendering verification
```

---

## 🛠️ Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/asitech5info-prog/asi-tech-blog.git
cd asi-tech-blog
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Development Server
```bash
python app.py
```
Open `http://127.0.0.1:5000` in your web browser.

---

## 🔑 Environment Variables & Admin Portal

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ADMIN_PASSWORD` | Secret admin access password | `vape1098` |
| `GEMINI_API_KEY` | Google Gemini API key for live AI answers | *(Optional - local cognitive engine used as fallback)* |

- **Admin Portal URL**: `http://127.0.0.1:5000/admin-portal-secret`
- **Default Password**: `vape1098`

---

## 🧪 Testing & Verification

Run the comprehensive test suite:
```bash
python tests/test_all_features.py
python tests/verify_ui_rendering.py
```

---

## 📄 License & Contact
- **Author**: ASI TECH
- **Email**: asitech5info@gmail.com
- **YouTube**: HOW TECH WORKS
