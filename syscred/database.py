# -*- coding: utf-8 -*-
"""
Database Manager for SysCRED
===========================
Handles connection to Supabase (PostgreSQL) and defines models.
"""

import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class AnalysisResult(db.Model):
    """Stores the result of a credibility analysis."""
    __tablename__ = 'analysis_results'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    credibility_score = db.Column(db.Float, nullable=False)
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Metadata stored as JSON if supported, or simplified columns
    source_reputation = db.Column(db.String(50))
    fact_check_count = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'score': self.credibility_score,
            'summary': self.summary,
            'created_at': self.created_at.isoformat(),
            'source_reputation': self.source_reputation
        }

def init_db(app):
    """Initialize the database with the Flask app."""
    # Prefer SYSCRED_DATABASE_URL (pooler), then DATABASE_URL (direct)
    db_url = os.environ.get('SYSCRED_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    # Fallback to SQLite in a writable directory
    if not db_url:
        import tempfile
        db_path = os.path.join(tempfile.gettempdir(), 'syscred.db')
        db_url = f'sqlite:///{db_path}'
        print(f"[SysCRED-DB] No DATABASE_URL, using SQLite: {db_path}")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    # Create tables if they don't exist (basic migration)
    with app.app_context():
        try:
            db.create_all()
            print("[SysCRED-DB] Database tables initialized.")
        except Exception as e:
            print(f"[SysCRED-DB] Warning: create_all failed: {e}")
