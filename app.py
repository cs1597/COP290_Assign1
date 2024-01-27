import base64
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime,timedelta
import jugaad_data as jd
from jugaad_data.nse import stock_df,index_df
import matplotlib.pyplot as plt
import numpy as np
import time
import os
import sys
import plotly.express as px
import plotly.graph_objects as go
colors = [
                    'blue', 'red', 'green', 'purple', 'orange', 'brown', 'cyan', 'magenta', 'yellow', 'black',
                    'gray', 'pink', 'lightblue', 'lightcoral', 'lightgreen', 'lightgray', 'lightpink', 'lightyellow', 'darkblue', 'darkred',
                    'darkgreen', 'darkpurple', 'darkorange', 'darkbrown', 'darkcyan', 'darkmagenta', 'darkyellow', 'darkgray', 'lightcyan',
                    'lightmagenta', 'lightyellow', 'darkcyan', 'darkmagenta', 'darkyellow', 'lightcyan', 'lightmagenta', 'lightyellow',
                    'darkcyan', 'darkmagenta', 'darkyellow', 'lightcyan', 'lightmagenta', 'lightyellow', 'darkcyan', 'darkmagenta', 'darkyellow'
                ]
df_nifty50=pd.read_csv('ind_nifty50list.csv')

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
    
@app.route('/analyze_nifty', methods=['GET','POST'])
def analyze_nifty():
    if request.method=="POST":
        time_period = request.form['time_period']
        end_date = datetime.now().date()
        if time_period == '1W':
            start_date = end_date - timedelta(weeks=1)
        elif time_period == '1M':
            start_date = end_date - timedelta(weeks=4)
        elif time_period == '1Y':
            start_date = end_date - timedelta(weeks=52)
        elif time_period == '3Y':
            start_date = end_date - timedelta(weeks=3*52)
        elif time_period == '5Y':
            start_date = end_date - timedelta(weeks=5*52)
        else:
            start_date = end_date - timedelta(weeks=2*52)
        param=request.form["parameter"]
        df = index_df(symbol="NIFTY 50", from_date=start_date, to_date=end_date)
        df.sort_values(by=['HistoricalDate'],inplace=True)
        trace1=go.Scatter(x=df['HistoricalDate'], y=df[param], mode='lines', name="NIFTY 50", line=dict(color='blue'))
        layout=go.Layout(
            title=f'Stock Prices for NIFTY50',
            xaxis_title='Date',
            yaxis_title=param,
            legend=dict(x=0, y=1, traceorder='normal'),
            xaxis=dict(
                type='date',  
                tickformat='%Y-%m-%d', 
            ),
            width=1500,
            height=550
        )
        fig=go.Figure(data=trace1,layout=layout)
        plot_html=fig.to_html(full_html=False)
        return render_template('analyze_nifty.html',plot_html=plot_html)
    else:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365 * 2)
        df = index_df(symbol="NIFTY 50", from_date=start_date, to_date=end_date)
        df.sort_values(by=['HistoricalDate'],inplace=True)
        trace1=go.Scatter(x=df['HistoricalDate'], y=df['CLOSE'], mode='lines', name="NIFTY 50", line=dict(color='blue'))
        layout=go.Layout(
                title=f'Index price for NIFTY 50',
                xaxis_title='Date',
                yaxis_title='Close Price',
                legend=dict(x=0, y=1, traceorder='normal'),
                xaxis=dict(
                    type='date',  
                    tickformat='%Y-%m-%d', 
                ),
                width=1500,
                height=550
            )
        fig=go.Figure(data=trace1,layout=layout)
        plot_html=fig.to_html(full_html=False)
        return render_template('analyze_nifty.html',plot_html=plot_html)

