import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'asi_tech_secret_key_2024_secure'

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ADMIN_PASSWORD = "vape1098"
ADMIN_URL = "/admin-portal-secret"

DATABASE = os.path.join(BASE_DIR, 'blog.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS blogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                title_image TEXT,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                author TEXT DEFAULT 'ASI TECH',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blog_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                rating INTEGER DEFAULT 5,
                comment TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (blog_id) REFERENCES blogs (id)
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        db.commit()

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database on startup
init_db()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============== ROUTES ==============

@app.route('/')
def home():
    db = get_db()
    blogs = db.execute(
        "SELECT * FROM blogs ORDER BY created_at DESC LIMIT 6"
    ).fetchall()
    categories = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()
    return render_template('index.html', blogs=blogs, categories=categories)

@app.route('/blog/<slug>')
def blog_detail(slug):
    db = get_db()
    blog = db.execute("SELECT * FROM blogs WHERE slug = ?", (slug,)).fetchone()
    if blog is None:
        flash('Blog not found!', 'error')
        return redirect(url_for('home'))
    db.execute("UPDATE blogs SET views = views + 1 WHERE id = ?", (blog['id'],))
    db.commit()
    reviews = db.execute(
        "SELECT * FROM reviews WHERE blog_id = ? ORDER BY created_at DESC",
        (blog['id'],)
    ).fetchall()
    related = db.execute(
        "SELECT * FROM blogs WHERE category = ? AND id != ? LIMIT 3",
        (blog['category'], blog['id'])
    ).fetchall()
    return render_template('blog.html', blog=blog, reviews=reviews, related=related)

@app.route('/blog/<slug>/review', methods=['POST'])
def add_review(slug):
    db = get_db()
    blog = db.execute("SELECT id FROM blogs WHERE slug = ?", (slug,)).fetchone()
    if blog is None:
        flash('Blog not found!', 'error')
        return redirect(url_for('home'))
    name = request.form.get('name', 'Anonymous')
    email = request.form.get('email', '')
    rating = request.form.get('rating', 5)
    comment = request.form.get('comment', '')
    if not comment:
        flash('Please write a review!', 'error')
        return redirect(url_for('blog_detail', slug=slug))
    db.execute(
        "INSERT INTO reviews (blog_id, name, email, rating, comment) VALUES (?, ?, ?, ?, ?)",
        (blog['id'], name, email, rating, comment)
    )
    db.commit()
    flash('Review posted successfully!', 'success')
    return redirect(url_for('blog_detail', slug=slug) + '#reviews')

@app.route('/category/<category>')
def category_page(category):
    db = get_db()
    blogs = db.execute(
        "SELECT * FROM blogs WHERE category = ? ORDER BY created_at DESC",
        (category,)
    ).fetchall()
    categories = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()
    return render_template('category.html', blogs=blogs, current_category=category, categories=categories)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    db = get_db()
    if query:
        blogs = db.execute(
            "SELECT * FROM blogs WHERE title LIKE ? OR content LIKE ? OR category LIKE ? ORDER BY created_at DESC",
            (f'%{query}%', f'%{query}%', f'%{query}%')
        ).fetchall()
    else:
        blogs = []
    categories = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()
    return render_template('search.html', blogs=blogs, query=query, categories=categories)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        if not name or not email or not message:
            flash('Please fill all required fields!', 'error')
        else:
            db = get_db()
            db.execute(
                "INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)",
                (name, email, subject, message)
            )
            db.commit()
            flash('Message sent successfully! We will get back to you soon.', 'success')
            return redirect(url_for('contact'))
    db = get_db()
    categories = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()
    return render_template('contact.html', categories=categories)

# ============== ADMIN ROUTES (HIDDEN) ==============

@app.route(ADMIN_URL)
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route(ADMIN_URL + '/auth', methods=['POST'])
def admin_auth():
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        flash('Welcome to Admin Dashboard!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid password!', 'error')
        return redirect(url_for('admin_login'))

@app.route(ADMIN_URL + '/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    blogs = db.execute("SELECT * FROM blogs ORDER BY created_at DESC").fetchall()
    total_blogs = db.execute("SELECT COUNT(*) as count FROM blogs").fetchone()['count']
    total_reviews = db.execute("SELECT COUNT(*) as count FROM reviews").fetchone()['count']
    total_contacts = db.execute("SELECT COUNT(*) as count FROM contacts").fetchone()['count']
    return render_template('admin_dashboard.html', blogs=blogs,
                         total_blogs=total_blogs, total_reviews=total_reviews,
                         total_contacts=total_contacts)

@app.route(ADMIN_URL + '/create', methods=['GET', 'POST'])
def admin_create():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        title = request.form.get('title')
        slug = request.form.get('slug')
        category = request.form.get('category')
        content = request.form.get('content')
        if not title or not slug or not category or not content:
            flash('Please fill all required fields!', 'error')
            return redirect(url_for('admin_create'))
        title_image = None
        if 'title_image' in request.files:
            file = request.files['title_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"title_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                title_image = filename
        inline_images = {}
        for key in request.files:
            if key.startswith('inline_image_'):
                file = request.files[key]
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"inline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    inline_images[key] = filename
        for key, filename in inline_images.items():
            placeholder = f"[{key}]"
            content = content.replace(placeholder, f'<img src="/static/uploads/{filename}" class="blog-inline-img" alt="Blog Image">')
        db = get_db()
        try:
            db.execute(
                "INSERT INTO blogs (title, slug, title_image, content, category) VALUES (?, ?, ?, ?, ?)",
                (title, slug, title_image, content, category)
            )
            db.commit()
            flash('Blog created successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except sqlite3.IntegrityError:
            flash('Slug already exists! Use a unique slug.', 'error')
            return redirect(url_for('admin_create'))
    return render_template('admin_create.html')

@app.route(ADMIN_URL + '/edit/<int:blog_id>', methods=['GET', 'POST'])
def admin_edit(blog_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    blog = db.execute("SELECT * FROM blogs WHERE id = ?", (blog_id,)).fetchone()
    if blog is None:
        flash('Blog not found!', 'error')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        title = request.form.get('title')
        slug = request.form.get('slug')
        category = request.form.get('category')
        content = request.form.get('content')
        title_image = blog['title_image']
        if 'title_image' in request.files:
            file = request.files['title_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"title_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                title_image = filename
        db.execute(
            "UPDATE blogs SET title = ?, slug = ?, title_image = ?, content = ?, category = ? WHERE id = ?",
            (title, slug, title_image, content, category, blog_id)
        )
        db.commit()
        flash('Blog updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_create.html', blog=blog, edit_mode=True)

@app.route(ADMIN_URL + '/delete/<int:blog_id>')
def admin_delete(blog_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    db.execute("DELETE FROM blogs WHERE id = ?", (blog_id,))
    db.execute("DELETE FROM reviews WHERE blog_id = ?", (blog_id,))
    db.commit()
    flash('Blog deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route(ADMIN_URL + '/contacts')
def admin_contacts():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    contacts = db.execute("SELECT * FROM contacts ORDER BY created_at DESC").fetchall()
    return render_template('admin_contacts.html', contacts=contacts)

@app.route(ADMIN_URL + '/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.context_processor
def inject_categories():
    db = get_db()
    categories = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()
    return dict(all_categories=categories)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
Fix database for Render
