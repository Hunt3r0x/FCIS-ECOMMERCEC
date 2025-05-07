import os
import random
import hashlib
import mysql.connector
from flask import Flask, render_template, redirect, url_for, request, session

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Directory for cover images
IMG_DIR = os.path.join(app.static_folder, 'imgs')

# -----------------------------
# Database helpers
# -----------------------------

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="passwd",
        database="bookstore",
        autocommit=False,
    )


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS books (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255),
                author VARCHAR(255),
                price FLOAT,
                cover_url VARCHAR(512) DEFAULT NULL
            ) ENGINE=InnoDB"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE,
                password TEXT,
                is_admin BOOLEAN DEFAULT FALSE
            ) ENGINE=InnoDB"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS cart (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                book_id INT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            ) ENGINE=InnoDB"""
    )
    conn.commit()
    conn.close()

# -----------------------------
# Authentication routes
# -----------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM users')
        is_admin = (cur.fetchone()[0] == 0)
        cur.execute(
            'INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)',
            (username, password, is_admin)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT id, is_admin FROM users WHERE username = %s AND password = %s',
            (username, password)
        )
        user = cur.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['is_admin'] = bool(user[1])
            session['username'] = username
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -----------------------------
# Shop routes
# -----------------------------

def choose_random_cover():
    imgs = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(('jpg','jpeg','png','webp'))]
    return f'imgs/{random.choice(imgs)}' if imgs else None

@app.route('/')
def home():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM books')
    raw = cur.fetchall()
    conn.close()
    books = []
    for b in raw:
        cover = b[4] if b[4] else choose_random_cover()
        books.append((b[0], b[1], b[2], b[3], cover))
    return render_template('index.html', books=books)

@app.route('/add_to_cart/<int:book_id>')
def add_to_cart(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO cart (user_id, book_id) VALUES (%s, %s)',
                (session['user_id'], book_id))
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT b.id, b.title, b.author, b.price, b.cover_url '
        'FROM cart c JOIN books b ON c.book_id=b.id WHERE c.user_id=%s',
        (session['user_id'],)
    )
    raw = cur.fetchall()
    conn.close()
    items = []
    for i in raw:
        cover = i[4] if i[4] else choose_random_cover()
        items.append((i[0], i[1], i[2], i[3], cover))
    total = sum(x[3] for x in items)
    return render_template('cart.html', cart_items=items, total_price=total)

@app.route('/clear_cart')
def clear_cart():
    if 'user_id' in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM cart WHERE user_id=%s', (session['user_id'],))
        conn.commit()
        conn.close()
    return redirect(url_for('cart'))

# -----------------------------
# Admin panel
# -----------------------------

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('home'))
    conn = get_db_connection()
    cur = conn.cursor()
    images = [f'imgs/{f}' for f in os.listdir(IMG_DIR)
              if f.lower().endswith(('jpg','jpeg','png','webp'))]
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_book':
            cur.execute('INSERT INTO books (title, author, price, cover_url) VALUES (%s, %s, %s, %s)',
                        (request.form['title'].strip(),
                         request.form['author'].strip(),
                         float(request.form['price']),
                         request.form.get('cover_url') or None))
            conn.commit()
        elif action == 'delete_book':
            cur.execute('DELETE FROM books WHERE id=%s', (request.form['book_id'],))
            conn.commit()
            cur.execute('SELECT COUNT(*) FROM books')
            if cur.fetchone()[0] == 0:
                cur.execute('ALTER TABLE books AUTO_INCREMENT = 1')
                conn.commit()
        elif action == 'edit_book':
            cur.execute('UPDATE books SET title=%s, author=%s, price=%s, cover_url=%s WHERE id=%s',
                        (request.form['title'].strip(),
                         request.form['author'].strip(),
                         float(request.form['price']),
                         request.form.get('cover_url') or None,
                         request.form['book_id']))
            conn.commit()
        elif action == 'delete_user':
            cur.execute('DELETE FROM users WHERE id=%s', (request.form['user_id'],))
            conn.commit()
            # reset auto-increment to next id
            cur.execute('SELECT IFNULL(MAX(id), 0) FROM users')
            max_id = cur.fetchone()[0]
            cur.execute('ALTER TABLE users AUTO_INCREMENT = %s', (max_id + 1,))
            conn.commit()
        elif action == 'edit_user':
            cur.execute('UPDATE users SET username=%s, is_admin=%s WHERE id=%s',
                        (request.form['username'].strip(),
                         request.form.get('is_admin') == 'on',
                         request.form['user_id']))
            conn.commit()
    cur.execute('SELECT * FROM users')
    users = cur.fetchall()
    cur.execute('SELECT * FROM books')
    books = cur.fetchall()
    conn.close()
    return render_template('admin.html', users=users, books=books, images=images)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
