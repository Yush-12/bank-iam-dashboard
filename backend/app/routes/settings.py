from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
import json

from ..seeder import clear_user_data, seed_database, seed_custom_data
from ..models import db

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")

@settings_bp.route("/randomize", methods=["POST"])
def randomize_data():
    """Clear user data and re-seed randomly."""
    try:
        clear_user_data()
        seed_database(randomize=True)
        return jsonify({"message": "Data randomized successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@settings_bp.route("/upload", methods=["POST"])
def upload_data():
    """Upload custom JSON data."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    try:
        data = json.load(file)
        if not isinstance(data, dict) or "users" not in data:
            return jsonify({"error": "Invalid JSON schema. 'users' key is required."}), 400
            
        clear_user_data()
        seed_custom_data(data)
        return jsonify({"message": "Custom data uploaded successfully."})
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format."}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
