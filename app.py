"""
CleanCity – Garbage Reporting System with CNN
=============================================
Run this file in PyCharm (or `python app.py`) to start the web app.

How CNN is used:
  1. User uploads a garbage photo
  2. The CNN model (MobileNetV2, trained by train.py) analyzes the photo
  3. It detects IF it's garbage and WHAT TYPE it is
  4. The team dashboard shows the AI result with confidence score

Settings (optional environment variables):
  TEAM_PASSWORD  password for the team dashboard   (default: cleancity)
  SECRET_KEY     key that signs login cookies      (default: random, saved in instance/)
  FLASK_DEBUG    set to 1 to enable debug mode     (default: off)
"""

import hmac
import io
import os
import secrets
import uuid
from collections import Counter
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from PIL import Image, ImageOps, UnidentifiedImageError

from database import STATUSES, ReportDB
from model.garbage_classifier import (GARBAGE_CLASSES, TF_AVAILABLE, load_model,
                                      load_model_info, predict_garbage)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_DESCRIPTION    = 500

# All reports come from the university campus
CAMPUS = {
    'latitude':  '24.9200',
    'longitude': '67.0650',
    'address':   'Sir Syed University of Engineering & Technology, Karachi',
    'district':  'District East (Gulshan Town)',
}

STATUS_LABELS = {
    'pending':     'Pending triage',
    'in_progress': 'In progress',
    'done':        'Cleaned',
    'rejected':    'Rejected',
}


def time_ago(timestamp):
    """'2026-10-02 11:06:00' → '12m ago' / '3h ago' / 'Yesterday' / '14 May'."""
    try:
        then = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return '—'
    seconds = (datetime.now() - then).total_seconds()
    if seconds < 60:
        return 'just now'
    if seconds < 3600:
        return f'{int(seconds // 60)}m ago'
    if seconds < 86400:
        return f'{int(seconds // 3600)}h ago'
    if seconds < 2 * 86400:
        return 'Yesterday'
    if seconds < 7 * 86400:
        return f'{int(seconds // 86400)}d ago'
    return then.strftime('%d %b %Y')


def nice_time(timestamp):
    """'2026-10-02 11:06:00' → '02 Oct 2026, 11:06'"""
    try:
        return datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y, %H:%M')
    except (TypeError, ValueError):
        return timestamp or '—'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_secret_key(instance_dir):
    """Use SECRET_KEY env var, or create a random one once and keep it in instance/."""
    if os.environ.get('SECRET_KEY'):
        return os.environ['SECRET_KEY']
    key_file = os.path.join(instance_dir, 'secret_key')
    if not os.path.exists(key_file):
        with open(key_file, 'w') as f:
            f.write(secrets.token_hex(32))
    with open(key_file) as f:
        return f.read().strip()


def save_photo(image, upload_dir):
    """
    Save the photo as a resized JPEG with a random name.
    Re-saving also removes hidden metadata (like the phone's GPS position).
    """
    image = image.convert('RGB')
    image.thumbnail((1600, 1600))
    filename = uuid.uuid4().hex + '.jpg'
    image.save(os.path.join(upload_dir, filename), 'JPEG', quality=85)
    return filename


