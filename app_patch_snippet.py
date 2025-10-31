# --- Add this block near your Flask/DB initialization ---
import os

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me-in-prod')

db_url = os.getenv('DATABASE_URL', 'sqlite:////tmp/inventory.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        app.logger.error(f"DB init error: {e}")

@app.route('/health')
def health():
    return 'ok', 200
