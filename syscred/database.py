# -*- coding: utf-8 -*-
"""
Database Manager for SysCRED
=============================
Handles connection to Supabase using REST API (PostgREST) for HF Spaces compatibility.
"""

import os
import requests
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

# Supabase REST API configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://zmluirvqfkmfazqitqgi.supabase.co')
# Use service role key for insert operations (SUPABASE_SECRET_KEY in HF Secrets)
SUPABASE_KEY = os.environ.get('SUPABASE_SECRET_KEY', os.environ.get('SUPABASE_SERVICE_ROLE_KEY', ''))
# Fallback to anon key for read operations
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_KEY', '')

class SupabaseClient:
    """REST API client for Supabase (PostgREST)."""
    
    def __init__(self):
        self.url = SUPABASE_URL
        self.key = SUPABASE_KEY
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def insert(self, table, data):
        """Insert a row into a table."""
        try:
            response = requests.post(
                f"{self.url}/rest/v1/{table}",
                json=data,
                headers=self.headers
            )
            if response.status_code not in [200, 201, 204]:
                print(f"[Supabase REST] Insert failed: {response.status_code} - {response.text[:200]}")
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"[Supabase REST] Insert error: {e}")
            return False
    
    def select(self, table, filters=None):
        """Select rows from a table."""
        try:
            params = filters or {}
            response = requests.get(
                f"{self.url}/rest/v1/{table}",
                params=params,
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"[Supabase REST] Select error: {e}")
            return []
    
    def count(self, table):
        """Count rows in a table."""
        try:
            response = requests.get(
                f"{self.url}/rest/v1/{table}",
                params={'select': 'count', 'count': 'exact'},
                headers=self.headers
            )
            if response.status_code == 200:
                return int(response.headers.get('Content-Range', '0-0').split('/')[-1])
            return 0
        except Exception as e:
            print(f"[Supabase REST] Count error: {e}")
            return 0
    
    def upsert_source(self, domain, reputation_score, analysis_count=1):
        """Insert or update a source (domain) in sources table."""
        try:
            # First check if source exists
            existing = self.select('sources', {'domain': f'eq.{domain}'})
            
            if existing:
                # Update existing source
                current = existing[0]
                new_count = current.get('analysis_count', 0) + analysis_count
                
                # Use PATCH to update
                response = requests.patch(
                    f"{self.url}/rest/v1/sources?domain=eq.{domain}",
                    json={
                        'reputation_score': reputation_score,
                        'analysis_count': new_count
                    },
                    headers=self.headers
                )
                if response.status_code in [200, 204]:
                    print(f"[Supabase] Updated source: {domain} (count: {new_count})")
                    return True
            else:
                # Insert new source
                response = requests.post(
                    f"{self.url}/rest/v1/sources",
                    json={
                        'domain': domain,
                        'reputation_score': reputation_score,
                        'analysis_count': analysis_count
                    },
                    headers=self.headers
                )
                if response.status_code in [200, 201]:
                    print(f"[Supabase] Inserted new source: {domain}")
                    return True
            
            print(f"[Supabase] Source upsert failed: {response.status_code} - {response.text[:100]}")
            return False
        except Exception as e:
            print(f"[Supabase REST] Upsert source error: {e}")
            return False


# Global Supabase client
supabase_client = None

def get_supabase():
    """Get or create Supabase client."""
    global supabase_client
    if supabase_client is None:
        if SUPABASE_KEY:
            supabase_client = SupabaseClient()
            print("[SysCRED-DB] Supabase REST client initialized")
        else:
            print("[SysCRED-DB] Warning: No SUPABASE_KEY, Supabase disabled")
    return supabase_client


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
    # Use SQLite fallback - Supabase operations use REST API separately
    import tempfile
    db_path = os.path.join(tempfile.gettempdir(), 'syscred.db')
    db_url = f'sqlite:///{db_path}'
    print(f"[SysCRED-DB] Using SQLite (Supabase uses REST API): {db_path}")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            print("[SysCRED-DB] Database tables initialized.")
        except Exception as e:
            print(f"[SysCRED-DB] Warning: create_all failed: {e}")
    
    # Initialize Supabase REST client
    get_supabase()
