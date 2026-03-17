# -*- coding: utf-8 -*-
"""
SysCRED Backend API - Flask Server
===================================
REST API for the credibility verification system.

Endpoints:
- POST /api/verify - Verify URL or text credibility
- POST /api/seo - Get SEO analysis only
- GET /api/ontology/stats - Get ontology statistics
- GET /api/health - Health check
- GET /api/config - View current configuration

(c) Dominique S. Loyer - PhD Thesis Prototype
"""

import sys
import os
import traceback

# Load environment variables from .env file
from pathlib import Path
try:
    from dotenv import load_dotenv
    # .env is at project root (parent of syscred/)
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if not env_path.exists():
        # Fallback: check syscred/ directory
        env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[SysCRED Backend] Loaded .env from {env_path}")
    else:
        print(f"[SysCRED Backend] No .env file found, using system env vars")
except ImportError:
    print("[SysCRED Backend] python-dotenv not installed, using system env vars")

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Add syscred package to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import SysCRED modules (with graceful fallbacks)
SYSCRED_AVAILABLE = False
TREC_AVAILABLE = False
DB_AVAILABLE = False

# Core modules (required)
try:
    from syscred.verification_system import CredibilityVerificationSystem
    from syscred.seo_analyzer import SEOAnalyzer
    from syscred.ontology_manager import OntologyManager
    from syscred.config import config, Config
    SYSCRED_AVAILABLE = True
    print("[SysCRED Backend] Core modules imported successfully")
except ImportError as e:
    print(f"[SysCRED Backend] Warning: Core modules failed: {e}")
    # Fallback config
    class Config:
        HOST = "0.0.0.0"
        PORT = 5000
        DEBUG = True
        ONTOLOGY_BASE_PATH = None
        ONTOLOGY_DATA_PATH = None
        LOAD_ML_MODELS = True
        GOOGLE_FACT_CHECK_API_KEY = None
    config = Config()

# Database (optional)
try:
    from syscred.database import init_db, db, AnalysisResult, get_supabase
    DB_AVAILABLE = True
    print("[SysCRED Backend] Database module loaded")
except ImportError as e:
    print(f"[SysCRED Backend] Database disabled: {e}")
    def init_db(app): pass
    def get_supabase(): return None

# TREC modules (optional)
try:
    from syscred.trec_retriever import TRECRetriever, Evidence, RetrievalResult
    from syscred.eval_metrics import EvaluationMetrics
    TREC_AVAILABLE = True
    print("[SysCRED Backend] TREC modules loaded")
except ImportError as e:
    print(f"[SysCRED Backend] TREC modules disabled: {e}")

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Allow iframe embedding on UQAM domains (for syscred.uqam.ca mirror)
@app.after_request
def add_security_headers(response):
    """Add security headers allowing UQAM iframe embedding."""
    response.headers['X-Frame-Options'] = 'ALLOW-FROM https://syscred.uqam.ca'
    response.headers['Content-Security-Policy'] = (
        "frame-ancestors 'self' https://syscred.uqam.ca https://*.uqam.ca"
    )
    return response

# Initialize Database
try:
    init_db(app) # [NEW] Setup DB connection
except Exception as e:
    print(f"[SysCRED Backend] Warning: DB init failed: {e}")

# --- Initialize SysCRED System ---
credibility_system = None
seo_analyzer = None
trec_retriever = None
eval_metrics = None

# --- Load TREC Corpus and Qrels from dataset files ---

import json as _json
from pathlib import Path as _Path
from collections import defaultdict as _defaultdict

