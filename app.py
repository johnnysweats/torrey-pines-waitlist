"""
Torrey Pines Waitlist Automation - Main Application
"""

import os
import sqlite3
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from automation import run_waitlist_automation
import threading
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database setup
DATABASE = os.environ.get('DATABASE_PATH', 'jobs.db')
PACIFIC_TZ = pytz.timezone('America/Los_Angeles')

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database"""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            course TEXT NOT NULL,
            players INTEGER NOT NULL,
            scheduled_time TEXT,
            status TEXT DEFAULT 'pending',
            result_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# Initialize scheduler
jobstores = {
    'default': SQLAlchemyJobStore(url=f'sqlite:///{DATABASE}')
}
scheduler = BackgroundScheduler(jobstores=jobstores, timezone=PACIFIC_TZ)

def run_job(job_id):
    """Execute a waitlist automation job"""
    logger.info(f"Running job {job_id}")
    
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    # Update status to running
    conn.execute('UPDATE jobs SET status = ? WHERE id = ?', ('running', job_id))
    conn.commit()
    
    try:
        result = run_waitlist_automation(
            first_name=job['first_name'],
            last_name=job['last_name'],
            email=job['email'],
            phone=job['phone'],
            course=job['course'],
            players=str(job['players']),
            headless=True
        )
        
        status = 'completed' if result['status'] == 'success' else 'failed'
        message = result['message']
        
    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {e}")
        status = 'failed'
        message = f"Error: {str(e)}"
    
    # Update job with result
    conn.execute('''
        UPDATE jobs 
        SET status = ?, result_message = ?, completed_at = ?
        WHERE id = ?
    ''', (status, message, datetime.now(PACIFIC_TZ).isoformat(), job_id))
    conn.commit()
    conn.close()
    
    logger.info(f"Job {job_id} completed with status: {status}")

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get all jobs"""
    conn = get_db()
    jobs = conn.execute('''
        SELECT * FROM jobs 
        ORDER BY 
            CASE status 
                WHEN 'running' THEN 1 
                WHEN 'pending' THEN 2 
                WHEN 'completed' THEN 3 
                WHEN 'failed' THEN 4 
            END,
            created_at DESC
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(job) for job in jobs])

@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Create a new job"""
    data = request.json
    
    # Validate required fields
    required = ['firstName', 'lastName', 'email', 'phone', 'course', 'players']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    conn = get_db()
    
    scheduled_time = data.get('scheduledTime')
    run_now = data.get('runNow', False)
    
    cursor = conn.execute('''
        INSERT INTO jobs (first_name, last_name, email, phone, course, players, scheduled_time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['firstName'],
        data['lastName'],
        data['email'],
        data['phone'],
        data['course'],
        int(data['players']),
        scheduled_time if not run_now else None,
        'pending'
    ))
    
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    if run_now:
        # Run immediately in background thread
        logger.info(f"Running job {job_id} immediately")
        thread = threading.Thread(target=run_job, args=(job_id,))
        thread.start()
    elif scheduled_time:
        # Schedule for later
        try:
            # Parse the scheduled time (expected format: "2024-01-15T04:30")
            run_time = datetime.fromisoformat(scheduled_time)
            run_time = PACIFIC_TZ.localize(run_time)
            
            scheduler.add_job(
                run_job,
                'date',
                run_date=run_time,
                args=[job_id],
                id=f'job_{job_id}',
                replace_existing=True
            )
            logger.info(f"Scheduled job {job_id} for {run_time}")
        except Exception as e:
            logger.error(f"Failed to schedule job {job_id}: {e}")
            return jsonify({'error': f'Failed to schedule: {str(e)}'}), 500
    
    return jsonify({'id': job_id, 'status': 'created'})

@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get a specific job"""
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    conn.close()
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(dict(job))

@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    """Update a pending job"""
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    
    if not job:
        conn.close()
        return jsonify({'error': 'Job not found'}), 404
    
    if job['status'] not in ['pending']:
        conn.close()
        return jsonify({'error': 'Can only edit pending jobs'}), 400
    
    data = request.json
    
    # Remove old scheduled job if exists
    try:
        scheduler.remove_job(f'job_{job_id}')
    except:
        pass
    
    conn.execute('''
        UPDATE jobs 
        SET first_name = ?, last_name = ?, email = ?, phone = ?, course = ?, players = ?, scheduled_time = ?
        WHERE id = ?
    ''', (
        data.get('firstName', job['first_name']),
        data.get('lastName', job['last_name']),
        data.get('email', job['email']),
        data.get('phone', job['phone']),
        data.get('course', job['course']),
        int(data.get('players', job['players'])),
        data.get('scheduledTime', job['scheduled_time']),
        job_id
    ))
    conn.commit()
    
    # Reschedule if needed
    scheduled_time = data.get('scheduledTime', job['scheduled_time'])
    if scheduled_time:
        try:
            run_time = datetime.fromisoformat(scheduled_time)
            run_time = PACIFIC_TZ.localize(run_time)
            
            scheduler.add_job(
                run_job,
                'date',
                run_date=run_time,
                args=[job_id],
                id=f'job_{job_id}',
                replace_existing=True
            )
        except Exception as e:
            logger.error(f"Failed to reschedule job {job_id}: {e}")
    
    conn.close()
    return jsonify({'status': 'updated'})

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a job"""
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    
    if not job:
        conn.close()
        return jsonify({'error': 'Job not found'}), 404
    
    # Remove scheduled job if exists
    try:
        scheduler.remove_job(f'job_{job_id}')
    except:
        pass
    
    conn.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'deleted'})

@app.route('/api/jobs/<int:job_id>/run', methods=['POST'])
def run_job_now(job_id):
    """Run a pending job immediately"""
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    
    if not job:
        conn.close()
        return jsonify({'error': 'Job not found'}), 404
    
    if job['status'] not in ['pending']:
        conn.close()
        return jsonify({'error': 'Can only run pending jobs'}), 400
    
    conn.close()
    
    # Remove scheduled job if exists
    try:
        scheduler.remove_job(f'job_{job_id}')
    except:
        pass
    
    # Run in background thread
    thread = threading.Thread(target=run_job, args=(job_id,))
    thread.start()
    
    return jsonify({'status': 'started'})

@app.route('/api/time')
def get_server_time():
    """Get current server time in Pacific timezone"""
    now = datetime.now(PACIFIC_TZ)
    return jsonify({
        'time': now.strftime('%Y-%m-%dT%H:%M'),
        'display': now.strftime('%B %d, %Y at %I:%M %p PST')
    })

if __name__ == '__main__':
    init_db()
    scheduler.start()
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
