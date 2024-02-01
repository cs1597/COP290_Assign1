from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime,timedelta
import jugaad_data as jd
from jugaad_data.nse import stock_df,index_df,NSELive
import matplotlib.pyplot as plt
import requests
import plotly.express as px
import plotly.graph_objects as go
from flask_migrate import Migrate
import csv
from flask_caching import Cache

nse_live=NSELive()
colors = [
                'blue', 'red', 'green', 'purple', 'orange', 'brown', 'cyan', 'magenta', 'yellow', 'black',
                'gray', 'pink', 'lightblue', 'lightcoral', 'lightgreen', 'lightgray', 'lightpink', 'lightyellow', 'darkblue', 'darkred',
                'darkgreen', 'darkpurple', 'darkorange', 'darkbrown', 'darkcyan', 'darkmagenta', 'darkyellow', 'darkgray', 'lightcyan',
                'lightmagenta', 'lightyellow', 'darkcyan', 'darkmagenta', 'darkyellow', 'lightcyan', 'lightmagenta', 'lightyellow',
                'darkcyan', 'darkmagenta', 'darkyellow', 'lightcyan', 'lightmagenta', 'lightyellow', 'darkcyan', 'darkmagenta', 'darkyellow'
            ]
df_nifty50=pd.read_csv('ind_nifty50list.csv')
news_api_key='650949e403754ffaacf906723c33b226'

app = Flask(__name__)
app.secret_key = 'your_secret_key' 
app.config['CACHE_TYPE'] = 'simple'  
app.config['CACHE_DEFAULT_TIMEOUT'] = 300 
cache = Cache(app)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name= db.Column(db.String(100), nullable=True)
    mobile_number=db.Column(db.String(10),nullable=True)
    email=db.Column(db.String(100),nullable=True)
    balance = db.Column(db.Integer,nullable=True)
    holdings=db.Column(db.String(255),nullable=True)
    watchlist=db.Column(db.Text,nullable=True)
    
    def write_dictionary_to_csv(self,username, your_dictionary):
        csv_file_name = f"{username}_file.csv"
        with open(csv_file_name, "w", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            for key, value in your_dictionary.items():
                csv_writer.writerow([key, value])


    def read_csv_to_dictionary(self,username):
        csv_file_name = f"{username}_file.csv"
        your_dictionary = {}
        with open(csv_file_name, "r") as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                key, value = row
                your_dictionary[key] = int(value)  # Assuming values are integers
        return your_dictionary

    #to write watchlist elements stored as a list to the csv file 
    def write_stock_symbols_to_csv(self,stock_symbols, username):
        csv_file_name=f"{username}_watchlist.csv"
        with open(csv_file_name, "w", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            for symbol in stock_symbols:
                csv_writer.writerow([symbol])
    
    def read_stock_symbols_from_csv(self,username):
        csv_file_name=f"{username}_watchlist.csv"
        stock_symbols = []
        with open(csv_file_name, "r") as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                stock_symbols.append(row[0])
        return stock_symbols

# Initialize Database within Application Context
with app.app_context():
    db.create_all()
migrate = Migrate(app,db)

#main page
@app.route('/')
def index():
    return render_template('login.html')

#registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password_hash=hashed_password, balance=200000)
        open(username+"_file.csv", 'w', newline='')
        open(username+"_watchlist.csv", 'w', newline='')
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('index'))

    return render_template('register.html')

#login page
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('homepage'))
    else:
        flash('Invalid username or password')
        return redirect(url_for('index'))

