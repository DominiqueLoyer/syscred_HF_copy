---
title: SysCRED - Système de Vérification de Crédibilité
emoji: 🔍
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# SysCRED - Credibility Verification System

A hybrid neuro-symbolic system for credibility verification and fact-checking.

## Features
- 🔍 URL and text credibility analysis
- 🧠 NLP-based coherence analysis with Transformers
- 📊 SEO and source reputation scoring
- 🌐 Knowledge graph visualization with D3.js
- 🔗 Ontology-based reasoning with RDFLib

## Author
**Dominique S. Loyer** - UQAM

## Usage

```bash
Enter a URL or paste text to analyze its credibility score based on multiple factors.
systemFactChecking_Production/
├── src/
│   └── syscred/                    ← Package Python principal
│       ├── __init__.py
│       ├── core/                   ← Cœur du système
│       │   ├── config.py           ← Configuration centralisée
│       │   ├── verification_system.py
│       │   └── scoring.py
│       ├── api/                    ← Interface web
│       │   ├── backend_app.py      ← Flask app
│       │   ├── routes/
│       │   └── middleware/
│       ├── ml/                     ← Modèles ML
│       │   ├── sentiment.py
│       │   ├── ner_analyzer.py     ← À fusionner depuis HF
│       │   └── eeat_calculator.py  ← À fusionner depuis HF
│       ├── graph/                  ← GraphRAG & Ontologie
│       │   ├── graph_rag.py
│       │   ├── ontology_manager.py
│       │   └── queries.py
│       ├── ir/                     ← TREC & Information Retrieval
│       │   ├── ir_engine.py
│       │   ├── trec_retriever.py
│       │   └── eval_metrics.py
│       ├── datasets/               ← Gestion datasets
│       │   └── liar_dataset.py
│       └── utils/                  ← Utilitaires
│           ├── api_clients.py
│           ├── database.py
│           └── helpers.py
│
├── data/                           ← Données (hors git pour gros fichiers)
│   ├── ontology/
│   │   ├── sysCRED_onto26avrtil.ttl
│   │   └── sysCRED_data.ttl
│   └── datasets/
│       ├── liar/                   ← Dataset LIAR
│       └── trec/                   ← Corpus TREC AP88-90 (276MB)
│
├── docs/                           ← Documentation
│   ├── DEV_LOGS/                   ← Journaux de développement
│   ├── PUBLICATIONS/               ← Papers et présentations
│   └── API.md
│
├── tests/                          ← Tests
│   ├── unit/
│   ├── integration/
│   └── benchmarks/
│
├── notebooks/                      ← Jupyter notebooks
│   └── exploration/
│
├── deploy/                         ← Configurations déploiement
│   ├── huggingface/                ← Spécifique HF Space
│   │   ├── Dockerfile.hf
│   │   ├── requirements-hf.txt
│   │   └── static/                 ← Assets HF
│   └── docker/                     ← Docker générique
│       ├── Dockerfile
│       └── docker-compose.yml
│
├── scripts/                        ← Scripts utilitaires
│   ├── start_syscred.sh
│   ├── deploy_huggingface.sh
│   └── run_benchmarks.py
│
├── 99_Archive/                     ← ARCHIVES (jamais supprimées)
│   └── 2026-03-14_restructuration/
│       ├── systemFactChecking-1/   ← Copie complète préservée
│       ├── syscred-space_backup/   ← Version HF préservée
│       ├── v2_syscred/             ← Ancienne version
│       ├── syscred_legacy/
│       └── SysCRED_v2.1_Update/
│       └── README.md               ← Documentation des archives
│
├── pyproject.toml                  ← Configuration package Python
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore                      ← Mis à jour avec data/large
└── README.md                       ← Mis à jour

```


