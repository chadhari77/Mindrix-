from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import json
import logging
from pathlib import Path
import traceback

# Initialize Firebase FIRST before importing other modules
from utils.firebase_config import initialize_firebase
firebase_app = initialize_firebase()

# Now import other modules that depend on Firebase
from utils.auth import authenticate_user, create_user, get_user_role
from utils.rag_system import RAGSystem
from utils.email_automation import send_notification

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['NOTES_FOLDER'] = 'uploads/notes'
app.config['DOCUMENTS_FOLDER'] = 'uploads/documents'
app.config['TEMP_FOLDER'] = 'uploads/temp'

# Create upload directories if they don't exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['NOTES_FOLDER'], 
               app.config['DOCUMENTS_FOLDER'], app.config['TEMP_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'ppt', 'pptx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize RAG system with error handling
try:
    rag_system = RAGSystem()
    #logger.info("RAG system initialized successfully")
except Exception as e:
    #logger.error(f"Failed to initialize RAG system: {str(e)}")
    rag_system = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Landing page - redirect to login if not authenticated"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for all user types"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get('email')
            password = data.get('password')
            user_type = data.get('user_type', 'student')
            
            if not email or not password:
                return jsonify({'error': 'Email and password are required'}), 400
            
            # Authenticate user
            user = authenticate_user(email, password, user_type)
            if user:
                session['user_id'] = user['uid']
                session['user_type'] = user_type
                session['user_email'] = email
                
                logger.info(f"User {email} logged in successfully as {user_type}")
                
                if request.is_json:
                    return jsonify({'success': True, 'redirect': url_for('dashboard')})
                else:
                    flash('Login successful!', 'success')
                    return redirect(url_for('dashboard'))
            else:
                error_msg = 'Invalid email or password'
                if request.is_json:
                    return jsonify({'error': error_msg}), 401
                else:
                    flash(error_msg, 'error')
                    
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            error_msg = 'An error occurred during login'
            if request.is_json:
                return jsonify({'error': error_msg}), 500
            else:
                flash(error_msg, 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page for all user types"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            required_fields = ['email', 'password', 'confirm_password', 'user_type', 'full_name']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
            
            # Validate password match
            if data['password'] != data['confirm_password']:
                return jsonify({'error': 'Passwords do not match'}), 400
            
            # Additional validation based on user type
            if data['user_type'] == 'student':
                if not data.get('student_id') or not data.get('section'):
                    return jsonify({'error': 'Student ID and Section are required for students'}), 400
            elif data['user_type'] == 'faculty':
                if not data.get('employee_id') or not data.get('department'):
                    return jsonify({'error': 'Employee ID and Department are required for faculty'}), 400
            elif data['user_type'] == 'admin':
                if not data.get('admin_code'):
                    return jsonify({'error': 'Admin code is required for admin registration'}), 400
            
            # Create user
            user = create_user(data)
            if user:
                logger.info(f"User {data['email']} registered successfully as {data['user_type']}")
                
                # Send welcome email
                try:
                    send_notification(
                        recipient=data['email'],
                        subject='Welcome to College Management System',
                        message=f"Welcome {data['full_name']}! Your account has been created successfully."
                    )
                except Exception as e:
                    logger.error(f"Failed to send welcome email: {str(e)}")
                
                if request.is_json:
                    return jsonify({'success': True, 'message': 'Registration successful! Please login.'})
                else:
                    flash('Registration successful! Please login.', 'success')
                    return redirect(url_for('login'))
            else:
                error_msg = 'Registration failed. Email might already exist.'
                if request.is_json:
                    return jsonify({'error': error_msg}), 400
                else:
                    flash(error_msg, 'error')
                    
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            error_msg = 'An error occurred during registration'
            if request.is_json:
                return jsonify({'error': error_msg}), 500
            else:
                flash(error_msg, 'error')
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page - role-based content"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_type = session.get('user_type', 'student')
    user_email = session.get('user_email', '')
    
    # Get user-specific data
    user_data = {
        'user_type': user_type,
        'email': user_email,
        'features': get_user_features(user_type)
    }
    
    return render_template('dashboard.html', user_data=user_data)

@app.route('/notes')
def notes():
    """AI Notes Bot page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('notes.html')

@app.route('/api/notes/upload', methods=['POST'])
def upload_notes():
    """Upload notes - Faculty only with improved error handling"""
    logger.info("Upload request received")
    
    # Check authentication
    if 'user_id' not in session:
        logger.error("Unauthorized access attempt")
        return jsonify({'error': 'Unauthorized - Please login'}), 403
    
    # Check user type
    if session.get('user_type') != 'faculty':
        logger.error(f"Non-faculty user attempted upload: {session.get('user_type')}")
        return jsonify({'error': 'Unauthorized - Faculty access required'}), 403
    
    # Check if RAG system is initialized
    if rag_system is None:
        logger.error("RAG system not initialized")
        return jsonify({'error': 'System not ready - RAG system initialization failed'}), 500
    
    try:
        logger.info("Checking for uploaded files")
        
        # Check if file is in request
        if 'file' not in request.files:
            logger.error("No file in request")
            return jsonify({'error': 'No file provided'}), 400
        
        files = request.files.getlist('file')
        if not files or (len(files) == 1 and files[0].filename == ''):
            logger.error("No file selected")
            return jsonify({'error': 'No file selected'}), 400
        
        uploaded_files = []
        failed_files = []
        
        for file in files:
            try:
                logger.info(f"Processing file: {file.filename}")
                
                # Validate file
                if not file.filename:
                    failed_files.append({'filename': 'Unknown', 'error': 'No filename'})
                    continue
                
                if not allowed_file(file.filename):
                    failed_files.append({'filename': file.filename, 'error': 'File type not allowed'})
                    continue
                
                # Get additional metadata from form
                department = request.form.get('department', 'General')
                subject = request.form.get('subject', 'General')
                
                logger.info(f"File validation passed for: {file.filename}")
                logger.info(f"Department: {department}, Subject: {subject}")
                
                # Save and process file using RAG system
                success = rag_system.add_document(file, department=department, subject=subject)
                
                if success:
                    uploaded_files.append({
                        'filename': file.filename,
                        'department': department,
                        'subject': subject
                    })
                    logger.info(f"Successfully processed: {file.filename}")
                else:
                    failed_files.append({'filename': file.filename, 'error': 'Failed to process document'})
                    logger.error(f"Failed to process: {file.filename}")
                
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                failed_files.append({'filename': file.filename, 'error': str(e)})
        
        # Prepare response
        response_data = {
            'success': len(uploaded_files) > 0,
            'uploaded_files': uploaded_files,
            'failed_files': failed_files
        }
        
        if len(uploaded_files) > 0:
            response_data['message'] = f'Successfully uploaded {len(uploaded_files)} file(s)'
            if len(failed_files) > 0:
                response_data['message'] += f', {len(failed_files)} file(s) failed'
        else:
            response_data['error'] = 'No files were uploaded successfully'
            return jsonify(response_data), 400
        
        logger.info(f"Upload completed: {len(uploaded_files)} success, {len(failed_files)} failed")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/notes/query', methods=['POST'])
def query_notes():
    """Query the AI notes bot"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if rag_system is None:
        return jsonify({'error': 'System not ready'}), 500
    
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Get response from RAG system
        response = rag_system.query(query)
        
        logger.info(f"Query processed: {query[:50]}...")
        return jsonify({'response': response})
        
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        return jsonify({'error': 'Query processing failed'}), 500

@app.route('/api/notes/list')
def list_notes():
    """List available notes"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if rag_system is None:
        return jsonify({'error': 'System not ready'}), 500
    
    try:
        notes = rag_system.get_document_list()
        return jsonify({'notes': notes})
    except Exception as e:
        logger.error(f"List notes error: {str(e)}")
        return jsonify({'error': 'Failed to get notes list'}), 500

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

def get_user_features(user_type):
    """Get available features based on user type"""
    features = {
        'student': [
            {'name': 'AI Notes Bot', 'url': '/notes', 'icon': 'robot'},
            {'name': 'My Schedule', 'url': '/schedule', 'icon': 'calendar'},
            {'name': 'Exam Seats', 'url': '/exam-seats', 'icon': 'chair'},
            {'name': 'Submit Complaint', 'url': '/complaints', 'icon': 'message-circle'}
        ],
        'faculty': [
            {'name': 'Upload Notes', 'url': '/notes', 'icon': 'upload'},
            {'name': 'Room Allocation', 'url': '/room-allocation', 'icon': 'map'},
            {'name': 'Student Management', 'url': '/students', 'icon': 'users'},
            {'name': 'Schedule Classes', 'url': '/schedule-classes', 'icon': 'clock'}
        ],
        'admin': [
            {'name': 'User Management', 'url': '/user-management', 'icon': 'settings'},
            {'name': 'Room Management', 'url': '/room-management', 'icon': 'building'},
            {'name': 'Complaint Management', 'url': '/complaint-management', 'icon': 'shield'},
            {'name': 'System Reports', 'url': '/reports', 'icon': 'bar-chart'}
        ]
    }
    return features.get(user_type, [])

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)