#homepage containing news, top gainers, losers and nifty plot 
@app.route('/homepage', methods=['GET','POST'])
def homepage():
    if request.method=="GET":
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365)
        df = index_df(symbol="NIFTY 50", from_date=start_date, to_date=end_date)
        df.sort_values(by=['HistoricalDate'],inplace=True)
        trace_candlestick = go.Candlestick(x=df['HistoricalDate'],open=df['OPEN'],high=df['HIGH'],low=df['LOW'],close=df['CLOSE'],)
        layout_candlestick = go.Layout(
            title=f'NIFTY50',
            xaxis_title='Date',
            yaxis_title='Stock Price',
            plot_bgcolor='rgb(3, 2, 21)',
            paper_bgcolor='rgb(3, 2, 21)',
            font=dict(color='#299ae1',family='Roboto,sans-serif',size=20),
            legend=dict(x=0, y=1, traceorder='normal'),
            xaxis=dict(
                type='date',
                tickformat='%Y-%m-%d',
                gridcolor= '#299ae1',),
            yaxis=dict(gridcolor='#299ae1',),
            width=1030,
            height=600
        )
        fig= go.Figure(data=trace_candlestick, layout=layout_candlestick)
        plot_html=fig.to_html(full_html=False)
        keywords = ['NSE','BSE','stock','share']
        articles=[]
        #fetching latest news 
        for keyword in keywords:
            news_api_url = f'https://newsapi.org/v2/top-headlines?q={keyword}&country=in&apiKey={news_api_key}'
            response = requests.get(news_api_url)
            data = response.json()
            article = data.get('articles', [])
            articles=articles+article
        end_date = datetime.now().date()
        gainz=[]
        start_date = end_date - timedelta(weeks=1)
        for symbol in df_nifty50['Symbol']:
            df_stock = stock_df(symbol=symbol, from_date=start_date, to_date=end_date, series="EQ")
            delta=round((df_stock['CLOSE'].iloc[0]-df_stock['CLOSE'].iloc[1])*100/df_stock['CLOSE'].iloc[1],2)
            gainz.append([delta,symbol])
        sorted(gainz)
        increase = sorted(gainz, key=lambda x: x[0], reverse=True)
        decrease = sorted(gainz, key=lambda x: x[0])
        increase = increase[:4] 
        decrease = decrease[:4] 
        return render_template('homepage.html', username=session['username'],increase=increase,decrease=decrease,top_news=articles[:3], plot_html=plot_html)

#analysing NIFTY50    
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
        if param=='Candlestick':
            df = index_df(symbol="NIFTY 50", from_date=start_date, to_date=end_date)
            df.sort_values(by=['HistoricalDate'],inplace=True)
            trace_candlestick = go.Candlestick(x=df['HistoricalDate'],open=df['OPEN'],high=df['HIGH'],low=df['LOW'],close=df['CLOSE'],)
            layout_candlestick = go.Layout(
                title=f'NIFTY50',
                xaxis_title='Date',
                yaxis_title='Stock Price',
                plot_bgcolor='rgb(3, 2, 21)',
                paper_bgcolor='rgb(3, 2, 21)',
                font=dict(color='#299ae1',family='Roboto,sans-serif',size=20),
                legend=dict(x=0, y=1, traceorder='normal'),
                xaxis=dict(
                    type='date',
                    tickformat='%Y-%m-%d',
                    gridcolor= '#299ae1',
                ),
                yaxis=dict(
                    gridcolor='#299ae1',
                ),
                width=1500,
                height=700
            )
            fig= go.Figure(data=trace_candlestick, layout=layout_candlestick)
        else:
            df = index_df(symbol="NIFTY 50", from_date=start_date, to_date=end_date)
            df.sort_values(by=['HistoricalDate'],inplace=True)
            trace1=go.Scatter(x=df['HistoricalDate'], y=df[param], mode='lines', name="NIFTY 50", line=dict(color='blue'))
            layout=go.Layout(
                title=f'Stock Prices for NIFTY50',
                xaxis_title='Date',
                yaxis_title=param,
                legend=dict(x=0, y=1, traceorder='normal'),
                plot_bgcolor='rgb(3, 2, 21)',
                paper_bgcolor='rgb(3, 2, 21)',
                font=dict(color='#299ae1',family='Roboto,sans-serif',size=20),
                xaxis=dict(
                    type='date',
                    tickformat='%Y-%m-%d',
                    gridcolor= '#299ae1',),
                yaxis=dict(gridcolor='#299ae1',),
                width=1500,
                height=700)
            fig=go.Figure(data=trace1,layout=layout)
        plot_html=fig.to_html(full_html=False)
        return render_template('analyze_nifty.html',plot_html=plot_html)
    else:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365*2)
        df = index_df(symbol="NIFTY 50", from_date=start_date, to_date=end_date)
        df.sort_values(by=['HistoricalDate'],inplace=True)
        trace_candlestick = go.Candlestick(x=df['HistoricalDate'],open=df['OPEN'],high=df['HIGH'],low=df['LOW'],close=df['CLOSE'],)
        layout_candlestick = go.Layout(
            title=f'NIFTY50',
            xaxis_title='Date',
            yaxis_title='Stock Price',
            plot_bgcolor='rgb(3, 2, 21)',
            paper_bgcolor='rgb(3, 2, 21)',
            font=dict(color='#299ae1',family='Roboto,sans-serif',size=20),
            legend=dict(x=0, y=1, traceorder='normal'),
            xaxis=dict(
                type='date',
                tickformat='%Y-%m-%d',
                gridcolor= '#299ae1',
            ),
            yaxis=dict(
                gridcolor='#299ae1',
            ),
            width=1500,
            height=700
        )
        fig= go.Figure(data=trace_candlestick, layout=layout_candlestick)
        plot_html=fig.to_html(full_html=False)
        return render_template('analyze_nifty.html', plot_html=plot_html)

