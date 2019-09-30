import os
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)


# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # print("all_stock", all_stock)

    row = db.execute("SELECT DISTINCT symbol, stock_name,SUM(shares) , price, price*SUM(shares)from history WHERE user_id = :id GROUP BY symbol", id=session['user_id'])
    cash = db.execute("SELECT cash FROM users WHERE id=:id ", id= session['user_id'])
    cost = 0
    for val in row:
        cost+=val['price*SUM(shares)']
    total = cost + cash[0]['cash']
    print("cost", cost)
    print("total", total)

    return render_template("index.html", row= row, total = total, cash=cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == 'GET':
        return render_template("buy.html")


    elif request.method == 'POST':
        # print( type(symbol))
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Please enter a positive integer", 400)
                 
        # print(shares)
        if shares < 1 :
            return apology("Please enter a positive integer", 400)
        else:
            # get the symbol from the /buy form
            sym = request.form.get("symbol")

            # lookup the symbol to get the price
            quote = lookup(sym)
            
            if quote == None:
                return apology("This stock does not exist", 400)

            # print("%%%%%%%% symbol=",sym)
            price = quote['price']
            stock_name = quote['name']
            # print(stock_name)
            


            # get the user's session id and use it to select the user's balance in the users table
            user_id = session["user_id"] 
            cash_available = db.execute("SELECT cash FROM users WHERE id = :id", id=user_id)
            cash = cash_available[0]['cash']
            cost = shares * price
            # subtract the cost of the shares bought from the cash value to get the current balance
            if cost > cash:
                return apology("Insufficient Funds")

            balance = cash - cost
            #update the cash value in the users table
            db.execute("UPDATE users SET cash = :balance WHERE id = :user", balance=balance, user=user_id)
            time = datetime.datetime.now()
            # insert the transaction details into the history table 
            db.execute("INSERT INTO  history(transactions, cost, balance, user_id, date_time, symbol, shares, price, stock_name) VALUES('Bought',:cost, :balance, :user, :time, :sym , :shares, :price, :stock_name)", cost=cost, balance=balance, user=user_id, time= time, sym=symbol, shares=shares, price=price, stock_name=stock_name)
    return redirect("/history")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""

    username =  request.args.get("username")
    print(jsonify(False))

    # print(username)
    rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
    if len(rows) >0:
        return jsonify(False)

    return jsonify(True)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute('SELECT * FROM history WHERE user_id= :id', id = session['user_id'])
    # print(history)
    return render_template("history.html", history= history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session['username'] = rows[0]['username']

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == 'GET':
        return render_template('quote.html')
    
    elif request.method == "POST":
        sym = request.form.get("symbol")
        quote = lookup(sym)
        print("quote", quote)

        if quote == None:
            return apology("This stock does not exist", 400)
        return render_template("quoted.html", quote=quote)



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # get all input values and store in python variables
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # print(username, password, confirmation)
        # User reached route via POST (as by submitting a form via POST)
        if not username or username == "":
            return apology("must provide username", 400)

        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
        print("^^^^^the rows",len(rows))
        
        if len(rows)>0:
            print("Passwords not provided")
            return apology("User already exists", 400)
         # Ensure password was submitted
        elif not password :
            print("Passwords not provided")

            return apology("must provide password", 400)

        if password!=confirmation:  
            print("Passwords do not match", 400)
            return apology("Passwords do not match", 400)
        
        hashed_pwd = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        # Insert into the  database
        db.execute("INSERT INTO users (username, hash)  VALUES (:username, :hash)", username=username, hash=hashed_pwd)
        return redirect("/login")      

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == 'GET':
        user=session['user_id']
        symbols = db.execute('SELECT DISTINCT symbol FROM history where user_id = :user', user=user)
        # prices = db.execute('SELECT DISTINCT symbol FROM history where user_id = :user', user=user)
        
        # print(symbols)
        return render_template("sell.html", symbols=symbols)


    elif request.method == 'POST':
        symbol = request.form.get("symbol")
        # print("typeof", type(symbol))
        shares = int(request.form.get("shares"))
        # print("shares", shares)

        if shares < 1:
            return apology("Please enter a positive integer", 403)
        else:
            # get the symbol from the /buy form
            sym = request.form.get("symbol")
            # print("sym", sym)
            # print"######## symbol:", sym)
            # lookup the symbol to get the price
    
            print("Sym", sym)

            quote = lookup(sym)
            print("Quote", type(quote))
            # print("***********SHARES",shares)

            price = quote["price"]
            stock_name= quote["name"]

            # print("Price", amt)

            # get the user's session id and use it to select the user's balance in the users table
            user_id = session["user_id"] 
            cash_available = db.execute("SELECT cash FROM users WHERE id = :id", id=user_id)
            stmt = db.execute("SELECT SUM(shares) FROM history WHERE symbol=:symbol AND user_id=:id", symbol=symbol, id=session['user_id'])

            print("Available shares stmt", stmt)
            shares_avail = stmt[0]['SUM(shares)']
            cash = cash_available[0]['cash']


            if shares_avail < shares:
                return apology("Insufficient Stocks")
            cost = shares * price
            # Add the cost of the shares from the cash value to get the current balance
            balance = cash + cost
            time = datetime.datetime.now()
            # print(time)
            #update the cash value in the users table
            db.execute("UPDATE users SET cash = :balance WHERE id = :user", balance=balance, user=user_id)

            # insert the transaction details into the history table 
            db.execute("INSERT INTO  history(transactions, cost, balance, user_id, date_time, symbol, shares, price, stock_name) VALUES('Sold',:cost, :balance, :user, :time, :sym , :shares, :price, :stock_name)", cost=cost, balance=balance, user=user_id, time= time, sym=symbol, shares=(-shares), price=price, stock_name=stock_name)
            



    return redirect("/history")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
