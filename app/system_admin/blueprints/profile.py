"""
System Admin Profile Management Blueprint
Handles profile picture uploads and user profile management
"""

import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
from ...extensions import db
from ..decorators import system_admin_api_required

bp = Blueprint('system_admin_profile', __name__, url_prefix='/system-admin/profile')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_image(image_path, max_size=(300, 300)):
    """Resize image to maximum dimensions while maintaining aspect ratio"""
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Resize image
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(image_path, 'JPEG', quality=85, optimize=True)
            return True
    except Exception as e:
        print(f"Error resizing image: {e}")
        return False

@bp.route('/api/upload-profile-picture', methods=['POST'])
@login_required
@system_admin_api_required
def upload_profile_picture():
    """Upload and update user profile picture"""
    try:
        # Check if file is in request
        if 'profile_picture' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['profile_picture']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': 'File size too large. Maximum 5MB allowed'}), 400
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'profiles')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{current_user.id}_{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Resize image
        if not resize_image(file_path):
            # If resize fails, remove the file and return error
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': 'Failed to process image'}), 500
        
        # Remove old profile picture if exists
        if current_user.profile_picture:
            old_file_path = os.path.join(current_app.static_folder, 'uploads', 'profiles', 
                                       os.path.basename(current_user.profile_picture))
            try:
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except:
                pass  # Ignore errors when removing old file
        
        # Update user profile picture in database
        profile_picture_url = f"/static/uploads/profiles/{unique_filename}"
        current_user.profile_picture = profile_picture_url
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile picture updated successfully',
            'profile_picture_url': profile_picture_url
        })
        
    except Exception as e:
        # Rollback database changes
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