#Analysing a single stock based on input parameters
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
        df = stock_df(symbol=stck, from_date=start_date, to_date=end_date, series="EQ")
        param=request.form["parameter"]
        if param!='Candlestick':
            trace1=go.Scatter(x=df['DATE'], y=df[param], mode='lines', name=stck, line=dict(color='blue'))
            layout=go.Layout(
                title=f'Stock Prices for {stck}',
                xaxis_title='Date',
                yaxis_title=param,
                plot_bgcolor='rgb(3, 2, 21)',
                paper_bgcolor='rgb(3, 2, 21)',
                font=dict(color='#299ae1',family='Roboto,sans-serif',size=20),
                legend=dict(x=0, y=1, traceorder='normal'),
                xaxis=dict(
                    type='date',
                    tickformat='%Y-%m-%d',
                    gridcolor= '#299ae1',
                ),
                yaxis=dict(
                    gridcolor='#299ae1',
                ),
                width=1500,
                height=700
            )
            fig=go.Figure(data=trace1,layout=layout)
        else:
            trace_candlestick = go.Candlestick(x=df['DATE'],
                                            open=df['OPEN'],
                                            high=df['HIGH'],
                                            low=df['LOW'],
                                            close=df['CLOSE'],
                                            name=stck)
            layout_candlestick = go.Layout(
                title=f'Candlestick Chart for {stck}',
                xaxis_title='Date',
                yaxis_title='Stock Price',
                plot_bgcolor='rgb(3, 2, 21)',
                paper_bgcolor='rgb(3, 2, 21)',
                font=dict(color='#299ae1',family='Roboto,sans-serif',size=20),
                legend=dict(x=0, y=1, traceorder='normal'),
                xaxis=dict(
                    type='date',
                    tickformat='%Y-%m-%d',
                    gridcolor= '#299ae1',
                ),
                yaxis=dict(
                    gridcolor='#299ae1',
                ),
                width=1500,
                height=700
            )
            fig= go.Figure(data=trace_candlestick, layout=layout_candlestick)
        plot_html=fig.to_html(full_html=False)
        return render_template('plot_stock.html',plot_html=plot_html, current_stock=stck)
    else:
        stck="SBIN"
        if 'current_stock' in request.args:
            user = User.query.filter_by(username=session['username']).first()
            stock_symbol=request.args['current_stock']
            cur_watchlist=user.read_stock_symbols_from_csv(session['username'])
            if stock_symbol not in cur_watchlist:
                cur_watchlist.append(stock_symbol)
            user.write_stock_symbols_to_csv(cur_watchlist,session['username'])
            stck=stock_symbol
        if 'selected_symbol' in request.args:
            stck=request.args['selected_symbol']
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=52) 
        df = stock_df(symbol=stck, from_date=start_date, to_date=end_date, series="EQ")
        trace_candlestick = go.Candlestick(x=df['DATE'],
                                           open=df['OPEN'],
                                           high=df['HIGH'],
                                           low=df['LOW'],
                                           close=df['CLOSE'],
                                           name=stck)
        layout_candlestick = go.Layout(
            title=f'Candlestick Chart for {stck}',
            xaxis_title='Date',
            yaxis_title='Stock Price',
            plot_bgcolor='rgb(3, 2, 21)',
            paper_bgcolor='rgb(3, 2, 21)',
            font=dict(color='#299ae1',family='Roboto,sans-serif',size=20),
            legend=dict(x=0, y=1, traceorder='normal'),
            xaxis=dict(
                type='date',
                tickformat='%Y-%m-%d',
                gridcolor= '#299ae1',
            ),
            yaxis=dict(
                gridcolor='#299ae1',
            ),
            width=1500,
            height=700
        )
        fig_candlestick = go.Figure(data=trace_candlestick, layout=layout_candlestick)
        plot_html=fig_candlestick.to_html(full_html=False)
        user = User.query.filter_by(username=session['username']).first()
        return render_template('plot_stock.html',plot_html=plot_html, current_stock=stck) 

