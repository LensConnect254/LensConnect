from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import threading

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lensconnect.db'
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
    19: "1GB_1HR", 20: "250MB_24HRS", 49: "350MB_7DAYS", 
    99: "1GB_24HRS", 300: "2.5GB_7DAYS", 700: "6GB_7DAYS"
}

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