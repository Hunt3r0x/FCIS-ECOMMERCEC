from flask import Flask, render_template, redirect, url_for, request, session
import hashlib
import mysql.connector

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="passwd",
        database="bookstore"
    )

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS books (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(255),
                        author VARCHAR(255),
                        price FLOAT
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(255) UNIQUE,
                        password TEXT,
                        is_admin BOOLEAN DEFAULT FALSE
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        book_id INT,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (book_id) REFERENCES books(id)
                    )''')

    conn.commit()
    conn.close()

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books')
    books = cursor.fetchall()
    conn.close()
    return render_template('index.html', books=books)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]

        is_admin = user_count == 0

        cursor.execute('INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)', (username, password, is_admin))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['is_admin'] = user[3]
            return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if 'is_admin' not in session or not session['is_admin']:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'delete_user':
            user_id = request.form.get('user_id')
            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))

        elif action == 'add_book':
            title = request.form.get('title')
            author = request.form.get('author')
            price = float(request.form.get('price'))
            cursor.execute('INSERT INTO books (title, author, price) VALUES (%s, %s, %s)', (title, author, price))

        elif action == 'delete_book':
            book_id = request.form.get('book_id')
            cursor.execute('DELETE FROM books WHERE id = %s', (book_id,))

        elif action == 'edit_book':
            book_id = request.form.get('book_id')
            title = request.form.get('title')
            author = request.form.get('author')
            price = float(request.form.get('price'))
            cursor.execute('UPDATE books SET title=%s, author=%s, price=%s WHERE id=%s', (title, author, price, book_id))

        elif action == 'edit_user':
            user_id = request.form.get('user_id')
            username = request.form.get('username')
            is_admin = request.form.get('is_admin') == 'on'
            cursor.execute('UPDATE users SET username=%s, is_admin=%s WHERE id=%s', (username, is_admin, user_id))

        conn.commit()

    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()

    cursor.execute('SELECT * FROM books')
    books = cursor.fetchall()

    conn.close()
    return render_template('admin.html', users=users, books=books)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
