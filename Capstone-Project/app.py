from flask import Flask, request, render_template, jsonify
import csv
import qrcode
import base64
from io import BytesIO
from datetime import datetime
from twilio.rest import Client
import os

app = Flask(__name__, template_folder="C:/Users/kvnsa/OneDrive/Desktop/capstoneProject/capstone/templates")

# Load CSV file
def load_csv(file_path):
    vehicles = []
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                row = {k.strip(): v.strip() for k, v in row.items()}
                vehicles.append(row)
    except FileNotFoundError:
        print("CSV file not found. Creating a new one...")
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["regNo", "owner", "insurance_upto", "pucc_upto", "fitness_upto", "contact"])
            writer.writeheader()
    return vehicles

# Save to CSV file
def save_to_csv(file_path, fieldnames, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

# Validate date format
def validate_date(date_str):
    try:
        return datetime.strptime(date_str, "%d %m %Y")
    except ValueError:
        return None

# Twilio credentials (ensure these are securely stored)
TWILIO_ACCOUNT_SID = "ACa9872491f78295de78a7f680cf89ab62"
TWILIO_AUTH_TOKEN = "66c106058f7921d31b502b70575ad93b"
TWILIO_PHONE_NUMBER = "+12315383763"

# Function to send SMS alerts
def send_alert_message(contact_number, message):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    try:
        response = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=contact_number
        )
        print(f"Message sent to {contact_number}: {response.sid}")
    except Exception as e:
        print(f"Error sending message: {e}")

# Generate QR code as base64 string
def generate_qr(data):
    qr = qrcode.make(data)
    qr_io = BytesIO()
    qr.save(qr_io, format='PNG')
    qr_io.seek(0)
    return base64.b64encode(qr_io.getvalue()).decode('utf-8')

# Vehicle validation & SMS alerts
@app.route("/", methods=["GET", "POST"])
def validate_vehicle():
    vehicle = None
    warning_messages = []

    if request.method == "POST":
        reg_no = request.form.get("regNo", "").strip()
        vehicles = load_csv("data/data.csv")
        vehicle = next((v for v in vehicles if v.get("regNo") == reg_no), None)

        if vehicle:
            today = datetime.today()
            insurance_expiry = validate_date(vehicle.get("insurance_upto", ""))
            puc_expiry = validate_date(vehicle.get("pucc_upto", ""))
            fitness_expiry = validate_date(vehicle.get("fitness_upto", ""))

            if insurance_expiry and insurance_expiry < today:
                msg = f"🚗💰 ALERT: Insurance expired for vehicle 🚘 {reg_no}. Renew immediately! ⚠️"
                warning_messages.append(msg)
                send_alert_message(vehicle.get("contact", ""), msg)

            if puc_expiry and puc_expiry < today:
                msg = f"🏭⚠️ ALERT: PUCC expired for vehicle 🚘 {reg_no}. Renew to avoid fines! 🚨"
                warning_messages.append(msg)
                send_alert_message(vehicle.get("contact", ""), msg)

            if fitness_expiry and fitness_expiry < today:
                msg = f"🏋️‍♂️🔴 ALERT: Fitness certificate expired for vehicle 🚘 {reg_no}. Immediate renewal needed! 🔥"
                warning_messages.append(msg)
                send_alert_message(vehicle.get("contact", ""), msg)

            return render_template("index1.html", vehicle=vehicle, warnings=warning_messages)
        else:
            return render_template("index1.html", vehicle=None, warnings=["⚠️ Vehicle is not registered. Please register first."])

    return render_template("index1.html", vehicle=None, warnings=[])

# Vehicle registration & QR code generation
@app.route("/register", methods=["GET", "POST"])
def register():
    qr_code = None
    if request.method == "POST":
        data = {
            "regNo": request.form.get("regNo", "").strip(),
            "owner": request.form.get("owner", "").strip(),
            "insurance_upto": request.form.get("insurance_upto", "").strip(),
            "pucc_upto": request.form.get("pucc_upto", "").strip(),
            "fitness_upto": request.form.get("fitness_upto", "").strip(),
            "contact": request.form.get("contact", "").strip()
        }
        
        save_to_csv("data/data.csv", data.keys(), data)
        qr_code = generate_qr(data['regNo'])
        return render_template("register.html", qr_code=qr_code, success=True)

    return render_template("register.html")

# QR code scanning to retrieve vehicle details
@app.route('/scan_qr', methods=['POST'])
def scan_qr():
    vehicle_number = request.form.get("qr_data", "").strip()
    vehicles = load_csv("data/data.csv")
    vehicle = next((v for v in vehicles if v.get("regNo") == vehicle_number), None)

    if vehicle:
        return jsonify({"status": "success", "message": f"Vehicle {vehicle_number} exists. Validation successful!"})
    else:
        return jsonify({"status": "error", "message": "⚠️ Vehicle is not registered. Please register first."})

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
