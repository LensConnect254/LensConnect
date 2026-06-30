Line 1: from flask import Flask, request, jsonify
Line 2: import json
Line 3: import os
Line 4: import threading
app = Flask(__name__)
Line 6: db_path = os.path.join(os.path.dirname(__file__), 'instance', 'lensconnect.db')
Line 7: os.makedirs(os.path.dirname(db_path), exist_ok=True)
Line 8: app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
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
@app.route('/c2b/validation', methods=['POST'])
def validation():
    response = {"ResultCode": 0, "ResultDesc": "Accepted"}

@app.route('/c2b/confirmation', methods=['POST'])
def confirmation():
    data = request.get_json()
    print("C2B Payment Received:", json.dumps(data, indent=4))
    response = {"ResultCode": 0, "ResultDesc": "Accepted"}
    return jsonify(response)

def process_bundle(phone, amount, mpesa_code):
    with app.app_context():  # <-- Add this line
        print(f"SIMULATED: Sending {bundle} to {phone}. Code: {mpesa_code}")
        txn = Transaction.query.filter_by(mpesa_code=mpesa_code).first()
        if txn:
            txn.status = "FULFILLED" 
            db.session.commit()
@app.route('/')
def home():
    return "LensConnect API is running"
@app.route('/mpesa/validation', methods=['POST'])
def validation():
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

@app.route('/mpesa/confirmation', methods=['POST'])
def confirmation():
    data = request.get_json()
    amount = float(data['TransAmount'])
    phone = data['MSISDN']
    mpesa_code = data['TransID']
    
    txn = Transaction(phone=phone, amount=amount, mpesa_code=mpesa_code, status="RECEIVED")
    db.session.add(txn); db.session.commit()

    threading.Thread(target=process_bundle, args=(phone, amount, mpesa_code)).start()
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
    from flask import request, jsonify
import json

@app.route('/c2b/validation', methods=['POST'])
def validation():
    # Safaricom asks: "Can I send money?" We say: "Yes 0 = Success"
    response = {"ResultCode": 0, "ResultDesc": "Accepted"}
    return jsonify(response)

@app.route('/c2b/confirmation', methods=['POST'])
def confirmation():
    # Safaricom sends the real M-Pesa data here after payment
    data = request.get_json()
    print("C2B Payment Received:", json.dumps(data, indent=4))
    # TODO: Later we will use process_bundle() here
    
    response = {"ResultCode": 0, "ResultDesc": "Accepted"}
    return jsonify(response)