@app.route('/stock_graph', methods=['GET', 'POST'])
def stock_graph():
    if request.method == 'POST':
        stck=request.form['stock']
        session["selected_stock"]=stck
        time_period = request.form['time_period']
        end_date = datetime.now().date()
        if time_period == '1W':
            start_date = end_date - timedelta(weeks=1)
        elif time_period == '1M':
            start_date = end_date - timedelta(weeks=4)
        elif time_period == '1Y':
            start_date = end_date - timedelta(weeks=52)
        elif time_period == '3Y':
            start_date = end_date - timedelta(weeks=3*52)
        elif time_period == '5Y':
            start_date = end_date - timedelta(weeks=5*52)
        else:
            start_date = end_date - timedelta(weeks=2*52)
        param=request.form["parameter"]
        df = stock_df(symbol=stck, from_date=start_date, to_date=end_date, series="EQ")
        trace1=go.Scatter(x=df['DATE'], y=df[param], mode='lines', name=stck, line=dict(color='blue'))
        layout=go.Layout(
            title=f'Stock Prices for {stck}',
            xaxis_title='Date',
            yaxis_title=param,
            legend=dict(x=0, y=1, traceorder='normal'),
            xaxis=dict(
                type='date',  
                tickformat='%Y-%m-%d', 
            ),
            width=1500,
            height=550
        )
        fig=go.Figure(data=trace1,layout=layout)
        plot_html=fig.to_html(full_html=False)
        return render_template('plot_stock.html',plot_html=plot_html)
    else:
        stck="SBIN"
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=2*52) 
        param="CLOSE"
        df = stock_df(symbol=stck, from_date=start_date, to_date=end_date, series="EQ")
        trace1=go.Scatter(x=df['DATE'], y=df[param], mode='lines', name=stck, line=dict(color='blue'))
        layout=go.Layout(
            title=f'Stock Prices for {stck}',
            xaxis_title='Date',
            yaxis_title='Close Price',
            legend=dict(x=0, y=1, traceorder='normal'),
            xaxis=dict(
                type='date',  
                tickformat='%Y-%m-%d', 
            ),
            width=1500,
            height=550
        )
        fig=go.Figure(data=trace1,layout=layout)
        plot_html=fig.to_html(full_html=False)
        return render_template('plot_stock.html') 

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if request.method == 'POST':
        session.pop('selected_stocks', None)
        symbols = request.form['stock'].split(',')
        session['selected_stocks'] = symbols
        time_period = request.form['time_period']
        end_date = datetime.now().date()
        if time_period == '1W':
            start_date = end_date - timedelta(weeks=1)
        elif time_period == '1M':
            start_date = end_date - timedelta(weeks=4)
        elif time_period == '1Y':
            start_date = end_date - timedelta(weeks=52)
        elif time_period == '3Y':
            start_date = end_date - timedelta(weeks=3*52)
        elif time_period == '5Y':
            start_date = end_date - timedelta(weeks=5*52)
        else:
            start_date = end_date - timedelta(weeks=2*52)
        plots = []
        param=request.form["parameter"]

        for i, stck in enumerate(symbols):
            stck = stck.strip()
            df = stock_df(symbol=stck, from_date=start_date, to_date=end_date, series="EQ")
            trace = go.Scatter(x=df['DATE'], y=df[param], mode='lines', name=stck, line=dict(color=colors[i]))
            plots.append(trace)

        layout = go.Layout(
            title=f'Stock Prices for {", ".join(symbols)}',
            xaxis_title='Date',
            yaxis_title=param,
            legend=dict(x=0, y=1, traceorder='normal'),
            xaxis=dict(
                type='date',
                tickformat='%Y-%m-%d',
            ),
            width=1500,
            height=550
        )

        fig = go.Figure(data=plots, layout=layout)
        plot_html = fig.to_html(full_html=False)
        return render_template('compare.html', plot_html=plot_html)
    else:
        stck="SBIN"
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=2*52) 
        param="CLOSE"
        df = stock_df(symbol=stck, from_date=start_date, to_date=end_date, series="EQ")
        trace1=go.Scatter(x=df['DATE'], y=df[param], mode='lines', name=stck, line=dict(color='blue'))
        layout=go.Layout(
            title=f'Stock Prices for {stck}',
            xaxis_title='Date',
            yaxis_title='Close Price',
            legend=dict(x=0, y=1, traceorder='normal'),
            xaxis=dict(
                type='date',  
                tickformat='%Y-%m-%d', 
            ),
            width=1500,
            height=550
        )
        fig=go.Figure(data=trace1,layout=layout)
        plot_html=fig.to_html(full_html=False)
        return render_template('compare.html')
    
@app.route('/filter_stocks', methods=['GET', 'POST'])
def filter_stocks():
    if request.method=="POST":
        plots=[]
        lower_bound=request.form["close_lower_bound"]
        upper_bound=request.form["close_upper_bound"]
        if lower_bound:
            lower_bound=int(lower_bound)
            upper_bound=int(upper_bound)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(weeks=1)
            filtered_list={}
            for symbol in df_nifty50['Symbol']:
                df_stock = stock_df(symbol=symbol, from_date=start_date, to_date=end_date, series="EQ")
                if df_stock['CLOSE'].iloc[0]>=lower_bound and df_stock['CLOSE'].iloc[0]<=upper_bound:
                    filtered_list[symbol]=df_stock
            fig = go.Figure()
            for symbol, filtered_df in filtered_list.items():
                trace=(go.Bar(
                    x=[symbol], 
                    y=[filtered_df['CLOSE'].iloc[0]],  
                    name=symbol,
                    text=f"{symbol}: {filtered_df['CLOSE'].iloc[0]}", 
                ))
                plots.append(trace)
            layout=go.Layout(
                title='Close Prices for Filtered Symbols',
                xaxis_title='Symbol',
                yaxis_title='Close Price',
                barmode='group', 
                showlegend=True,
                width=1500,
                height=550
            )
        else:
            lower_bound=int(request.form["value_lower_bound"])
            upper_bound=int(request.form["value_upper_bound"])
            end_date = datetime.now().date()
            start_date = end_date - timedelta(weeks=1)
            filtered_list={}
            for symbol in df_nifty50['Symbol']:
                df_stock = stock_df(symbol=symbol, from_date=start_date, to_date=end_date, series="EQ")
                if df_stock['VALUE'].iloc[0]>=lower_bound and df_stock['VALUE'].iloc[0]<=upper_bound:
                    filtered_list[symbol]=df_stock
            fig = go.Figure()
            for symbol, filtered_df in filtered_list.items():
                trace=(go.Bar(
                    x=[symbol], 
                    y=[filtered_df['VALUE'].iloc[0]],  
                    name=symbol,
                    text=f"{symbol}: {filtered_df['VALUE'].iloc[0]}", 
                ))
                plots.append(trace)
            layout=go.Layout(
                title='Close Prices for Filtered Symbols',
                xaxis_title='Symbol',
                yaxis_title='Close Price',
                barmode='group', 
                showlegend=True,
                width=1500,
                height=550
            )
        fig = go.Figure(data=plots, layout=layout)
        plot_html=fig.to_html(full_html=False)
        return render_template('filter_stocks.html',plot_html=plot_html)
    else:
        return render_template('filter_stocks.html')
 
    
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
