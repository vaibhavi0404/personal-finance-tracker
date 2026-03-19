from flask import Flask, render_template, request, redirect, session
import sqlite3
import random

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DB INIT =================
def init_db():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        mobile TEXT,
        pin TEXT DEFAULT '1234',
        balance INTEGER DEFAULT 0,
        cibil INTEGER DEFAULT 700
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount INTEGER,
        description TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

init_db()

# ================= HOME =================
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    # Transactions
    cur.execute("SELECT * FROM transactions WHERE user_id=?", (session['user_id'],))
    data = cur.fetchall()

    # User
    cur.execute("SELECT username, balance, cibil FROM users WHERE id=?", (session['user_id'],))
    user = cur.fetchone()

    if not user:
        conn.close()
        return redirect('/login')

    # Income
    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='income'", (session['user_id'],))
    income = cur.fetchone()[0] or 0

    # Expense
    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type!='income'", (session['user_id'],))
    expense = cur.fetchone()[0] or 0

    conn.close()

    return render_template('dashboard.html',
                           transactions=data,
                           balance=user[1],
                           username=user[0],
                           cibil=user[2],
                           msg=request.args.get('msg'),
                           income=income,
                           expense=expense)

# ================= SIGNUP =================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        m = request.form['mobile']
        pin = request.form['pin'] or '1234'

        conn = sqlite3.connect('users.db')
        cur = conn.cursor()

        cur.execute("INSERT INTO users (username, password, mobile, pin) VALUES (?,?,?,?)",
                    (u, p, m, pin))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('signup.html')

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = sqlite3.connect('users.db')
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        user = cur.fetchone()

        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/')
        else:
            return "Invalid credentials"

    return render_template('login.html')

# ================= OTP =================
@app.route('/otp')
def generate_otp():
    code = random.randint(1000, 9999)
    session['otp'] = str(code)
    return f"Your OTP is {code}"

# ================= ADD TRANSACTION =================
@app.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session:
        return redirect('/login')

    t = request.form['type']
    amt = int(request.form['amount'])
    desc = request.form['description']

    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    if t == 'income':
        cur.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amt, session['user_id']))
    else:
        cur.execute("UPDATE users SET balance = balance - ? WHERE id=?", (amt, session['user_id']))

    cur.execute("INSERT INTO transactions (user_id, type, amount, description) VALUES (?,?,?,?)",
                (session['user_id'], t, amt, desc))

    conn.commit()
    conn.close()

    return redirect('/')

# ================= SEND MONEY =================
@app.route('/send', methods=['POST'])
def send():
    if 'user_id' not in session:
        return redirect('/login')

    pin = request.form['pin']
    to = request.form['to_user']
    amount = int(request.form['amount'])
    otp = request.form.get('otp')

    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    # Sender
    cur.execute("SELECT username, balance, pin FROM users WHERE id=?", (session['user_id'],))
    sender = cur.fetchone()

    if not sender:
        conn.close()
        return redirect('/login')

    # PIN check
    if pin != sender[2]:
        conn.close()
        return redirect('/?msg=Wrong PIN')

    # OTP check
    if otp != session.get('otp'):
        conn.close()
        return redirect('/?msg=Wrong OTP')

    # Receiver
    cur.execute("SELECT id FROM users WHERE username=?", (to,))
    receiver = cur.fetchone()

    if not receiver:
        conn.close()
        return redirect('/?msg=User not found')

    if sender[1] < amount:
        conn.close()
        return redirect('/?msg=Insufficient balance')

    receiver_id = receiver[0]

    # Transfer
    cur.execute("UPDATE users SET balance = balance - ? WHERE id=?", (amount, session['user_id']))
    cur.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, receiver_id))

    # Reward
    reward = 10 if amount > 100 else 0
    cur.execute("UPDATE users SET balance = balance + ? WHERE id=?", (reward, session['user_id']))

    # Transactions
    cur.execute("INSERT INTO transactions (user_id, type, amount, description) VALUES (?,?,?,?)",
                (session['user_id'], 'sent', amount, f"Sent to {to}"))

    cur.execute("INSERT INTO transactions (user_id, type, amount, description) VALUES (?,?,?,?)",
                (receiver_id, 'received', amount, f"Received from {sender[0]}"))

    conn.commit()
    conn.close()

    return render_template('success.html', amount=amount, to_user=to)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ================= RUN =================
if __name__ == "__main__":
    import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))