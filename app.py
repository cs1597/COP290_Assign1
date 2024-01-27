from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from jugaad_data.nse import stock_df
from datetime import timedelta


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

# Initialize Database within Application Context
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid username or password')
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('welcome.html', username=session['username'])
    else:
        return redirect(url_for('index'))

# should we take from the user that for last how much time do they want the data to be seen?
def get_stock_data(symbol,time_scale):
    # end_date=pd.to_datetime('today')
    # start_date=end_date-pd.DateOffset(years=years)
    # data=stock_df(symbol=symbol,from_date=start_date.date(),to_date=end_date.date(),series="EQ")
    # return data[['DATE','OPEN','CLOSE','HIGH','LOW','LTP','VOLUME','VALUE','NO OF TRADES']]
    end_date=pd.to_datetime('today')
    if time_scale=="Daily":
        start_date=end_date-timedelta(days=365)
        interval='1D'
    elif time_scale=="Weekly":
        start_date=end_date-timedelta(weeks=52*5)
        interval='1W'
    elif time_scale=="Monthly":
        start_date=end_date-timedelta(weeks=52*20)
        interval='1M'
    elif time_scale=='yearly':
        start_date =end_date-timedelta(weeks=52*20)
        interval='1Y'
    data=stock_df(symbol=symbol,from_date=start_date.date(),to_date=end_date.date(),series="EQ",interval=interval)
    return data[['DATE','CLOSE']]


@app.route('/single_stock_graphs',methods=['POST','GET'])
def single_stock_graphs():
    stock_list=['ADANIENT','CIPLA','ITC','LT','ONGC','SBIN']
    print("Hello1")
    if request.method=="POST":
        selected_stock=request.form.get('selected_stock')
        selected_time_scale=request.form.get('time_scale')
        print("Helloo")
        stock_data=get_stock_data(selected_stock,selected_time_scale)
        print("Hello")
        dates=stock_data['DATE'].to_list()
        prices=stock_data['CLOSE'].to_list()
        return jsonify({'dates': dates,'prices':prices})
    return render_template('analyse_stocks.html',stock_symbols=stock_list)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)