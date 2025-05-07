from flask import Flask, render_template, redirect, url_for, request, session
import os
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
                        password TEXT
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
        cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, password))
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
            return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/add_to_cart/<int:book_id>')
def add_to_cart(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO cart (user_id, book_id) VALUES (%s, %s)', (user_id, book_id))
    conn.commit()
    conn.close()

    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT b.title, b.author, b.price 
                      FROM cart c 
                      JOIN books b ON c.book_id = b.id 
                      WHERE c.user_id = %s''', (user_id,))
    cart_items = cursor.fetchall()
    total_price = sum(item[2] for item in cart_items) if cart_items else 0
    conn.close()

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/clear_cart')
def clear_cart():
    if 'user_id' in session:
        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE user_id = %s', (user_id,))
        conn.commit()
        conn.close()

    return redirect(url_for('cart'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
