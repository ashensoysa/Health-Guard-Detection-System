from models import Base, engine

# Create all tables defined in models.py
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully!")