def _load_trec_corpus():
    """Load TREC corpus from datasets/trec/corpus.jsonl."""
    corpus = {}
    corpus_path = None
    
    # Try config path first
    if SYSCRED_AVAILABLE:
        corpus_path = getattr(Config, 'TREC_CORPUS_PATH', None)
    
    # Fallback to local datasets dir
    if not corpus_path:
        local_path = _Path(__file__).parent / "datasets" / "trec" / "corpus.jsonl"
        if local_path.exists():
            corpus_path = str(local_path)
    
    if corpus_path and os.path.exists(corpus_path):
        try:
            with open(corpus_path, 'r', encoding='utf-8') as f:
                for line in f:
                    doc = _json.loads(line.strip())
                    doc_id = doc.get('id', '')
                    corpus[doc_id] = {
                        'text': doc.get('contents', doc.get('text', '')),
                        'title': doc.get('title', ''),
                        'topic': doc.get('topic', 'general')
                    }
            print(f"[SysCRED Backend] TREC corpus loaded: {len(corpus)} documents from {corpus_path}")
        except Exception as e:
            print(f"[SysCRED Backend] TREC corpus load error: {e}")
    else:
        print(f"[SysCRED Backend] TREC corpus file not found, using empty corpus")
    
    return corpus


def _load_trec_qrels():
    """Load TREC qrels from datasets/trec/qrels.txt."""
    # topic_id -> set of relevant doc_ids
    qrels_by_topic = _defaultdict(set)
    # topic_id -> {doc_id: relevance}
    qrels_graded = _defaultdict(dict)
    qrels_path = None
    
    if SYSCRED_AVAILABLE:
        qrels_path = getattr(Config, 'TREC_QRELS_PATH', None)
    
    if not qrels_path:
        local_path = _Path(__file__).parent / "datasets" / "trec" / "qrels.txt"
        if local_path.exists():
            qrels_path = str(local_path)
    
    if qrels_path and os.path.exists(qrels_path):
        try:
            with open(qrels_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        topic_id, _, doc_id, relevance = parts[:4]
                        rel = int(relevance)
                        qrels_graded[topic_id][doc_id] = rel
                        if rel > 0:
                            qrels_by_topic[topic_id].add(doc_id)
            print(f"[SysCRED Backend] TREC qrels loaded: {sum(len(v) for v in qrels_graded.values())} judgments for {len(qrels_graded)} topics")
        except Exception as e:
            print(f"[SysCRED Backend] TREC qrels load error: {e}")
    else:
        print(f"[SysCRED Backend] TREC qrels file not found")
    
    return dict(qrels_by_topic), dict(qrels_graded)


# Load at module level
TREC_CORPUS = _load_trec_corpus()
TREC_QRELS_BY_TOPIC, TREC_QRELS_GRADED = _load_trec_qrels()

# Build reverse mapping: doc_id -> set of topics (for topic matching)
TREC_DOC_TOPICS = {}
for doc_id, doc in TREC_CORPUS.items():
    TREC_DOC_TOPICS[doc_id] = doc.get('topic', 'general')



def initialize_system():
    """Initialize the credibility system (lazy loading)."""
    global credibility_system, seo_analyzer
    
    if not SYSCRED_AVAILABLE:
        print("[SysCRED Backend] Cannot initialize - modules not available")
        return False
    
    try:
        # Initialize SEO analyzer (lightweight)
        seo_analyzer = SEOAnalyzer()
        print("[SysCRED Backend] SEO Analyzer initialized")
        
        # Initialize full system (may take time to load ML models)
        print("[SysCRED Backend] Initializing credibility system (loading ML models)...")
        ontology_base = str(config.ONTOLOGY_BASE_PATH) if config.ONTOLOGY_BASE_PATH else None
        ontology_data = str(config.ONTOLOGY_DATA_PATH) if config.ONTOLOGY_DATA_PATH else None
        credibility_system = CredibilityVerificationSystem(
            ontology_base_path=ontology_base if ontology_base and os.path.exists(ontology_base) else None,
            ontology_data_path=ontology_data,
            load_ml_models=config.LOAD_ML_MODELS,
            google_api_key=config.GOOGLE_FACT_CHECK_API_KEY
        )
        print("[SysCRED Backend] System initialized successfully!")
        return True
        
    except Exception as e:
        print(f"[SysCRED Backend] Error initializing system: {e}")
        traceback.print_exc()
        return False

# --- API Routes ---

@app.route('/')
def index():
    """Serve the frontend."""
    return send_from_directory('static', 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'syscred_available': SYSCRED_AVAILABLE,
        'system_initialized': credibility_system is not None,
        'seo_analyzer_ready': seo_analyzer is not None
    })


