from app.db.session import engine, Base
import app.models  # Ensure all models are registered

def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()
