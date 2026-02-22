from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        print("Attempting to add 'framework' column to 'practice_history'...")
        # Check if column exists first? Postgres throws error if exists.
        # We'll just try to add it.
        db.session.execute(text("ALTER TABLE practice_history ADD COLUMN framework VARCHAR(255);"))
        db.session.commit()
        print("Migration successful: Added framework column.")
    except Exception as e:
        print(f"Migration output (ignore if column exists): {e}")
