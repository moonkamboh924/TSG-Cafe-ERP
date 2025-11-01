import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
from ..models import User
from ..extensions import db
from ..auth import log_audit

bp = Blueprint('profile', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folder():
    """Create upload folder if it doesn't exist"""
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    return upload_folder

def resize_image(image_path, max_size=(300, 300)):
    """Resize image to maximum dimensions while maintaining aspect ratio"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Resize maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save as JPEG with high quality
            img.save(image_path, 'JPEG', quality=90, optimize=True)
            
    except Exception as e:
        current_app.logger.error(f"Error resizing image: {str(e)}")
        raise

@bp.route('/api/profile/upload-picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Upload and update user profile picture"""
    try:
        # Check if file is present
        if 'profile_picture' not in request.files:
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        file = request.files['profile_picture']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                'success': False, 
                'message': 'Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WebP files only.'
            }), 400
        
        # Create upload folder
        upload_folder = create_upload_folder()
        
        # Generate unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{current_user.id}_{uuid.uuid4().hex}.jpg"  # Always save as JPG after processing
        file_path = os.path.join(upload_folder, filename)
        
        # Save the uploaded file temporarily
        temp_path = os.path.join(upload_folder, f"temp_{filename}")
        file.save(temp_path)
        
        try:
            # Resize and optimize the image
            resize_image(temp_path, max_size=(300, 300))
            
            # Move to final location
            if os.path.exists(file_path):
                os.remove(file_path)  # Remove old file if exists
            os.rename(temp_path, file_path)
            
            # Remove old profile picture if exists
            if current_user.profile_picture:
                old_path = os.path.join(current_app.root_path, 'static', current_user.profile_picture.lstrip('/'))
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass  # Ignore errors when removing old file
            
            # Update user profile picture path in database
            profile_picture_url = f"/static/uploads/profiles/{filename}"
            current_user.profile_picture = profile_picture_url
            db.session.commit()
            
            # Log the action
            log_audit('update', 'user_profile', current_user.id, {
                'action': 'profile_picture_upload',
                'filename': filename
            })
            
            return jsonify({
                'success': True,
                'message': 'Profile picture updated successfully',
                'profile_picture_url': profile_picture_url
            })
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
            
    except Exception as e:
        current_app.logger.error(f"Error uploading profile picture: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to upload profile picture. Please try again.'
        }), 500

@bp.route('/api/profile/remove-picture', methods=['POST'])
@login_required
def remove_profile_picture():
    """Remove user profile picture"""
    try:
        # Remove file from filesystem
        if current_user.profile_picture:
            old_path = os.path.join(current_app.root_path, 'static', current_user.profile_picture.lstrip('/'))
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass  # Ignore errors when removing file
        
        # Update database
        current_user.profile_picture = None
        db.session.commit()
        
        # Log the action
        log_audit('update', 'user_profile', current_user.id, {
            'action': 'profile_picture_removed'
        })
        
        return jsonify({
            'success': True,
            'message': 'Profile picture removed successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error removing profile picture: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to remove profile picture. Please try again.'
        }), 500