@app.route('/api/verify', methods=['POST'])
def verify_endpoint():
    """
    Main verification endpoint.
    
    Request JSON:
    {
        "input_data": "URL or text to verify",
        "include_seo": true/false (optional, default true),
        "include_pagerank": true/false (optional, default true)
    }
    """
    global credibility_system
    
    # Lazy initialization
    if credibility_system is None:
        if not initialize_system():
            return jsonify({
                'error': 'System initialization failed. Check server logs.'
            }), 503
    
    # Validate request
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    input_data = data.get('input_data', '').strip()
    
    if not input_data:
        return jsonify({'error': "'input_data' is required"}), 400
    
    include_seo = data.get('include_seo', True)
    include_pagerank = data.get('include_pagerank', True)
    
    print(f"[SysCRED Backend] Verifying: {input_data[:100]}...")
    
    try:
        # Run main verification
        result = credibility_system.verify_information(input_data)
        
        if 'error' in result:
            return jsonify(result), 400
        
        # Add SEO analysis if requested and it's a URL
        if include_seo and credibility_system.is_url(input_data):
            try:
                web_content = credibility_system.api_clients.fetch_web_content(input_data)
                if web_content.success:
                    seo_result = seo_analyzer.analyze_seo(
                        url=input_data,
                        title=web_content.title,
                        meta_description=web_content.meta_description,
                        text_content=web_content.text_content
                    )
                    result['seoAnalysis'] = {
                        'titleLength': seo_result.title_length,
                        'titleHasKeywords': seo_result.title_has_keywords,
                        'metaDescriptionLength': seo_result.meta_description_length,
                        'wordCount': seo_result.word_count,
                        'readabilityScore': round(seo_result.readability_score, 2),
                        'seoScore': round(seo_result.seo_score, 2),
                        'topKeywords': list(seo_result.keyword_density.keys())
                    }
            except Exception as e:
                print(f"[SysCRED Backend] SEO analysis error: {e}")
                result['seoAnalysis'] = {'error': str(e)}
        
        # Add PageRank estimation if requested
        if include_pagerank and credibility_system.is_url(input_data):
            try:
                external_data = credibility_system.api_clients.fetch_external_data(input_data)
                pr_result = seo_analyzer.estimate_pagerank(
                    url=input_data,
                    domain_age_days=external_data.domain_age_days,
                    source_reputation=external_data.source_reputation
                )
                result['pageRankEstimation'] = {
                    'estimatedPR': round(pr_result.estimated_pr, 3),
                    'confidence': round(pr_result.confidence, 2),
                    'factors': pr_result.factors,
                    'explanation': pr_result.explanation_text
                }
            except Exception as e:
                print(f"[SysCRED Backend] PageRank estimation error: {e}")
                result['pageRankEstimation'] = {'error': str(e)}
        
        print(f"[SysCRED Backend] Score: {result.get('scoreCredibilite', 'N/A')}")
        
        # [NEW] TREC Evidence Search + IR Metrics
        try:
            global trec_retriever, eval_metrics
            
            # Initialize TREC if needed
            if trec_retriever is None and TREC_AVAILABLE:
                trec_retriever = TRECRetriever(use_stemming=True, enable_prf=False)
                trec_retriever.corpus = TREC_CORPUS
                eval_metrics = EvaluationMetrics()
                print(f"[SysCRED Backend] TREC Retriever initialized with {len(TREC_CORPUS)} documents")
            
            if trec_retriever and eval_metrics:
                import time
                start_time = time.time()
                
                # Use the input text as query
                query_text = input_data[:200] if not credibility_system.is_url(input_data) else result.get('informationEntree', input_data)[:200]
                
                trec_result = trec_retriever.retrieve_evidence(query_text, k=10, model='bm25')
                search_time = (time.time() - start_time) * 1000
                
                retrieved_ids = [e.doc_id for e in trec_result.evidences]
                
                # Map document topic labels to qrel topic IDs
                _TOPIC_LABEL_TO_ID = {
                    'climate': '101', 'factcheck': '102', 'health': '103',
                    'bias': '104', 'media': '105', 'credibility': '108',
                    'disinfo': '107', 'economy': '109', 'tech': '110',
                    'environment': '111', 'education': '112', 'politics': '105',
                    'science': '106',
                }
                
                # Determine best matching qrel topic from retrieved docs
                topic_scores = {}
                for doc_id in retrieved_ids:
                    doc_topic = TREC_DOC_TOPICS.get(doc_id, 'general')
                    qrel_topic_id = _TOPIC_LABEL_TO_ID.get(doc_topic, '108')  # default: credibility
                    topic_scores[qrel_topic_id] = topic_scores.get(qrel_topic_id, 0) + 1
                
                best_topic_id = max(topic_scores, key=topic_scores.get) if topic_scores else '108'
                relevant_ids = TREC_QRELS_BY_TOPIC.get(best_topic_id, set())
                graded_relevance = TREC_QRELS_GRADED.get(best_topic_id, {})
                
                # Compute IR metrics
                k = len(retrieved_ids) if retrieved_ids else 1
                precision = eval_metrics.precision_at_k(retrieved_ids, relevant_ids, k) if retrieved_ids else 0
                recall = eval_metrics.recall_at_k(retrieved_ids, relevant_ids, k) if retrieved_ids else 0
                ap = eval_metrics.average_precision(retrieved_ids, relevant_ids) if retrieved_ids else 0
                mrr = eval_metrics.mrr(retrieved_ids, relevant_ids) if retrieved_ids else 0
                
                # Use graded relevance for NDCG
                relevance_dict = graded_relevance if graded_relevance else {doc: 1 for doc in relevant_ids}
                ndcg = eval_metrics.ndcg_at_k(retrieved_ids, relevance_dict, k) if retrieved_ids else 0
                
                # BM25 score from top result
                tfidf_score = trec_result.evidences[0].score if trec_result.evidences else 0
                
                # Evidence snippets for display
                evidence_snippets = []
                for ev in trec_result.evidences[:5]:
                    doc_info = TREC_CORPUS.get(ev.doc_id, {})
                    evidence_snippets.append({
                        'doc_id': ev.doc_id,
                        'title': doc_info.get('title', ''),
                        'score': round(ev.score, 4),
                        'snippet': ev.text[:200] if ev.text else ''
                    })
                
                result['trec_metrics'] = {
                    'precision': round(precision, 4),
                    'recall': round(recall, 4),
                    'map': round(ap, 4),
                    'ndcg': round(ndcg, 4),
                    'tfidf_score': round(tfidf_score, 4),
                    'mrr': round(mrr, 4),
                    'retrieved_count': len(retrieved_ids),
                    'corpus_size': len(TREC_CORPUS),
                    'search_time_ms': round(search_time, 2),
                    'matched_topic': best_topic_id,
                    'evidence_snippets': evidence_snippets
                }
                print(f"[SysCRED Backend] TREC: P={precision:.3f} R={recall:.3f} MAP={ap:.3f} NDCG={ndcg:.3f} MRR={mrr:.3f} Topic={best_topic_id}")
        except Exception as e:
            print(f"[SysCRED Backend] TREC metrics error: {e}")
            result['trec_metrics'] = {'error': str(e)}
        
        # [NEW] Persist to Database (SQLite + Supabase REST)
        try:
            # Extract domain for sources table
            domain = None
            if credibility_system and credibility_system.is_url(input_data):
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(input_data).netloc
                except:
                    pass
            
            source_reputation = result.get('detailsScore', {}).get('factors', [{}])[0].get('value')
            
            # Save to SQLite
            new_analysis = AnalysisResult(
                url=input_data[:500],
                credibility_score=result.get('scoreCredibilite', 0.5),
                summary=result.get('resumeAnalyse', ''),
                source_reputation=source_reputation
            )
            db.session.add(new_analysis)
            db.session.commit()
            print(f"[SysCRED-DB] Result saved to SQLite. ID: {new_analysis.id}")
            
            # Also save to Supabase via REST API
            try:
                from syscred.database import get_supabase
                supabase = get_supabase()
                if supabase:
                    supabase.insert('analysis_results', {
                        'url': input_data[:500],
                        'credibility_score': result.get('scoreCredibilite', 0.5),
                        'summary': result.get('resumeAnalyse', ''),
                        'source_reputation': source_reputation
                    })
                    print(f"[SysCRED-DB] Result synced to Supabase")
                    
                    # Sync source (domain)
                    if domain and source_reputation:
                        # Convert reputation to numeric score
                        rep_score = 0.5
                        if source_reputation in ['High', 'high', '5 found']:
                            rep_score = 0.8
                        elif source_reputation in ['Medium', 'medium']:
                            rep_score = 0.5
                        elif source_reputation in ['Low', 'low', 'Unknown']:
                            rep_score = 0.2
                        
                        supabase.upsert_source(domain, rep_score)
            except Exception as supabase_err:
                print(f"[SysCRED-DB] Supabase sync failed: {supabase_err}")
                
        except Exception as e:
            print(f"[SysCRED-DB] Save failed: {e}")

        return jsonify(result), 200
        
    except Exception as e:
        print(f"[SysCRED Backend] Error: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Internal error: {str(e)}'}), 500


@app.route('/api/seo', methods=['POST'])
def seo_endpoint():
    """
    SEO-only analysis endpoint (faster, no ML models needed).
    
    Request JSON:
    {
        "url": "URL to analyze"
    }
    """
    global seo_analyzer
    
    if seo_analyzer is None:
        seo_analyzer = SEOAnalyzer()
    
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url or not url.startswith('http'):
        return jsonify({'error': 'Valid URL is required'}), 400
    
    try:
        # Fetch content
        from syscred.api_clients import ExternalAPIClients
        api_client = ExternalAPIClients()
        
        web_content = api_client.fetch_web_content(url)
        if not web_content.success:
            return jsonify({'error': f'Failed to fetch URL: {web_content.error}'}), 400
        
        # SEO analysis
        seo_result = seo_analyzer.analyze_seo(
            url=url,
            title=web_content.title,
            meta_description=web_content.meta_description,
            text_content=web_content.text_content
        )
        
        # IR metrics
        ir_metrics = seo_analyzer.get_ir_metrics(web_content.text_content)
        
        # PageRank estimation
        external_data = api_client.fetch_external_data(url)
        pr_result = seo_analyzer.estimate_pagerank(
            url=url,
            domain_age_days=external_data.domain_age_days,
            source_reputation=external_data.source_reputation
        )
        
        return jsonify({
            'url': url,
            'title': web_content.title,
            'seo': {
                'titleLength': seo_result.title_length,
                'metaDescriptionLength': seo_result.meta_description_length,
                'wordCount': seo_result.word_count,
                'readabilityScore': round(seo_result.readability_score, 2),
                'seoScore': round(seo_result.seo_score, 2),
                'keywordDensity': seo_result.keyword_density
            },
            'irMetrics': {
                'documentLength': ir_metrics.document_length,
                'topTerms': ir_metrics.top_terms[:5],
                'avgTermFrequency': round(ir_metrics.avg_term_frequency, 4)
            },
            'pageRank': {
                'estimated': round(pr_result.estimated_pr, 3),
                'confidence': round(pr_result.confidence, 2),
                'factors': pr_result.factors
            },
            'domain': {
                'reputation': external_data.source_reputation,
                'ageDays': external_data.domain_age_days
            }
        }), 200
        
    except Exception as e:
        print(f"[SysCRED Backend] SEO endpoint error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500



@app.route('/api/ontology/graph', methods=['GET'])
def ontology_graph():
    """Get ontology graph data for D3.js."""
    global credibility_system
    
    if credibility_system and credibility_system.ontology_manager:
        graph_data = credibility_system.ontology_manager.get_graph_json()
        return jsonify(graph_data), 200
    else:
        # Return empty graph rather than 400 to avoid breaking frontend
        return jsonify({'nodes': [], 'links': []}), 200


@app.route('/api/ontology/stats', methods=['GET'])
def ontology_stats():
    """Get ontology statistics."""
    global credibility_system
    
    if credibility_system and credibility_system.ontology_manager:
        stats = credibility_system.ontology_manager.get_statistics()
        return jsonify(stats), 200
    else:
        return jsonify({
            'error': 'Ontology not loaded',
            'base_triples': 0,
            'data_triples': 0
        }), 200


# --- TREC Endpoints ---

@app.route('/api/trec/search', methods=['POST'])
def trec_search():
    """
    Search for evidence using TREC retrieval methods.
    
    Request JSON:
    {
        "query": "Claim or query to search for",
        "k": 10,              # Number of results (optional, default 10)
        "model": "bm25"       # Retrieval model: bm25, tfidf, qld (optional)
    }
    
    Response:
    {
        "query": "original query",
        "results": [
            {"doc_id": "AP880101-0001", "score": 6.27, "rank": 1, "text": "...", "title": "..."},
            ...
        ],
        "total": 3,
        "model": "bm25",
        "search_time_ms": 12.5
    }
    """
    global trec_retriever, eval_metrics
    
    # Initialize TREC components if needed
    if trec_retriever is None:
        try:
            trec_retriever = TRECRetriever(use_stemming=True, enable_prf=False)
            trec_retriever.corpus = TREC_CORPUS
            eval_metrics = EvaluationMetrics()
            print(f"[SysCRED Backend] TREC Retriever initialized with {len(TREC_CORPUS)} documents")
        except Exception as e:
            return jsonify({'error': f'TREC initialization failed: {str(e)}'}), 503
    
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': "'query' is required"}), 400
    
    k = data.get('k', 10)
    model = data.get('model', 'bm25')
    
    try:
        import time
        start_time = time.time()
        
        # Retrieve evidence
        result = trec_retriever.retrieve_evidence(query, k=k, model=model)
        search_time_ms = (time.time() - start_time) * 1000
        
        # Format results
        results = []
        for ev in result.evidences:
            doc_info = trec_retriever.corpus.get(ev.doc_id, {})
            results.append({
                'doc_id': ev.doc_id,
                'score': round(ev.score, 4),
                'rank': ev.rank,
                'text': ev.text,
                'title': doc_info.get('title', ''),
                'model': ev.retrieval_model
            })
        
        return jsonify({
            'query': query,
            'results': results,
            'total': len(results),
            'model': model,
            'search_time_ms': round(search_time_ms, 2)
        }), 200
        
    except Exception as e:
        print(f"[SysCRED Backend] TREC search error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/trec/corpus', methods=['GET'])
def trec_corpus():
    """
    Get the TREC demo corpus information.
    
    Response:
    {
        "corpus_size": 7,
        "corpus_type": "AP88-90 Demo",
        "documents": [
            {"doc_id": "AP880101-0001", "title": "...", "text_preview": "..."},
            ...
        ]
    }
    """
    docs = []
    for doc_id, doc in TREC_CORPUS.items():
        docs.append({
            'doc_id': doc_id,
            'title': doc.get('title', ''),
            'text_preview': doc['text'][:150] + '...' if len(doc['text']) > 150 else doc['text']
        })
    
    return jsonify({
        'corpus_size': len(TREC_CORPUS),
        'corpus_type': 'AP88-90 SysCRED',
        'documents': docs
    }), 200


@app.route('/api/trec/metrics', methods=['POST'])
def trec_metrics():
    """
    Calculate IR evaluation metrics for a retrieval result.
    
    Request JSON:
    {
        "retrieved": ["AP880101-0001", "AP890215-0001", "AP880101-0002"],
        "relevant": ["AP880101-0001", "AP880101-0002", "AP880102-0001"]
    }
    
    Response:
    {
        "precision_at_3": 0.67,
        "recall_at_3": 0.67,
        "average_precision": 0.81,
        "mrr": 1.0,
        "ndcg_at_3": 0.88
    }
    """
    global eval_metrics
    
    if eval_metrics is None:
        eval_metrics = EvaluationMetrics()
    
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    retrieved = data.get('retrieved', [])
    relevant = set(data.get('relevant', []))
    
    if not retrieved:
        return jsonify({'error': "'retrieved' list is required"}), 400
    
    k = len(retrieved)
    
    try:
        # Calculate metrics
        p_at_k = eval_metrics.precision_at_k(retrieved, relevant, k)
        r_at_k = eval_metrics.recall_at_k(retrieved, relevant, k)
        ap = eval_metrics.average_precision(retrieved, relevant)
        mrr = eval_metrics.mrr(retrieved, relevant)
        
        # For NDCG, create relevance dict (binary: 1 if relevant, 0 otherwise)
        relevance_dict = {doc: 1 for doc in relevant}
        ndcg = eval_metrics.ndcg_at_k(retrieved, relevance_dict, k)
        
        return jsonify({
            f'precision_at_{k}': round(p_at_k, 4),
            f'recall_at_{k}': round(r_at_k, 4),
            'average_precision': round(ap, 4),
            'mrr': round(mrr, 4),
            f'ndcg_at_{k}': round(ndcg, 4),
            'metrics_explanation': {
                'P@K': 'Proportion de documents pertinents parmi les K premiers récupérés',
                'R@K': 'Proportion de documents pertinents récupérés parmi tous les pertinents',
                'AP': 'Moyenne des précisions à chaque document pertinent trouvé',
                'MRR': 'Rang réciproque du premier document pertinent',
                'NDCG': 'Gain cumulatif normalisé avec décroissance logarithmique'
            }
        }), 200
        
    except Exception as e:
        print(f"[SysCRED Backend] TREC metrics error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trec/health', methods=['GET'])
def trec_health():
    """Health check for TREC module."""
    return jsonify({
        'status': 'healthy',
        'trec_available': TREC_AVAILABLE if 'TREC_AVAILABLE' in dir() else True,
        'retriever_initialized': trec_retriever is not None,
        'corpus_size': len(TREC_CORPUS),
        'models_available': ['bm25', 'tfidf', 'qld']
    }), 200


# --- Main ---
if __name__ == '__main__':
    print("=" * 60)
    print("SysCRED Backend API Server")
    print("(c) Dominique S. Loyer - PhD Thesis Prototype")
    print("=" * 60)
    print()
    
    # Initialize system at startup
    print("[SysCRED Backend] Pre-initializing system...")
    initialize_system()
    
    print()
    print("[SysCRED Backend] Starting Flask server...")
    print("[SysCRED Backend] Endpoints:")
    print("  - POST /api/verify          - Full credibility verification")
    print("  - POST /api/seo             - SEO analysis only (faster)")
    print("  - GET  /api/ontology/stats  - Ontology statistics")
    print("  - GET  /api/health          - Health check")
    print("  --- TREC Endpoints ---")
    print("  - POST /api/trec/search     - Evidence retrieval (BM25/TF-IDF/QLD)")
    print("  - POST /api/trec/metrics    - Calculate IR metrics (MAP, P@K, NDCG)")
    print("  - GET  /api/trec/corpus     - Demo corpus info")
    print("  - GET  /api/trec/health     - TREC module health")
    print()
    
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
