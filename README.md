---
title: SysCRED - Système de Vérification de Crédibilité
emoji: 🔍
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: true
license: cc-by-4.0
tags:
  - credibility
  - fact-checking
  - neuro-symbolic
  - information-retrieval
  - E-E-A-T
  - ontology
  - knowledge-graph
  - NLP
  - hybrid-system
  - RDFLib
  - transformers
  - docker
datasets:
  - DomLoyer/trec-ap-88-90
  - ucsbnlp/liar
---


# SysCRED — Système Hybride d'Évaluation de la Crédibilité

[![DOI](https://img.shields.io/badge/DOI-10.13140%2FRG.2.2.22926.47680-blue)](https://doi.org/10.13140/RG.2.2.22926.47680)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0003--9713--7189-green)](https://orcid.org/0009-0003-9713-7109)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Space](https://img.shields.io/badge/🤗%20Space-SysCRED-yellow)](https://huggingface.co/spaces/DomLoyer/syscred)

SysCRED est un **système hybride neuro-symbolique** d'évaluation de la crédibilité
de l'information, développé dans le cadre d'une thèse de doctorat en informatique
cognitive à l'UQAM. Il combine des **règles de prédicats ontologiques** (OWL/RDFLib)
et des **modèles NLP neuronaux** (Transformers) pour produire un score de crédibilité
multidimensionnel.

🔗 **Demo live** : [domloyer-syscred.hf.space](https://domloyer-syscred.hf.space)

## Description

SysCRED évalue la crédibilité des sources et des contenus informationnels selon
une approche hybride inspirée des critères **E-E-A-T de Google**
(Experience, Expertise, Authoritativeness, Trustworthiness) et des métriques
formelles de la recherche d'information (Précision, Rappel, F-measure, NDCG).

## Fonctionnalités

- 🔍 **Analyse URL et texte** : score de crédibilité sur contenu web et textuel
- 🧠 **Analyse NLP** : cohérence sémantique via modèles Transformers
- 📊 **Score SEO et réputation** : évaluation quantitative de la source
- 🌐 **Visualisation Knowledge Graph** : graphe de connaissances interactif D3.js
- 🔗 **Raisonnement ontologique** : règles de prédicats formels via RDFLib/OWL
- 📈 **Métriques IR** : BM25, TF-IDF, NDCG, Précision@k, Rappel@k

## Architecture


```bash
SysCRED/
├── Couche symbolique/     → Ontologie OWL + règles SPARQL/SWRL (RDFLib)
├── Couche neuronale/      → Modèles NLP Transformers (classification, NER)
├── Couche agrégation/     → Score de crédibilité hybride pondéré
└── Couche visualisation/  → Knowledge Graph D3.js + Dashboard Flask

# version étendue

SysCRED/
├── ontology/                        → Couche symbolique
│   ├── syscred.owl                  # Ontologie OWL principale
│   ├── rules.sparql                 # Règles SPARQL
│   └── swrl_rules.py                # Règles SWRL via RDFLib
├── nlp/                             → Couche neuronale
│   ├── classifier.py                # Classification Transformers
│   └── ner.py                       # Named Entity Recognition
├── scoring/                         → Couche agrégation
│   ├── hybrid_score.py              # Score crédibilité hybride pondéré
│   ├── eeat_metrics.py              # Critères E-E-A-T
│   └── ir_metrics.py                # BM25, TF-IDF, NDCG
├── visualization/                   → Couche visualisation
│   ├── knowledge_graph.js           # Knowledge Graph D3.js
│   └── dashboard/                   # Dashboard Flask
├── data/
│   ├── trec-ap-88-90/               # Dataset TREC AP 88-90
│   └── liar/                        # Dataset LIAR
├── app.py                           # Point d'entrée Flask
├── Dockerfile                       # Déploiement HF Spaces
├── requirements.txt
├── README.md
└── CITATION.cff

```





