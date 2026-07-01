from flask import Flask, request, jsonify, render_template_string, redirect, session
import os 
import requests 
import base64
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lensconnectdevkey123")

# ===== M-PESA SANDBOX CONFIG =====
CONSUMER_KEY = 'LeGawPo7b4x93kIGli7D8AIAr5LAWT9cHDtF58YyxqFtZ09f'
CONSUMER_SECRET = 'u5jkHpE4epBHu6nRZFzX0b3keVGTCqR9upjybehiX0md8GOYkLanq1R0Vh2OOHAT'
BUSINESS_SHORT_CODE = '174379' 
PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
CALLBACK_URL = 'https://lensconnect-x1uh.onrender.com/mpesa/confirmation'

def get_access_token():
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(api_url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    try: return r.json()['access_token']
    except: return None

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'lensconnect.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    balance = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    amount = db.Column(db.Float)
    bundle_name = db.Column(db.String(50))
    mpesa_code = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default="PAID")

with app.app_context(): db.create_all()

PRICES = {
    19: "1GB 1HR", 20: "250MB 24HRS", 49: "350MB 7DAYS", 50: "1.5GB 3HRS", 
    55: "1.25GB TILL MIDNIGHT", 99: "1GB 24HRS", 300: "2.5GB 7DAYS", 700: "6GB 7DAYS",
    23: "1GB 1HR TUNUKIWA", 51: "1.5GB 3HRS TUNUKIWA", 110: "2GB 24HRS TUNUKIWA",
    22: "43MINS 3HRS", 52: "50MINS TILL MID", 5: "20SMS 24HRS", 
    10: "200SMS 24HRS", 30: "1000SMS 7DAYS", 101: "1500SMS 30DAYS",
}

def process_bundle(phone, amount, mpesa_code):
    bundle = PRICES.get(amount, "UNKNOWN_BUNDLE")
    print(f"SIMULATED: Sending {bundle} to {phone}. Code: {mpesa_code}")
    txn = Transaction.query.filter_by(mpesa_code=mpesa_code).first()
    if txn:
        txn.status = "FULFILLED"
        db.session.commit()

AI_INSIGHTS = {"hot_bundle": "1GB 24HRS","trend_pct": 42,"forecast": 1240.50,"alert": "Tunukiwa 2GB now Ksh 99 ↓"}

