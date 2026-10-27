from flask import Flask,render_template,request,session,redirect,url_for,flash,abort
from werkzeug.security import generate_password_hash,check_password_hash
from functools import wraps
from pathlib import Path
import os,sqlite3
app=Flask(__name__)
app.secret_key=os.getenv('SECRET_KEY','local-development-only')
DB=Path(__file__).parent/'instance'/'app.db'
DB.parent.mkdir(exist_ok=True)
def connect():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def login_required(fn):
 @wraps(fn)
 def wrapped(*args,**kwargs):
  if 'user' not in session:return redirect(url_for('login'))
  return fn(*args,**kwargs)
 return wrapped
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  email=request.form.get('email','').strip().lower();pw=request.form.get('password','')
  with connect() as c:
   if request.form.get('action')=='register':
    if len(pw)<8 or not email:flash('Use a valid email and 8+ character password.');return redirect(url_for('login'))
    try:c.execute('INSERT INTO users(email,password) VALUES(?,?)',(email,generate_password_hash(pw)))
    except sqlite3.IntegrityError:flash('Account exists.');return redirect(url_for('login'))
   row=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
   if row and check_password_hash(row['password'],pw):session.clear();session['user']=row['id'];return redirect(url_for('index'))
  flash('Invalid credentials.')
 return render_template('login.html')
@app.route('/logout',methods=['POST'])
def logout():session.clear();return redirect(url_for('index'))

def init_db():
 with connect() as c:
  c.executescript("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL); CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT,price INTEGER,category TEXT); CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,user_id INTEGER,items TEXT,total INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);")
  if not c.execute("SELECT 1 FROM products LIMIT 1").fetchone():c.execute("INSERT INTO products(name,price,category) VALUES ('Studio Headphones',149,'Audio'),('Travel Backpack',89,'Accessories'),('Desk Lamp',69,'Home'),('Mechanical Keyboard',129,'Tech')")
@app.route('/')
def index():
 with connect() as c:
  products=c.execute('SELECT * FROM products WHERE lower(name) LIKE ?',('%'+request.args.get('q','').lower()+'%',)).fetchall();return render_template('index.html',items=products)
@app.route('/cart/add/<int:item>',methods=['POST'])
def add(item):
 with connect() as c:
  if not c.execute('SELECT 1 FROM products WHERE id=?',(item,)).fetchone():abort(404)
 cart=session.get('cart',{});cart[str(item)]=cart.get(str(item),0)+1;session['cart']=cart
 return redirect(url_for('index'))
@app.route('/checkout',methods=['POST'])
@login_required
def checkout():
 cart=session.get('cart',{})
 with connect() as c:
  products=c.execute('SELECT * FROM products').fetchall()
  total=sum(p['price']*cart.get(str(p['id']),0) for p in products)
  if total:c.execute('INSERT INTO orders(user_id,items,total) VALUES(?,?,?)',(session['user'],str(cart),total))
 session.pop('cart',None);flash('Demo order recorded. No payment was processed.')
 return redirect(url_for('index'))

if __name__=='__main__':
 init_db()
 app.run(debug=os.getenv('FLASK_DEBUG')=='1')
