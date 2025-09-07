import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
import json
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib import colors

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum('admin', 'teacher', 'student'), nullable=False, default='student')
    full_name = db.Column(db.String(200), nullable=False)
    profile_picture = db.Column(db.String(300), nullable=True)
    contact_details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    groups = db.relationship('GroupMember', backref='student', lazy=True)
    created_groups = db.relationship('Group', backref='teacher', lazy=True)
    submissions = db.relationship('Submission', backref='student', lazy=True)
    feedbacks = db.relationship('Feedback', backref='teacher', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    join_password = db.Column(db.String(100), nullable=False)
    project_question = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    members = db.relationship('GroupMember', backref='group', lazy=True)
    log_entries = db.relationship('LogEntry', backref='group', lazy=True)
    assignments = db.relationship('Assignment', backref='group', lazy=True)

class GroupMember(db.Model):
    __tablename__ = 'group_members'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

class LogEntry(db.Model):
    __tablename__ = 'log_entries'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    # ADD THESE RELATIONSHIPS
    student = db.relationship('User', backref='log_entries_created')
    group_rel = db.relationship('Group', backref='log_entries_rel')
    
    feedbacks = db.relationship('Feedback', backref='log_entry', lazy=True)

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    question_file = db.Column(db.String(300), nullable=True)
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    submissions = db.relationship('Submission', backref='assignment', lazy=True)

class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    submitted_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    grade = db.Column(db.Numeric(5, 2), nullable=True)
    feedback = db.Column(db.Text, nullable=True)

class Feedback(db.Model):
    __tablename__ = 'feedbacks'
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('log_entries.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'pptx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file, subfolder):
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
        
        # Create directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        print(f"File saved to: {file_path}")  # Debug
        
        return f"uploads/{subfolder}/{unique_filename}"
    return None

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'student')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return render_template('auth/register.html')
        
        profile_picture = None
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                try:
                    # Simple file extension check
                    if file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        unique_filename = f"{timestamp}_{filename}"
                        
                        # Save file
                        profiles_dir = os.path.join('static', 'uploads', 'profiles')
                        os.makedirs(profiles_dir, exist_ok=True)
                        file_path = os.path.join(profiles_dir, unique_filename)
                        file.save(file_path)
                        
                        profile_picture = f"uploads/profiles/{unique_filename}"
                        print(f"Profile picture saved: {profile_picture}")
                    else:
                        flash('Please upload an image file (PNG, JPG, GIF)', 'warning')
                except Exception as e:
                    print(f"Error saving file: {e}")
                    flash('Error uploading profile picture', 'danger')
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            profile_picture=profile_picture
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return render_template('dashboard/admin.html')
    elif current_user.role == 'teacher':
        groups = Group.query.filter_by(teacher_id=current_user.id).all()
        return render_template('dashboard/teacher.html', groups=groups)
    else:
        # Get groups where the current user is a member
        group_memberships = GroupMember.query.filter_by(student_id=current_user.id).all()
        group_ids = [gm.group_id for gm in group_memberships]
        groups = Group.query.filter(Group.id.in_(group_ids)).all() if group_ids else []
        
        # Get pending assignments
        assignments = Assignment.query.filter(
            Assignment.group_id.in_(group_ids),
            Assignment.due_date > datetime.now()
        ).all()
        
        # Check which assignments the student has submitted
        submitted_assignments = Submission.query.filter(
            Submission.student_id == current_user.id,
            Submission.assignment_id.in_([a.id for a in assignments])
        ).all()
        
        submitted_assignment_ids = [sa.assignment_id for sa in submitted_assignments]
        
        return render_template('dashboard/student.html', 
                             groups=groups, 
                             assignments=assignments,
                             submitted_assignment_ids=submitted_assignment_ids,
                             now=datetime.now())

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/groups/create', methods=['GET', 'POST'])
@login_required
def create_group():
    if current_user.role != 'teacher':
        flash('Only teachers can create groups', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        join_password = request.form.get('join_password')
        project_question = request.form.get('project_question')
        
        group = Group(
            name=name,
            description=description,
            teacher_id=current_user.id,
            join_password=join_password,
            project_question=project_question
        )
        
        db.session.add(group)
        db.session.commit()
        
        flash('Group created successfully', 'success')
        return redirect(url_for('view_group', group_id=group.id))
    
    return render_template('groups/create.html')

@app.route('/groups/join', methods=['GET', 'POST'])
@login_required
def join_group():
    if current_user.role != 'student':
        flash('Only students can join groups', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        
        if not password:
            flash('Please enter the group password', 'danger')
            return render_template('groups/join.html')
        
        # Find group by join password
        group = Group.query.filter_by(join_password=password).first()
        
        if not group:
            flash('Invalid group password. Please check the password and try again.', 'danger')
            return render_template('groups/join.html')
        
        # Check if student is already a member
        existing_member = GroupMember.query.filter_by(
            group_id=group.id, 
            student_id=current_user.id
        ).first()
        
        if existing_member:
            flash('You are already a member of this group', 'info')
            return redirect(url_for('view_group', group_id=group.id))
        
        membership = GroupMember(group_id=group.id, student_id=current_user.id)
        db.session.add(membership)
        db.session.commit()
        
        flash(f'Successfully joined the group: {group.name}', 'success')
        return redirect(url_for('view_group', group_id=group.id))
    
    return render_template('groups/join.html')

@app.route('/groups/<int:group_id>')
@login_required
def view_group(group_id):
    group = Group.query.get_or_404(group_id)
    
    # Check if user has access to this group
    if current_user.role == 'student':
        membership = GroupMember.query.filter_by(
            group_id=group_id, 
            student_id=current_user.id
        ).first()
        if not membership:
            flash('You are not a member of this group', 'danger')
            return redirect(url_for('dashboard'))
    elif current_user.role == 'teacher' and group.teacher_id != current_user.id:
        flash('You are not the teacher of this group', 'danger')
        return redirect(url_for('dashboard'))
    
    # EAGER LOAD THE STUDENT RELATIONSHIP
    log_entries = LogEntry.query.options(db.joinedload(LogEntry.student)).filter_by(
        group_id=group_id
    ).order_by(LogEntry.created_at.desc()).all()
    
    assignments = Assignment.query.filter_by(group_id=group_id).order_by(Assignment.due_date.asc()).all()
    members = GroupMember.query.filter_by(group_id=group_id).all()
    
    return render_template('groups/view.html', 
                         group=group, 
                         log_entries=log_entries,
                         assignments=assignments,
                         members=members,
                         now=datetime.now())
                         
@app.route('/logs/create', methods=['GET', 'POST'])
@login_required
def create_log():
    if current_user.role != 'student':
        flash('Only students can create log entries', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get groups where the current user is a member
    group_memberships = GroupMember.query.filter_by(student_id=current_user.id).all()
    group_ids = [gm.group_id for gm in group_memberships]
    groups = Group.query.filter(Group.id.in_(group_ids)).all() if group_ids else []
    
    if request.method == 'POST':
        group_id = request.form.get('group_id')
        title = request.form.get('title')
        content = request.form.get('content')
        
        # Verify the student is a member of the group
        membership = GroupMember.query.filter_by(
            group_id=group_id, 
            student_id=current_user.id
        ).first()
        
        if not membership:
            flash('You are not a member of this group', 'danger')
            return redirect(url_for('dashboard'))
        
        media_url = None
        if 'media' in request.files:
            file = request.files['media']
            media_url = save_file(file, 'media')
        
        log_entry = LogEntry(
            group_id=group_id,
            student_id=current_user.id,
            title=title,
            content=content,
            media_url=media_url
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        flash('Log entry created successfully', 'success')
        return redirect(url_for('view_group', group_id=group_id))
    
    return render_template('logs/create.html', groups=groups)

@app.route('/assignments/<int:assignment_id>')
@login_required
def view_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if user has access to this assignment
    if current_user.role == 'student':
        # Check if student is in the group
        membership = GroupMember.query.filter_by(
            group_id=assignment.group_id, 
            student_id=current_user.id
        ).first()
        if not membership:
            flash('You are not a member of this group', 'danger')
            return redirect(url_for('dashboard'))
    elif current_user.role == 'teacher' and assignment.group.teacher_id != current_user.id:
        flash('You are not the teacher of this group', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if student has submitted this assignment
    submission = None
    if current_user.role == 'student':
        submission = Submission.query.filter_by(
            assignment_id=assignment_id,
            student_id=current_user.id
        ).first()
    
    return render_template('assignments/view.html', 
                         assignment=assignment,
                         submission=submission,
                         now=datetime.now())

@app.route('/assignments/create', methods=['GET', 'POST'])
@login_required
def create_assignment():
    if current_user.role != 'teacher':
        flash('Only teachers can create assignments', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get groups taught by the current user
    groups = Group.query.filter_by(teacher_id=current_user.id).all()
    
    if request.method == 'POST':
        group_id = request.form.get('group_id')
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        
        # Verify the teacher owns the group
        group = Group.query.get(group_id)
        if not group or group.teacher_id != current_user.id:
            flash('Invalid group selection', 'danger')
            return render_template('assignments/create.html', groups=groups)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format', 'danger')
            return render_template('assignments/create.html', groups=groups)
        
        # Handle file upload
        question_file = None
        if 'question_file' in request.files:
            file = request.files['question_file']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    question_file = save_file(file, 'questions')
                else:
                    flash('Invalid file type. Allowed: PDF, DOC, DOCX, PPT, PPTX', 'danger')
                    return render_template('assignments/create.html', groups=groups)
        
        # Create assignment with question file
        assignment = Assignment(
            group_id=group_id,
            teacher_id=current_user.id,
            title=title,
            description=description,
            question_file=question_file,
            due_date=due_date
        )
        
        db.session.add(assignment)
        db.session.commit()
        
        flash('Assignment created successfully', 'success')
        return redirect(url_for('view_group', group_id=group_id))
    
    return render_template('assignments/create.html', groups=groups)

@app.route('/assignments/<int:assignment_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_assignment(assignment_id):
    if current_user.role != 'student':
        flash('Only students can submit assignments', 'danger')
        return redirect(url_for('dashboard'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if student is in the group
    membership = GroupMember.query.filter_by(
        group_id=assignment.group_id, 
        student_id=current_user.id
    ).first()
    
    if not membership:
        flash('You are not a member of this group', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if already submitted
    existing_submission = Submission.query.filter_by(
        assignment_id=assignment_id,
        student_id=current_user.id
    ).first()
    
    if request.method == 'POST':
        if existing_submission:
            flash('You have already submitted this assignment', 'info')
            return redirect(url_for('view_group', group_id=assignment.group_id))
        
        if 'file' not in request.files or not request.files['file'].filename:
            flash('Please select a file to upload', 'danger')
            return render_template('assignments/submit.html', assignment=assignment, now=datetime.now())
        
        file = request.files['file']
        file_path = save_file(file, 'submissions')
        
        if not file_path:
            flash('Invalid file type', 'danger')
            return render_template('assignments/submit.html', assignment=assignment, now=datetime.now())
        
        submission = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            file_path=file_path
        )
        
        db.session.add(submission)
        db.session.commit()
        
        flash('Assignment submitted successfully', 'success')
        return redirect(url_for('view_group', group_id=assignment.group_id))
    
    return render_template('assignments/submit.html', 
                         assignment=assignment, 
                         existing_submission=existing_submission,
                         now=datetime.now())

@app.route('/assignments/<int:assignment_id>/grade', methods=['POST'])
@login_required
def grade_assignment(assignment_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Only teachers can grade assignments'}), 403
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Verify the teacher owns the assignment's group
    if assignment.group.teacher_id != current_user.id:
        return jsonify({'error': 'You are not the teacher of this group'}), 403
    
    data = request.get_json()
    student_id = data.get('student_id')
    grade = data.get('grade')
    feedback = data.get('feedback', '')
    
    # Validate grade - allow empty grade (null)
    if grade and grade != '':
        try:
            grade_value = float(grade)
            if grade_value < 0 or grade_value > 100:
                return jsonify({'error': 'Grade must be between 0 and 100'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid grade format'}), 400
    else:
        grade_value = None
    
    submission = Submission.query.filter_by(
        assignment_id=assignment_id,
        student_id=student_id
    ).first()
    
    if not submission:
        return jsonify({'error': 'Submission not found'}), 404
    
    # Update the submission
    submission.grade = grade_value
    submission.feedback = feedback
    
    try:
        db.session.commit()
        return jsonify({'message': 'Grade updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
    
@app.route('/logs/<int:log_id>')
@login_required
def view_log(log_id):
    log_entry = LogEntry.query.options(db.joinedload(LogEntry.student)).get_or_404(log_id)
    
    # Check if user has access to this log
    if current_user.role == 'student' and log_entry.student_id != current_user.id:
        flash('You can only view your own log entries', 'danger')
        return redirect(url_for('dashboard'))
    
    # For teachers, check if they teach the group
    if current_user.role == 'teacher' and log_entry.group.teacher_id != current_user.id:
        flash('You are not the teacher of this group', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('logs/view.html', 
                         log_entry=log_entry,
                         now=datetime.now())   

@app.route('/logs/<int:log_id>/feedback', methods=['POST'])
@login_required
def add_feedback(log_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Only teachers can provide feedback'}), 403
    
    log_entry = LogEntry.query.get_or_404(log_id)
    
    # Verify the teacher owns the group
    if log_entry.group.teacher_id != current_user.id:
        return jsonify({'error': 'You are not the teacher of this group'}), 403
    
    data = request.get_json()
    feedback_text = data.get('feedback')
    
    if not feedback_text:
        return jsonify({'error': 'Feedback cannot be empty'}), 400
    
    feedback = Feedback(
        log_id=log_id,
        teacher_id=current_user.id,
        feedback=feedback_text
    )
    
    db.session.add(feedback)
    db.session.commit()
    
    return jsonify({'message': 'Feedback added successfully'})

@app.route('/generate-report/<int:group_id>')
@login_required
def generate_report(group_id):
    group = Group.query.get_or_404(group_id)
    
    # Check if user has access to this group
    if current_user.role == 'student':
        membership = GroupMember.query.filter_by(
            group_id=group_id, 
            student_id=current_user.id
        ).first()
        if not membership:
            flash('You are not a member of this group', 'danger')
            return redirect(url_for('dashboard'))
    elif current_user.role == 'teacher' and group.teacher_id != current_user.id:
        flash('You are not the teacher of this group', 'danger')
        return redirect(url_for('dashboard'))
    
    # Create a PDF report
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        alignment=1
    )
    story.append(Paragraph(f"Group Report: {group.name}", title_style))
    story.append(Spacer(1, 12))
    
    # Group info
    story.append(Paragraph(f"Teacher: {group.teacher.full_name}", styles['Normal']))
    story.append(Paragraph(f"Created: {group.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Members
    story.append(Paragraph("Members:", styles['Heading2']))
    members = GroupMember.query.filter_by(group_id=group_id).all()
    member_data = [['Name', 'Joined Date']]
    for member in members:
        member_data.append([member.student.full_name, member.joined_at.strftime('%Y-%m-%d')])
    
    member_table = Table(member_data, colWidths=[3*inch, 2*inch])
    member_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(member_table)
    story.append(Spacer(1, 12))
    
    # Log entries
    story.append(Paragraph("Recent Log Entries:", styles['Heading2']))
    log_entries = LogEntry.query.filter_by(group_id=group_id).order_by(LogEntry.created_at.desc()).limit(10).all()
    
    for log in log_entries:
        story.append(Paragraph(f"{log.title} - by {log.student.full_name} on {log.created_at.strftime('%Y-%m-%d')}", styles['Heading3']))
        story.append(Paragraph(log.content, styles['Normal']))
        story.append(Spacer(1, 6))
    
    # Assignments
    story.append(Paragraph("Assignments:", styles['Heading2']))
    assignments = Assignment.query.filter_by(group_id=group_id).order_by(Assignment.due_date.asc()).all()
    assignment_data = [['Title', 'Due Date', 'Status']]
    
    for assignment in assignments:
        submission_count = Submission.query.filter_by(assignment_id=assignment.id).count()
        member_count = GroupMember.query.filter_by(group_id=group_id).count()
        status = f"{submission_count}/{member_count} submitted"
        assignment_data.append([assignment.title, assignment.due_date.strftime('%Y-%m-%d'), status])
    
    assignment_table = Table(assignment_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    assignment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(assignment_table)
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"report_{group.name}.pdf", mimetype='application/pdf')

@app.route('/api/timeline/<int:group_id>')
@login_required
def get_timeline_data(group_id):
    # Check if user has access to this group
    if current_user.role == 'student':
        membership = GroupMember.query.filter_by(
            group_id=group_id, 
            student_id=current_user.id
        ).first()
        if not membership:
            return jsonify({'error': 'Access denied'}), 403
    elif current_user.role == 'teacher':
        group = Group.query.get(group_id)
        if not group or group.teacher_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
    
    # Get log entries
    log_entries = LogEntry.query.filter_by(group_id=group_id).order_by(LogEntry.created_at.asc()).all()
    
    # Get assignments
    assignments = Assignment.query.filter_by(group_id=group_id).order_by(Assignment.due_date.asc()).all()
    
    timeline_data = []
    
    for log in log_entries:
        timeline_data.append({
            'id': f"log_{log.id}",
            'content': log.title,
            'start': log.created_at.strftime('%Y-%m-%d'),
            'type': 'point',
            'className': 'log-entry',
            'title': f"By: {log.student.full_name}",
            'description': log.content[:100] + '...' if len(log.content) > 100 else log.content
        })
    
    for assignment in assignments:
        timeline_data.append({
            'id': f"assignment_{assignment.id}",
            'content': assignment.title,
            'start': assignment.due_date.strftime('%Y-%m-%d'),
            'type': 'point',
            'className': 'assignment',
            'title': 'Assignment Due',
            'description': assignment.description[:100] + '...' if len(assignment.description) > 100 else assignment.description
        })
    
    return jsonify(timeline_data)

@app.route('/profile/update', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        try:
            # Update basic profile information
            current_user.full_name = request.form.get('full_name')
            current_user.email = request.form.get('email')
            current_user.contact_details = request.form.get('contact_details')
            
            # Handle profile picture upload
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename != '':
                    if allowed_file(file.filename):
                        # Delete old profile picture if exists
                        if current_user.profile_picture:
                            try:
                                old_file_path = os.path.join('static', current_user.profile_picture)
                                if os.path.exists(old_file_path):
                                    os.remove(old_file_path)
                            except Exception as e:
                                print(f"Error deleting old file: {e}")
                        
                        # Save new profile picture
                        profile_picture = save_file(file, 'profiles')
                        if profile_picture:
                            current_user.profile_picture = profile_picture
                            flash('Profile picture updated successfully!', 'success')
                    else:
                        flash('Invalid file type. Please use JPG, PNG, or GIF images.', 'danger')
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating profile: {e}")
            flash('Error updating profile. Please try again.', 'danger')
        
        return redirect(url_for('update_profile'))
    
    return render_template('dashboard/profile.html')

# Create upload directories if they don't exist
with app.app_context():
    upload_dirs = ['profiles', 'submissions', 'media', 'questions']
    for directory in upload_dirs:
        dir_path = os.path.join(app.config['UPLOAD_FOLDER'], directory)
        os.makedirs(dir_path, exist_ok=True)
        print(f"Created directory: {dir_path}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)