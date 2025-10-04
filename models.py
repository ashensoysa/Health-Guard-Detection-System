from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from flask_login import UserMixin

# 🧠 Create database engine
engine = create_engine('sqlite:///patients.db', echo=False)

# 🔧 Setup base and session factory
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)
db_session = SessionLocal()

class Doctor(Base, UserMixin):
    __tablename__ = 'doctors'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password = Column(String(255))  # hashed password
    # Add doctor-specific fields if needed (name, specialization)

# 👨‍⚕️ Patient table definition
class Patient(Base):
    __tablename__ = 'patients'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    address = Column(String)
    systolic = Column(Float)
    diastolic = Column(Float)
    heart_rate = Column(Float)
    spo2 = Column(Float)
    result = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    notes = Column(String)  # Optional doctor's notes

# 🏁 Create DB tables
def init_db():
    Base.metadata.create_all(engine)

# 💾 Save patient record
def save_patient(data, prediction):
    patient = Patient(
        name=data['name'],
        age=data['age'],
        address=data['address'],
        systolic=data['systolic_bp'],
        diastolic=data['diastolic_bp'],
        heart_rate=data['heart_rate'],
        spo2=data['spo2'],
        result=prediction,
        notes=data.get('notes', '')  # Include notes if present
    )
    db_session.add(patient)
    db_session.commit()

# 📋 Get latest patient history
def get_patient_history():
    return db_session.query(Patient).order_by(Patient.timestamp.desc()).limit(10).all()

# 🔍 Search patients by name or date
def search_patient_history(name='', start='', end=''):
    query = db_session.query(Patient)
    if name:
        query = query.filter(Patient.name.like(f"%{name}%"))
    if start:
        query = query.filter(Patient.timestamp >= datetime.strptime(start, "%Y-%m-%d"))
    if end:
        query = query.filter(Patient.timestamp <= datetime.strptime(end, "%Y-%m-%d"))
    return query.order_by(Patient.timestamp.desc()).all()


