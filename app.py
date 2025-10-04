from flask import Flask, render_template, request, redirect, jsonify, make_response
from models import init_db, save_patient, get_patient_history, Patient, db_session, Doctor
import os, io, csv
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import engine


app = Flask(__name__)
app.secret_key = "your_secret_key"

# Initialize DB
if not os.path.exists('patients.db'):
    init_db()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db_session.query(Doctor).get(int(user_id))

# 🧠 Landing page
@app.route('/')
def index():
    return redirect('/login')

# 🔐 Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        new_doc = Doctor(username=username, password=password)
        db_session.add(new_doc)
        db_session.commit()
        return redirect('/login')
    return render_template('register.html')

# 🔐 Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        print("🔍 Trying login for:", username)  # DEBUG: Input username

        doc = db_session.query(Doctor).filter_by(username=username).first()
        print("🧑‍⚕️ Found doctor record:", doc)  # DEBUG: Doctor object from DB

        if doc and check_password_hash(doc.password, password):
            login_user(doc)
            print("✅ Login successful for:", username)
            return redirect('/dashboard')
        else:
            print("❌ Login failed for:", username)
            return "Invalid credentials", 401

    return render_template('login.html')

# 🚪 Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# 📊 Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    history = get_patient_history()
    return render_template('dashboard.html', history=history)

# 🤖 Prediction
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    data = request.get_json()
    systolic = int(data['systolic_bp'])
    diastolic = int(data['diastolic_bp'])
    heart_rate = int(data['heart_rate'])
    spo2 = int(data['spo2'])

    result = "RISK" if (systolic > 140 or diastolic > 90 or heart_rate > 100 or spo2 < 95) else "HEALTHY"
    save_patient(data, result)
    return {'result': result}

# 📤 Export CSV
@app.route('/export/csv')
@login_required
def export_csv():
    patients = get_patient_history()
    rows = [['Name', 'Age', 'Address', 'Date', 'Systolic', 'Diastolic', 'HR', 'SpO2', 'Result']]
    for p in patients:
        rows.append([p.name, p.age, p.address, p.timestamp.strftime('%Y-%m-%d %H:%M'),
                     p.systolic, p.diastolic, p.heart_rate, p.spo2, p.result])
    output = make_response('\n'.join([','.join(map(str, row)) for row in rows]))
    output.headers["Content-Disposition"] = "attachment; filename=patient_history.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# 📤 Export PDF
@app.route('/export/pdf')
@login_required
def export_pdf():
    patients = get_patient_history()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = [Paragraph("🧠 Health Guard — Patient Report", getSampleStyleSheet()['Title']), Spacer(1, 12)]

    data = [['Name', 'Age', 'Address', 'Date', 'Systolic', 'Diastolic', 'HR', 'SpO₂', 'Result']]
    for p in patients:
        data.append([p.name, p.age, p.address, p.timestamp.strftime('%Y-%m-%d %H:%M'),
                     p.systolic, p.diastolic, p.heart_rate, p.spo2, p.result])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0077b6')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (1,1), (-1,-1), [colors.whitesmoke, colors.lightgrey])
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return make_response(buffer.getvalue(), {
        "Content-Disposition": "attachment; filename=patient_report.pdf",
        "Content-Type": "application/pdf"
    })

# 📈 Chart Data
@app.route('/chartdata')
@login_required
def chart_data():
    patients = get_patient_history()[::-1]
    labels = [p.timestamp.strftime('%Y-%m-%d %H:%M') for p in patients]
    return jsonify({
        'labels': labels,
        'heart': [p.heart_rate for p in patients],
        'spo2': [p.spo2 for p in patients],
        'systolic': [p.systolic for p in patients],
        'diastolic': [p.diastolic for p in patients]
    })

@app.route('/diseases')
@login_required
def diseases():
    return render_template('diseases.html')

# 👤 Patient Profile View
@app.route('/patient/<int:id>')
@login_required
def patient_profile(id):
    patient = db_session.query(Patient).filter_by(id=id).first()
    if not patient:
        return "Patient not found", 404

    query = db_session.query(Patient).filter_by(name=patient.name)
    if request.args.get('start_date'):
        query = query.filter(Patient.timestamp >= datetime.strptime(request.args.get('start_date'), "%Y-%m-%d"))
    if request.args.get('end_date'):
        query = query.filter(Patient.timestamp <= datetime.strptime(request.args.get('end_date'), "%Y-%m-%d"))
    if request.args.get('keyword'):
        query = query.filter(Patient.notes.like(f"%{request.args.get('keyword')}%"))
    if request.args.get('risk_only'):
        query = query.filter(Patient.result == "RISK")

    records = query.order_by(Patient.timestamp.desc()).all()
    return render_template('profile.html', patient=patient, records=records)

@app.route('/patient/chartdata/<int:id>')
@login_required
def patient_chartdata(id):
    patient = db_session.query(Patient).filter_by(id=id).first()
    if not patient:
        return jsonify({})
    records = db_session.query(Patient).filter_by(name=patient.name).order_by(Patient.timestamp.asc()).all()
    labels = [r.timestamp.strftime('%Y-%m-%d %H:%M') for r in records]
    return jsonify({
        'labels': labels,
        'heart': [r.heart_rate for r in records],
        'spo2': [r.spo2 for r in records],
        'systolic': [r.systolic for r in records],
        'diastolic': [r.diastolic for r in records]
    })

@app.route('/patient/export/pdf/<int:id>')
@login_required
def export_profile_pdf(id):
    patient = db_session.query(Patient).filter_by(id=id).first()
    if not patient:
        return "Patient not found", 404

    records = db_session.query(Patient).filter_by(name=patient.name).order_by(Patient.timestamp.desc()).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = [Paragraph("🧠 Liberty Channel Center – Patient Summary", getSampleStyleSheet()['Title']), Spacer(1, 12)]
    elements.append(Paragraph(f"👤 <b>Name:</b> {patient.name}<br/>🕒 <b>Age:</b> {patient.age}<br/>🏠 <b>Address:</b> {patient.address}", getSampleStyleSheet()['Normal']))
    elements.append(Spacer(1, 12))

    table_data = [['Timestamp', 'Result', 'Systolic', 'Diastolic', 'HR', 'SpO₂', 'Notes']]
    for r in records:
                table_data.append([
            r.timestamp.strftime('%Y-%m-%d %H:%M'),
            r.result,
            r.systolic,
            r.diastolic,
            r.heart_rate,
            r.spo2,
            r.notes or '—'
        ])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0077b6')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (1,1), (-1,-1), [colors.whitesmoke, colors.lightgrey])
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return make_response(buffer.getvalue(), {
        "Content-Disposition": f"attachment; filename={patient.name}_profile.pdf",
        "Content-Type": "application/pdf"
    })

def init_db():
    from models import Base  # If using a declarative base
    Base.metadata.create_all(bind=engine)


# 🚀 Start App
if __name__ == '__main__':
    app.run(debug=True)