#Comparing multiple stocks in a single graph based on multiple parameters
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
            plot_bgcolor='rgb(3, 2, 21)',
            paper_bgcolor='rgb(3, 2, 21)',
            font=dict(color='#299ae1',family='Roboto,sans-serif',size=20),
            xaxis=dict(
                type='date',
                tickformat='%Y-%m-%d',
                gridcolor= '#299ae1',
            ),
            yaxis=dict(
                gridcolor='#299ae1',
            ),
            width=1500,
            height=700
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
            plot_bgcolor='rgb(3, 2, 21)',
            paper_bgcolor='rgb(3, 2, 21)',
            font=dict(color='#299ae1',family='Roboto,sans-serif',size=20),
            legend=dict(x=0, y=1, traceorder='normal'),
            xaxis=dict(
                type='date',
                tickformat='%Y-%m-%d',
                gridcolor= '#299ae1',
            ),
            yaxis=dict(
                gridcolor='#299ae1',
            ),
            width=1500,
            height=700
        )
        fig=go.Figure(data=trace1,layout=layout)
        plot_html=fig.to_html(full_html=False)
        return render_template('compare.html')

#Filtering stocks based on multiple parameters 
@app.route('/filter_stocks', methods=['GET', 'POST'])
def filter_stocks():
    if request.method=="POST":
        lower_bound=request.form["lower_bound"]
        upper_bound=request.form["upper_bound"]
        lower_bound=int(lower_bound)
        upper_bound=int(upper_bound)
        param=request.form['parameter']
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=1)
        filtered_list={}
        for symbol in df_nifty50['Symbol']:
            df_stock = stock_df(symbol=symbol, from_date=start_date, to_date=end_date, series="EQ")
            if df_stock[param].iloc[0]>=lower_bound and df_stock[param].iloc[0]<=upper_bound:
                filtered_list[symbol]=df_stock[param].iloc[0]
        return render_template('filter_stocks.html',filtered_list=filtered_list, param=param)
    else:
        filtered_list={}
        return render_template('filter_stocks.html',filtered_list=filtered_list)

#caching for fast retrieval of data  
@app.route('/buying_market', methods=['GET', 'POST'])
@cache.cached(timeout=300)
def buying_market():
    if request.method=="POST":
        lower_bound=request.form["lower_bound"]
        upper_bound=request.form["upper_bound"]
        lower_bound=int(lower_bound)
        upper_bound=int(upper_bound)
        param=request.form['parameter']
        end_date = datetime.now().date()
        username=session['username']
        user = User.query.filter_by(username=username).first()
        start_date = end_date - timedelta(weeks=1)
        filtered_list={}
        for symbol in df_nifty50['Symbol']:
            df_stock = stock_df(symbol=symbol, from_date=start_date, to_date=end_date, series="EQ")
            if df_stock[param].iloc[0]>=lower_bound and df_stock[param].iloc[0]<=upper_bound:
                filtered_list[symbol]=df_stock[param].iloc[0]
        return render_template('buying_market.html',filtered_list=filtered_list, param=param)
    else: 
        filtered_list={}
        for symbol in df_nifty50['Symbol']:
            q=nse_live.stock_quote(symbol)
            filtered_list[symbol]=q['priceInfo']['lastPrice']
        return render_template('buying_market.html',filtered_list=filtered_list)

