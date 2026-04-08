# =============================
# FINAL PRO+ VERSION
# Added:
# - Search by Name
# - Edit/Delete
# - Live Dashboard (auto refresh)
# - Clear Add Data feedback
# =============================

from flask import Flask, render_template, request, redirect, session
import pandas as pd
import sqlite3
import os
import matplotlib.pyplot as plt
import random

app = Flask(__name__)
app.secret_key = 'secret123'
DB = 'fraud.db'

# ----------------------
# DB
# ----------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        income INTEGER,
        transactions INTEGER,
        criminal INTEGER,
        loan_default INTEGER,
        suspicious_score INTEGER,
        result TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# ----------------------
# LOGIC
# ----------------------
def detect_fraud(data):
    score = 0
    if int(data['criminal']) == 1: score += 40
    if int(data['loan_default']) == 1: score += 20
    if int(data['suspicious_score']) > 70: score += 30
    if int(data['transactions']) > int(data['income']) * 2: score += 20
    return ("Fraud", score) if score >= 50 else ("Not Fraud", score)

# ----------------------
# HOME
# ----------------------
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/check', methods=['GET', 'POST'])
def check():
    if request.method == 'POST':
        data = request.form.to_dict()
        result, score = detect_fraud(data)

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO users (name, age, income, transactions, criminal, loan_default, suspicious_score, result) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (data['name'], data['age'], data['income'], data['transactions'], data['criminal'], data['loan_default'], data['suspicious_score'], result))
        conn.commit()
        conn.close()

        return render_template("result.html", result=result, score=score)

    return render_template("check.html")

# ----------------------
# LOGIN
# ----------------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        if request.form['username']=='admin' and request.form['password']=='1234':
            session['admin']=True
            return redirect('/admin')
        return "Invalid Login"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ----------------------
# ADD DATA (VISIBLE RESULT)
# ----------------------
@app.route('/add', methods=['GET','POST'])
def add():
    if request.method=='POST':
        data = request.form.to_dict()
        result,score = detect_fraud(data)

        conn=sqlite3.connect(DB)
        c=conn.cursor()
        c.execute("INSERT INTO users (name,age,income,transactions,criminal,loan_default,suspicious_score,result) VALUES (?,?,?,?,?,?,?,?)",
                  (data['name'],data['age'],data['income'],data['transactions'],data['criminal'],data['loan_default'],data['suspicious_score'],result))
        conn.commit(); conn.close()

        return f"<h3>✅ Data Saved</h3><p>Result: {result} | Score: {score}</p><a href='/admin'>Go Admin</a>"
    return render_template('add.html')

# ----------------------
# AUTO DATA
# ----------------------
@app.route('/auto')
def auto():
    names=["Amit","Rahul","Ravi","Sohan","Karan"]
    data={
        'name':random.choice(names),
        'age':random.randint(20,60),
        'income':random.randint(10000,50000),
        'transactions':random.randint(5000,150000),
        'criminal':random.randint(0,1),
        'loan_default':random.randint(0,1),
        'suspicious_score':random.randint(10,100)
    }
    result,_=detect_fraud(data)

    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute("INSERT INTO users (name,age,income,transactions,criminal,loan_default,suspicious_score,result) VALUES (?,?,?,?,?,?,?,?)",
              (data['name'],data['age'],data['income'],data['transactions'],data['criminal'],data['loan_default'],data['suspicious_score'],result))
    conn.commit(); conn.close()

    return redirect('/admin')

# ----------------------
# ADMIN + SEARCH
# ----------------------
@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/login')

    search = request.args.get('search')

    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()

    df['name'] = df['name'].astype(str)

    if search:
        search = str(search).strip().lower()

        if search.isdigit():
            num = int(search)
            df = df[
                (df['income'] == num) |
                (df['result'].str.lower() == ('fraud' if num == 1 else 'not fraud'))
            ]
        else:
            df = df[df['name'].str.lower().str.contains(search, na=False)]

    # Buttons
    df['Actions'] = df['id'].apply(lambda x: 
        f'<a href=\"/edit/{x}\" class=\"btn btn-sm btn-warning\">Edit</a> '
        f'<a href=\"/delete/{x}\" class=\"btn btn-sm btn-danger\">Delete</a>'
    )

    if df.empty:
        html = "<h3>No Data Found</h3>"
    else:
        html = df.to_html(classes='table table-bordered', index=False, escape=False)

    return render_template('admin.html', table=html)

# ----------------------
# DELETE
# ----------------------
@app.route('/delete/<int:id>')
def delete(id):
    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute("DELETE FROM users WHERE id=?",(id,))
    conn.commit(); conn.close()
    return redirect('/admin')

# ----------------------
# EDIT
# ----------------------
@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit(id):
    conn=sqlite3.connect(DB); c=conn.cursor()

    if request.method=='POST':
        data=request.form.to_dict()
        result,_=detect_fraud(data)
        c.execute("UPDATE users SET name=?,age=?,income=?,transactions=?,criminal=?,loan_default=?,suspicious_score=?,result=? WHERE id=?",
                  (data['name'],data['age'],data['income'],data['transactions'],data['criminal'],data['loan_default'],data['suspicious_score'],result,id))
        conn.commit(); conn.close()
        return redirect('/admin')

    user=c.execute("SELECT * FROM users WHERE id=?",(id,)).fetchone()
    conn.close()
    return render_template('edit.html',user=user)

# ----------------------
# GRAPH (AUTO REFRESH DASHBOARD)
# ----------------------
@app.route('/graph')
def graph():
    if not session.get('admin'): return redirect('/login')

    conn=sqlite3.connect(DB)
    df=pd.read_sql_query("SELECT * FROM users",conn)
    conn.close()

    if not os.path.exists('static'): os.makedirs('static')

    plt.figure()
    df['result'].value_counts().plot(kind='pie',autopct='%1.1f%%')
    plt.savefig('static/pie.png'); plt.close()

    return render_template('graph.html')

# ----------------------
# API FOR LIVE CHART (JSON)
# ----------------------
@app.route('/api/data')
def api_data():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT result, COUNT(*) as count FROM users GROUP BY result", conn)
    conn.close()

    data = {row['result']: row['count'] for _, row in df.iterrows()}
    return data

# ----------------------
if __name__=='__main__':
    app.run(debug=True)
