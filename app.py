import base64
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime,timedelta
import jugaad_data as jd
from jugaad_data.nse import stock_df
import matplotlib.pyplot as plt
import numpy as np
import time
import os
import sys


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

@app.route('/homepage')
def homepage():
    return render_template('homepage.html', username=session['username'])

@app.route('/analyze', methods=['GET','POST'])
def analyze():
    return render_template('analyze.html', username=session['username'])

@app.route('/compare', methods=['POST','GET'])
def compare():
    return render_template('compare.html', username=session['username'])

@app.route('/stockname',methods=['POST'])
def stockname():
    if request.method=='POST':
        stck=request.form['stockname']
        end_date=datetime.now().date()
        start_date=end_date-timedelta(days=365*0.2)
        df = stock_df(symbol=stck, from_date=start_date, to_date=end_date, series="EQ")
        df_array = df[['DATE', 'CLOSE']].to_numpy()
        plt.figure(figsize=(10, 6))
        plt.plot(df_array[:, 0], df_array[:, 1], label='Stock Price')
        plt.title(f'Stock Price for {stck}')
        plt.xlabel('date')
        plt.ylabel('Close Price')
        plt.legend()
        plt.grid(True)

        # Convert the plot to a base64-encoded image
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf-8')

        plt.close()
    # Render the template with the plot
        return render_template('stockanalyze.html', plot_url=plot_url)
    else:
        # Handle the case where the route is accessed with a GET request
        return render_template('stock_form.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