#platform for selling stocks
@app.route('/selling_market',methods=['GET'])
def selling_market():
    username=session['username']
    user = User.query.filter_by(username=username).first()
    balance=user.balance
    holdings=user.read_csv_to_dictionary(session['username'])
    return render_template('selling_market.html',holdings=holdings,balance=balance)

#interface for selling stocks
@app.route('/sell_stocks',methods=['POST','GET'])
def sell_stocks():
    if request.method=="GET":
        symbol=request.args['selected_symbol'].strip()
        q=nse_live.stock_quote(symbol.strip())
        last_price=q['priceInfo']['lastPrice']
        return render_template('sell_stocks.html',last_price=last_price, stock_symbol=symbol)
    else:
        stock_no=int(request.form["stock_no"])
        symbol=request.form['selected_symbol'].strip()
        q=nse_live.stock_quote(symbol.strip())
        last_price=q['priceInfo']['lastPrice']
        user = User.query.filter_by(username=session['username']).first()
        current_balance=user.balance
        holdings=user.read_csv_to_dictionary(session['username'])
        if(holdings[symbol]>=stock_no):
            valid=True
            holdings[symbol]-=stock_no
            if(holdings[symbol]==0):
                del holdings[symbol]
            user.write_dictionary_to_csv(session['username'],holdings)
            user.balance=current_balance+int(stock_no)*last_price
        else:
            valid=False
        # condition to add whether can sell these many stocks or not, if yes increase balance and remove from holdings also some indicator like valid

        db.session.commit()
        return render_template('sell_transaction.html',valid=valid,balance=user.balance)
 

#interface to buy a particular stock   
@app.route('/buy_stocks',methods=['POST','GET'])
def buy_stocks():
    if request.method=="GET":
        last_price=request.args['last_price']
        username=session['username']
        user = User.query.filter_by(username=username).first()
        return render_template('buy_stocks.html',stock_symbol=request.args['selected_symbol'],last_price=last_price,balance=user.balance)
    else:
        stock_no=int(request.form["stock_no"].strip())
        symbol=request.form["stock_symbol"].strip()
        q=nse_live.stock_quote(symbol)
        last_price=q['priceInfo']['lastPrice']
        user = User.query.filter_by(username=session['username']).first()
        current_balance=user.balance
        if(int(stock_no)*last_price<=current_balance):
            user.balance=current_balance-int(stock_no)*last_price
            holdings=user.read_csv_to_dictionary(session['username'])
            # print(holdings)
            if(symbol in holdings):
                holdings[symbol]+=int(stock_no)
            else:
                holdings[symbol]=int(stock_no)
            # If the transaction is succesfull we need to update the holdings of the user 
            user.write_dictionary_to_csv(session['username'],holdings)
            valid=True
        else:
            valid=False
        db.session.commit()
        return render_template('transaction.html',valid=valid,balance=user.balance)

#about the website   
@app.route('/about')
def about():
    return render_template('about.html')

#user info page
@app.route('/user_info')
def user_info():
    end_date=datetime.now().date()
    start_date=end_date-timedelta(weeks=1)
    user = User.query.filter_by(username=session['username']).first()
    watchlist=user.read_stock_symbols_from_csv(session['username'])
    stock_rows=[]
    for symbol in watchlist:
        df_stock= stock_df(symbol=symbol, from_date=start_date, to_date=end_date, series="EQ")
        stock_rows.append(df_stock.iloc[0])
    print(stock_rows)
    return render_template('user_info.html', username=session['username'], mobile_number=user.mobile_number,full_name=user.full_name,email=user.email,watchlist=stock_rows)

#change user info
@app.route('/change_user_info', methods=["GET","POST"])
def change_user_info():
    if request.method == 'POST':
        username = request.form['username']
        full_name=request.form['full_name']
        email=request.form['email']
        mobile_number=request.form['mobile_number']
        user = User.query.filter_by(username=session['username']).first()
        user.username=username
        user.full_name=full_name
        user.email=email
        user.mobile_number=mobile_number
        db.session.commit()
        session['username']=username
        flash('Details Updated Succesfully')
        return redirect(url_for('user_info'))
    
    return render_template('change_user_info.html',username=session['username']) 
    
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