def create_app(test_config=None):
    app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.update(
        UPLOAD_FOLDER=os.path.join(BASE_DIR, 'static', 'uploads'),
        DATABASE=os.path.join(app.instance_path, 'cleancity.db'),
        LEGACY_JSON=os.path.join(BASE_DIR, 'reports.json'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
        TEAM_PASSWORD=os.environ.get('TEAM_PASSWORD', 'cleancity'),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        CNN_MODEL=None,
        MODEL_TRAINED=False,
        LOAD_MODEL=True,
    )
    if test_config:
        app.config.update(test_config)
    app.secret_key = app.config.get('SECRET_KEY') or load_secret_key(app.instance_path)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db = ReportDB(app.config['DATABASE'])
    imported = db.import_json(app.config['LEGACY_JSON'])
    if imported:
        print(f"Imported {imported} report(s) from reports.json into SQLite.")

    # ── Load CNN Model once at startup ────────────────────────────────────────
    if app.config['LOAD_MODEL']:
        print("=" * 50)
        print("Loading CNN model (MobileNetV2)...")
        model, trained = load_model()
        app.config['CNN_MODEL'], app.config['MODEL_TRAINED'] = model, trained
        if trained:
            print("Trained CNN model loaded successfully!")
        elif not TF_AVAILABLE:
            print("WARNING: TensorFlow not installed — run: pip install -r requirements.txt")
        else:
            print("WARNING: No trained model found — run: python train.py --data-dir dataset")
        print("=" * 50)

    # ── Security helpers ──────────────────────────────────────────────────────
    def team_required(view):
        """Only logged-in team members can open the dashboard."""
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not session.get('team'):
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Login required'}), 401
                return redirect(url_for('team_login', next=request.path))
            return view(*args, **kwargs)
        return wrapper

    def csrf_token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_hex(16)
        return session['csrf']

    @app.context_processor
    def inject_helpers():
        return {'csrf_token': csrf_token, 'status_labels': STATUS_LABELS,
                'logged_in': bool(session.get('team')), 'campus': CAMPUS,
                'model_trained': app.config['MODEL_TRAINED'], 'model_info': load_model_info()}

    app.jinja_env.filters['ago'] = time_ago
    app.jinja_env.filters['nice_time'] = nice_time

    @app.before_request
    def check_csrf():
        """Every team form must carry the secret token from the page (stops fake form posts)."""
        if request.method == 'POST' and request.endpoint != 'submit_report':
            sent     = request.form.get('csrf_token', '')
            expected = session.get('csrf', '')
            if not expected or not hmac.compare_digest(sent, expected):
                abort(400, 'Invalid or expired form. Please reload the page.')

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({'success': False, 'error': 'Photo is too large (max 16MB)'}), 413

    # ── USER ROUTES ───────────────────────────────────────────────────────────
    @app.route('/')
    def user_home():
        return render_template('user.html')

    @app.route('/submit', methods=['POST'])
    def submit_report():
        photo = request.files.get('photo')
        if photo is None or photo.filename == '' or not allowed_file(photo.filename):
            return jsonify({'success': False,
                            'error': 'Please choose a photo (PNG, JPG, GIF or WEBP)'}), 400

        image_bytes = photo.read()
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()                          # make sure it's really a valid image
            image = ImageOps.exif_transpose(image)
        except (UnidentifiedImageError, OSError):
            return jsonify({'success': False, 'error': 'That file is not a valid image'}), 400

        description = request.form.get('description', '').strip()[:MAX_DESCRIPTION]

        # ── Run CNN Prediction ────────────────────────────────────────────────
        ai_result = predict_garbage(image_bytes, app.config['CNN_MODEL'])
        app.logger.info("CNN result: %s (%s%%)", ai_result['garbage_type'], ai_result['confidence'])

        filename  = save_photo(image, app.config['UPLOAD_FOLDER'])
        report_id = db.add(filename, CAMPUS['latitude'], CAMPUS['longitude'], CAMPUS['address'],
                           description or 'No description', ai_result)

        report = db.get(report_id)
        return jsonify({'success': True, 'report_id': report_id, 'ai_result': ai_result,
                        'submitted_at': nice_time(report['submitted_at']),
                        'photo_url': url_for('static', filename='uploads/' + filename)})

    # ── TEAM ROUTES ───────────────────────────────────────────────────────────
    @app.route('/team/login', methods=['GET', 'POST'])
    def team_login():
        if request.method == 'POST':
            password = request.form.get('password', '')
            if hmac.compare_digest(password.encode(), app.config['TEAM_PASSWORD'].encode()):
                session.clear()
                session['team'] = True
                next_url = request.args.get('next', '')
                # Only redirect to pages on this site
                if not next_url.startswith('/') or next_url.startswith('//'):
                    next_url = url_for('team_dashboard')
                return redirect(next_url)
            flash('Wrong password. Please try again.')
        return render_template('login.html')

    @app.route('/team/logout', methods=['POST'])
    def team_logout():
        session.clear()
        return redirect(url_for('user_home'))

    @app.route('/team')
    @team_required
    def team_dashboard():
        reports = db.all()
        events  = db.all_events()
        for r in reports:
            # Reports created before the audit trail existed get a basic history
            r['events'] = events.get(r['id']) or [
                {'at': r['submitted_at'], 'message': 'Report submitted by citizen via web form'},
                {'at': r['submitted_at'], 'message': db.describe_ai(r['ai_result'])}]
            r['ago'] = time_ago(r['submitted_at'])
            r['photo_url'] = url_for('static', filename='uploads/' + r['photo'])

        status_counts = Counter(r['status'] for r in reports)
        type_counts = Counter(r['ai_result'].get('garbage_type', 'Unknown') for r in reports
                              if r['status'] != 'rejected')
        critical = sum(1 for r in reports
                       if r['ai_result'].get('danger_level') == 'High' and r['status'] == 'pending')
        day_ago = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        last_24h = sum(1 for r in reports if r['submitted_at'] >= day_ago)
        closed = status_counts['done'] + status_counts['rejected']
        resolution_rate = round(status_counts['done'] / closed * 100, 1) if closed else None

        return render_template('team.html',
                               reports=reports,
                               total=len(reports),
                               last_24h=last_24h,
                               pending=status_counts['pending'],
                               critical=critical,
                               in_progress=status_counts['in_progress'],
                               done=status_counts['done'],
                               resolution_rate=resolution_rate,
                               garbage_classes=GARBAGE_CLASSES + ['Unknown'],
                               type_counts=type_counts,
                               last_updated=datetime.now().strftime('%d %b %Y, %H:%M'))

    @app.route('/update_status', methods=['POST'])
    @team_required
    def update_status():
        report_id  = request.form.get('report_id', type=int)
        new_status = request.form.get('status')
        if report_id is None or new_status not in STATUSES:
            abort(400, 'Invalid report or status')
        if not db.set_status(report_id, new_status):
            abort(404, 'Report not found')
        flash(f'Report #{report_id} marked as {STATUS_LABELS[new_status].lower()}.')
        return redirect(url_for('team_dashboard', open=report_id))

    @app.route('/reclassify', methods=['POST'])
    @team_required
    def reclassify():
        """Run the CNN again on a stored photo (e.g. after retraining the model)."""
        report_id = request.form.get('report_id', type=int)
        report = db.get(report_id) if report_id is not None else None
        if report is None:
            abort(404, 'Report not found')
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(report['photo']))
        if not os.path.exists(photo_path):
            abort(404, 'Photo file is missing')
        with open(photo_path, 'rb') as f:
            ai_result = predict_garbage(f.read(), app.config['CNN_MODEL'])
        db.set_ai_result(report_id, ai_result)
        flash(f"Report #{report_id} re-classified: {ai_result['garbage_type']} "
              f"({ai_result['confidence']}%).")
        return redirect(url_for('team_dashboard', open=report_id))

    @app.route('/delete_report', methods=['POST'])
    @team_required
    def delete_report():
        report_id = request.form.get('report_id', type=int)
        report = db.delete(report_id) if report_id is not None else None
        if report is None:
            abort(404, 'Report not found')
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(report['photo']))
        if os.path.exists(photo_path):
            os.remove(photo_path)
        flash(f'Report #{report_id} deleted.')
        return redirect(url_for('team_dashboard'))

    @app.route('/api/reports')
    @team_required
    def api_reports():
        return jsonify(db.all(newest_first=False))

    return app


# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app = create_app()
    if 'TEAM_PASSWORD' not in os.environ:
        print("NOTE: Team dashboard password is the default 'cleancity'.")
        print("      Set the TEAM_PASSWORD environment variable to change it.")
    print("\nServer running at: http://127.0.0.1:5000")
    print("Team dashboard:    http://127.0.0.1:5000/team\n")
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