def page(content_html, show_nav=False, nav='home'):
    nav_html = ""
    if show_nav:
        nav_html = f"""
        <nav class="fixed bottom-4 left-1/2 -translate-x-1/2 w-[95%] max-w-md bg-slate-800/60 backdrop-blur-xl border-slate-700 rounded-2xl flex justify-around py-3 shadow-2xl">
            <a href="/dashboard" class="flex flex-col items-center {'text-emerald-400' if nav=='home' else 'text-slate-400'}"><i data-lucide="home" class="w-6 h-6"></i><span class="text-xs">Home</span></a>
            <a href="/bundles" class="flex flex-col items-center {'text-emerald-400' if nav=='bundles' else 'text-slate-400'}"><i data-lucide="package" class="w-6 h-6"></i><span class="text-xs">Bundles</span></a>
            <a href="/ai-insights" class="flex flex-col items-center {'text-emerald-400' if nav=='ai' else 'text-slate-400'}"><i data-lucide="zap" class="w-6 h-6"></i><span class="text-xs">AI</span></a>
            <a href="#" class="flex flex-col items-center text-slate-400"><i data-lucide="user" class="w-6 h-6"></i><span class="text-xs">Account</span></a>
        </nav>
        <script>lucide.createIcons();</script>
        """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <title>LensConnect Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/lucide@latest"></script>
        <style> body {{ font-family: 'Inter', sans-serif; background-color: #0F172A; }} </style>
    </head>
    <body class="pb-24 text-slate-200">
        <div class="max-w-md mx-auto min-h-screen relative">
            {content_html}
        </div>
        {nav_html}
    </body>
    </html>
    """

@app.route('/')
def home(): return redirect('/signup')
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        if User.query.filter_by(email=email).first(): return page("<div class='p-8'>Email exists. <a href='/login' class='text-emerald-400'>Login</a></div>", False)
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user); db.session.commit()
        session['user_id'] = user.id
        return redirect('/dashboard')
    content = """
    <div class="p-8 pt-16">
        <h1 class="text-3xl font-bold">LensConnect</h1>
        <p class="text-slate-400 mb-8">Buy Data, SMS, Minutes</p>
        <form method="post" class="space-y-4">
            <input name="email" type="email" placeholder="Email" required class="w-full px-4 py-3 bg-slate-800 border-slate-700 rounded-xl">
            <input name="password" type="password" placeholder="Password" required class="w-full px-4 py-3 bg-slate-800 border-slate-700 rounded-xl">
            <button class="w-full py-3 font-bold text-white bg-emerald-600 rounded-xl hover:bg-emerald-700">Signup</button>
        </form>
        <p class="text-sm text-center mt-4">Have an account? <a href="/login" class="text-emerald-400 font-semibold">Login</a></p>
    </div>
    """
    return page(content, False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect('/dashboard')
        return page("<div class='p-8'>Invalid login. <a href='/login' class='text-emerald-400'>Try again</a></div>", False)
    content = """
    <div class="p-8 pt-16">
        <h1 class="text-3xl font-bold">LensConnect</h1>
        <p class="text-slate-400 mb-8">Buy Data, SMS, Minutes</p>
        <form method="post" class="space-y-4">
            <input name="email" type="email" placeholder="Email" required class="w-full px-4 py-3 bg-slate-800 border-slate-700 rounded-xl">
            <input name="password" type="password" placeholder="Password" required class="w-full px-4 py-3 bg-slate-800 border-slate-700 rounded-xl">
            <button class="w-full py-3 font-bold text-white bg-emerald-600 rounded-xl hover:bg-emerald-700">Login</button>
        </form>
        <p class="text-sm text-center mt-4">No account? <a href="/signup" class="text-emerald-400 font-semibold">Signup</a></p>
    </div>
    """
    return page(content, False)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/login')
    user = User.query.get(session['user_id'])
    content = f"""
    <div class="p-4">
        <div class="flex justify-between items-center mb-4">
            <p class="text-lg font-semibold">Hello {user.email.split('@')[0]} 👋</p>
            <a href="/logout"><i data-lucide="log-out" class="w-6 h-6 text-slate-400"></i></a>
        </div>
        <div class="bg-slate-800/60 backdrop-blur-xl border-slate-700 p-5 rounded-2xl shadow-lg">
            <p class="text-sm text-slate-400">Wallet Balance</p>
            <p class="text-5xl font-bold my-2 text-emerald-400">Ksh {user.balance:,.2f}</p>
            <div class="flex gap-3 mt-4">
                <button class="flex-1 bg-slate-700 py-2 rounded-lg text-sm">Statement</button>
                <a href="/bundles" class="flex-1 bg-emerald-600 py-2 rounded-lg text-sm text-center font-semibold">Top Up</a>
            </div>
        </div>
        <div class="bg-slate-800/60 backdrop-blur-xl border-slate-700 p-4 rounded-2xl mt-6">
            <div class="flex justify-between items-center mb-3"><p class="font-semibold">Quick Actions</p><a href="/bundles" class="text-sm text-emerald-400">Manage</a></div>
            <div class="grid grid-cols-4 gap-4 text-center">
                <a href="/bundles?tab=data" class="flex flex-col items-center gap-1"><div class="w-14 h-14 bg-slate-700 rounded-full flex items-center justify-center"><i data-lucide="smartphone" class="w-7 h-7 text-emerald-400"></i></div><span class="text-xs text-slate-400">Data</span></a>
                <a href="/bundles?tab=minutes" class="flex flex-col items-center gap-1"><div class="w-14 h-14 bg-slate-700 rounded-full flex items-center justify-center"><i data-lucide="phone" class="w-7 h-7 text-slate-400"></i></div><span class="text-xs text-slate-400">Minutes</span></a>
                <a href="/bundles?tab=sms" class="flex flex-col items-center gap-1"><div class="w-14 h-14 bg-slate-700 rounded-full flex items-center justify-center"><i data-lucide="message-square" class="w-7 h-7 text-slate-400"></i></div><span class="text-xs text-slate-400">SMS</span></a>
                <a href="/bundles?tab=tunukiwa" class="flex flex-col items-center gap-1"><div class="w-14 h-14 bg-slate-700 rounded-full flex items-center justify-center"><i data-lucide="zap" class="w-7 h-7 text-slate-400"></i></div><span class="text-xs text-slate-400">Tunukiwa</span></a>
            </div>
        </div>
    </div>
    """
    return page(content, True, 'home')

@app.route('/bundles')
def bundles():
    if 'user_id' not in session: return redirect('/login')
    tab = request.args.get('tab', 'data')
    if tab == 'data': items = {k: v for k, v in PRICES.items() if 'MB' in v or 'GB' in v and 'SMS' not in v and 'MINS' not in v and 'TUNUKIWA' not in v}
    elif tab == 'minutes': items = {k: v for k, v in PRICES.items() if 'MINS' in v}
    elif tab == 'sms': items = {k: v for k, v in PRICES.items() if 'SMS' in v}
    else: items = {k: v for k, v in PRICES.items() if 'TUNUKIWA' in v}
    
    items_html = ""
    for amount, name in sorted(items.items()):
        items_html += f"""
        <form action="/stkpush" method="post" class="bg-slate-800/60 backdrop-blur-xl border border-slate-700 p-4 rounded-xl flex justify-between items-center shadow-sm">
            <input type="hidden" name="amount" value="{amount}">
            <div>
                <p class="font-bold">{name}</p>
                <p class="text-sm text-slate-400">Valid: {name.split(' ')[-1]}</p>
            </div>
            <div class="text-right">
                 <p class="font-bold text-emerald-400">Ksh {amount}</p>
                 <input name="phone" type="tel" placeholder="2547XX" required class="w-24 mt-1 px-2 py-1 bg-slate-900 border-slate-700 rounded-lg text-xs text-center">
            </div>
        </form>
        """
    content = f"""
    <div class="p-4">
        <a href="/dashboard" class="flex items-center gap-2 mb-4 text-slate-400"><i data-lucide="arrow-left"></i> Back</a>
        <div class="flex border-b border-slate-700 mb-4">
            <a href="/bundles?tab=data" class="flex-1 py-2 text-center font-semibold {'border-b-2 border-emerald-400 text-emerald-400' if tab=='data' else 'text-slate-400'}">Data</a>
            <a href="/bundles?tab=minutes" class="flex-1 py-2 text-center font-semibold {'border-b-2 border-emerald-400 text-emerald-400' if tab=='minutes' else 'text-slate-400'}">Minutes</a>
            <a href="/bundles?tab=sms" class="flex-1 py-2 text-center font-semibold {'border-b-2 border-emerald-400 text-emerald-400' if tab=='sms' else 'text-slate-400'}">SMS</a>
            <a href="/bundles?tab=tunukiwa" class="flex-1 py-2 text-center font-semibold {'border-b-2 border-emerald-400 text-emerald-400' if tab=='tunukiwa' else 'text-slate-400'}">Tunukiwa</a>
        </div>
        <div class="space-y-3">
            {items_html}
        </div>
    </div>
    """
    return page(content, True, 'bundles')

@app.route('/ai-insights')
def ai_insights():
    if 'user_id' not in session: return redirect('/login')
    content = f"""
    <div class="p-4">
        <p class="text-2xl font-bold mb-4">AI Market Watch</p>
        <div class="space-y-4">
            <div class="bg-slate-800/60 backdrop-blur-xl border-slate-700 p-4 rounded-2xl">
                <p class="text-sm text-slate-400">Hot Right Now</p>
                <p class="text-2xl font-bold">{AI_INSIGHTS['hot_bundle']} <span class="text-emerald-400 text-lg">+{AI_INSIGHTS['trend_pct']}%</span></p>
            </div>
            <div class="bg-slate-800/60 backdrop-blur-xl border-slate-700 p-4 rounded-2xl">
                <p class="text-sm text-slate-400">Spend Forecast This Week</p>
                <p class="text-2xl font-bold">Ksh {AI_INSIGHTS['forecast']:,.2f}</p>
            </div>
            <div class="bg-slate-800/60 backdrop-blur-xl border-red-500/30 p-4 rounded-2xl">
                <p class="text-sm text-slate-400">Price Alert</p>
                <p class="text-lg font-semibold text-red-400">{AI_INSIGHTS['alert']}</p>
            </div>
            <form action="/stkpush" method="post" class="bg-slate-800/60 backdrop-blur-xl border-slate-700 p-4 rounded-2xl">
                <p class="font-semibold mb-2">Smart Rebuy</p>
                <input type="hidden" name="amount" value="99">
                <input name="phone" type="tel" placeholder="2547XX" required class="w-full px-4 py-2 bg-slate-900 border-slate-700 rounded-lg mb-2">
                <button class="w-full bg-emerald-600 py-2 rounded-lg font-bold">Rebuy 1GB 24HRS - Ksh 99</button>
            </form>
        </div>
    </div>
    """
    return page(content, True, 'ai')

@app.route('/stkpush', methods=['POST'])
def stkpush():
    if 'user_id' not in session: return redirect('/login')
    phone = request.form['phone'] 
    amount = int(request.form['amount'])
    user = User.query.get(session['user_id'])
    if user and not user.phone: user.phone = phone; db.session.commit()

    access_token = get_access_token()
    if not access_token: return "Error getting token"
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((BUSINESS_SHORT_CODE + PASSKEY + timestamp).encode()).decode('utf-8')
    payload = {"BusinessShortCode": BUSINESS_SHORT_CODE, "Password": password, "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline", "Amount": amount, "PartyA": phone, "PartyB": BUSINESS_SHORT_CODE, "PhoneNumber": phone, "CallBackURL": CALLBACK_URL, "AccountReference": "LensConnect", "TransactionDesc": PRICES.get(amount)}
    requests.post(api_url, json=payload, headers={"Authorization": f"Bearer {access_token}"})
    content = f"<div class='p-8 text-center'><i data-lucide='check-circle' class='w-16 h-16 text-emerald-400 mx-auto'></i><p class='mt-4 font-semibold'>STK sent for {PRICES.get(amount)}</p><a href='/bundles' class='text-emerald-400 mt-2 block'>Back to Bundles</a></div>"
    return page(content, True, 'bundles')

@app.route('/mpesa/confirmation', methods=['POST'])
def mpesa_confirmation():
    data = request.get_json()
    if data['Body']['stkCallback']['ResultCode'] == 0:
        callback = data['Body']['stkCallback']['CallbackMetadata']['Item']
        amount = int(next(item['Value'] for item in callback if item['Name'] == 'Amount'))
        mpesa_code = next(item['Value'] for item in callback if item['Name'] == 'MpesaReceiptNumber')
        phone = str(next(item['Value'] for item in callback if item['Name'] == 'PhoneNumber'))
        bundle_name = PRICES.get(amount, "UNKNOWN")
        
        if not Transaction.query.filter_by(mpesa_code=mpesa_code).first():
            txn = Transaction(phone=phone, amount=amount, bundle_name=bundle_name, mpesa_code=mpesa_code)
            db.session.add(txn)
            user = User.query.filter_by(phone=phone).first()
            if user and user.balance >= amount:
                user.balance -= amount
            db.session.commit()
            process_bundle(phone, amount, mpesa_code)
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})
    return jsonify({"ResultCode": 1, "ResultDesc": "Failed"})

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
