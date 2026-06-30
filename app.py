from flask import Flask, request, jsonify
import json
import os 
import threading
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'lensconnect.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

db = SQLAlchemy(app)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    amount = db.Column(db.Float)
    mpesa_code = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20))

with app.app_context():
    db.create_all()

PRICES = {
    # DATA BUNDLES - Buy once per day
    19: "1GB_1HR", 
    20: "250MB_24HRS", 
    49: "350MB_7DAYS", 
    50: "1.5GB_3HRS", 
    55: "1.25GB_TILL_MIDNIGHT", 
    99: "1GB_24HRS", 
    300: "2.5GB_7DAYS", 
    700: "6GB_7DAYS",

    # TUNUKIWA OFFERS - Buy many times per day 
    23: "1GB_1HR_TUNUKIWA", 
    51: "1.5GB_3HRS_TUNUKIWA", 
    110: "2GB_24HRS_TUNUKIWA",

    # MINUTES OFFERS - Buy many times per day
    22: "43MINS_3HRS", 
    52: "50MINS_TILL_MID",

    # SMS OFFERS - Buy many times per day
    5: "20SMS_24HRS", 
    10: "200SMS_24HRS", 
    30: "1000SMS_7DAYS", 
    101: "1500SMS_30DAYS",
}

def process_bundle(phone, amount, mpesa_code):
    with app.app_context():  # <-- Add this line
    bundle = PRICES.get(amount, "UNKNOWN")
    print(f"SIMULATED: Sending {bundle} to {phone}. Code: {mpesa_code}")
        txn = Transaction.query.filter_by(mpesa_code=mpesa_code).first()
        if txn:
            txn.status = "FULFILLED" 
            db.session.commit()
@app.route('/')
def home():
    return "LensConnect API is running"
@app.route('/mpesa/validation', methods=['POST'])
def mpesa_validation():
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

@app.route('/mpesa/confirmation', methods=['POST'])
def mpesa_confirmation():
    data = request.get_json()
    amount = float(data['TransAmount'])
    phone = data['MSISDN']
    mpesa_code = data['TransID']
    
    txn = Transaction(phone=phone, amount=amount, mpesa_code=mpesa_code, status="RECEIVED")
    db.session.add(txn); db.session.commit()

    threading.Thread(target=process_bundle, args=(phone, amount, mpesa_code)).start()
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})
def process_bundle(phone, amount, mpesa_code):
    with app.app_context():
        bundle = PRICES.get(amount, "UNKNOWN")
        print(f"SIMULATED: Sending {bundle} to {phone}. Code: {mpesa_code}")
        txn = Transaction.query.filter_by(mpesa_code=mpesa_code).first()
        if txn:
            txn.status = "FULFILLED" 
            db.session.commit()
@app.route("/")
def home():
    return "LensConnect API is running"
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
