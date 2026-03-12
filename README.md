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
Enter a URL or paste text to analyze its credibility score based on multiple factors.

# Journal de Développement - Stabilisation Critique
**Date :** 9 mars 2026
**Projet :** SysCRED (Système de Vérification de Crédibilité - Thèse de Doctorat)
**Objectif :** Diagnostic et correction des crashs applicatifs sur HuggingFace et synchronisation sécurisée du code source.

---

## 1. Résumé Exécutif

L'application `systemFactChecking` sur HuggingFace rencontrait des crashs systématiques (`Worker Timeout`, `SIGKILL`) et des erreurs de chargement de modèles NER suite à des mises à jour de la librairie `transformers`.

Une session de diagnostic et de correction a permis de :
1.  **Stabiliser l'application live** sur HuggingFace (correction du timeout et du NER).
2.  **Sauvegarder le code local** sur une branche Git sécurisée (`backup-pre-refactor-mars-2026`).
3.  **Identifier un blocage réseau** sur le dépôt GitHub principal (push échouant en HTTP 400), bien que le code soit sauvé localement et sur HuggingFace.

---

## 2. Corrections Techniques Appliquées

### 2.1 Correction du Crash NER (Named Entity Recognition)
**Problème :**
Le modèle NER (`dslim/bert-base-NER`) échouait au chargement avec l'erreur :
`TokenClassificationPipeline._sanitize_parameters() got an unexpected keyword argument 'grouped_entities'`

**Cause :**
La librairie HuggingFace `transformers` a récemment déprécié l'argument `grouped_entities=True` au profit de `aggregation_strategy`.

**Solution Appliquée :**
*Fichier :* `syscred/verification_system.py`
*Ligne :* 127

**Avant (Code Buggy) :**
```python
self.ner_pipeline = pipeline(
    "ner",
    model="dslim/bert-base-NER",
    grouped_entities=True,  # <--- OBSOLÈTE
    device=-1,
    model_kwargs={"low_cpu_mem_usage": True}
)
```

**Après (Code Corrigé) :**
```python
self.ner_pipeline = pipeline(
    "ner",
    model="dslim/bert-base-NER",
    aggregation_strategy="simple", # <--- CORRECTION
    device=-1,
    model_kwargs={"low_cpu_mem_usage": True}
)
```

---

### 2.2 Correction du Crash Timeout (LIME Explainer)
**Problème :**
L'application plantait lors de l'analyse de textes longs (ex: "insurrection on january...") avec l'erreur :
`[CRITICAL] WORKER TIMEOUT (pid:9)`
`fatal: the remote end hung up unexpectedly`

**Cause :**
La librairie LIME utilise par défaut `num_samples=5000` pour générer des explications. Sur les CPU standards de HuggingFace, ce calcul prend trop de temps (>60s), déclenchant un "Kill" du processus par Gunicorn.

**Solution Appliquée :**
*Fichier :* `syscred/verification_system.py`
*Ligne :* 234

**Avant (Code Risqué) :**
```python
explanation = self.explainer.explain_instance(
    text[:512], predict_proba, num_features=6
)
```

**Après (Code Corrigé) :**
```python
explanation = self.explainer.explain_instance(
    text[:512], predict_proba, num_features=6, num_samples=500 # <--- AJOUT POUR PERFORMANCE
)
```
*Note : La valeur a été baissée à 500 pour garantir la rapidité, au prix d'une précision légèrement moindre de l'explication.*

---

### 2.3 Correction des Permissions Fichiers
**Problème :**
Erreur lors de l'export de l'ontologie : `[Errno 13] Permission denied: '/app/ontology/sysCRED_data.ttl'`

**Solution :**
Ajout de `os.makedirs` avant l'écriture des fichiers dans `ontology_manager.py` pour s'assurer que le dossier existe et est accessible.

---

## 3. Architecture Git & Sauvegarde

### 3.1 Branches et Remotes
Le dossier de travail principal est : `/Users/bk280625/syscred-hf-local`

**Remotes configurés :**
*   `origin` : Pointe vers l'espace HuggingFace (`https://huggingface.co/spaces/DomLoyer/syscred`).
*   `github` : Pointe vers le dépôt source GitHub (`https://github.com/DominiqueLoyer/syscred`).

**Branche créée :**
`backup-pre-refactor-mars-2026`
*   Cette branche contient l'état stable et corrigé du système.
*   Elle sert de sauvegarde avant toute future refactorisation majeure.

### 3.2 État de la Synchronisation

| Destination | Statut | Détails |
| :--- | :--- | :--- |
| **Local (Mac)** | ✅ **SAUVEGARDÉ** | Commit `4c9055a` créé avec succès. |
| **HuggingFace** | ✅ **À JOUR** | Push `origin` réussi. L'application live a redémarré avec les corrections. |
| **GitHub** | ❌ **EN ÉCHEC** | Push `github` échoue avec `HTTP 400`. Le code n'est pas encore sur le dépôt principal. |

### 3.3 Problème Connu : GitHub Push HTTP 400
Le push vers GitHub échoue systématiquement avec :
`error: RPC failed; HTTP 400 curl 56 The requested URL returned error: 400`
`fatal: the remote end hung up unexpectedly`

**Diagnostic :** Le problème semble lié à **Git LFS** (Large File Storage). L'upload des objets LFS démarre mais échoue à la finalisation, peut-être dû à une limite de taille de buffer ou un timeout serveur.

**Commandes à tenter pour résoudre (à faire ultérieurement) :**
```bash
# 1. Augmenter le buffer Git
git config http.postBuffer 524288000

# 2. Réessayer le push
git push github backup-pre-refactor-mars-2026
```

**Workaround :** Le code est sauvé en local et sur HuggingFace. Il est possible de récupérer le code depuis HuggingFace si besoin, ou de résoudre l'erreur LFS plus tard.

---

## 4. Plan de Refactorisation (Futur)

Une fois le système stabilisé et le GitHub sync résolu, la structure du code doit être nettoyée selon les standards SOTA (State of the Art).

**Structure Cible :**
*   `src/` : Contiendra le package `syscred/`.
*   `docs/` : Documentation centralisée (déplacer `03_DOCS` ici).
*   `tests/` : Tests unitaires.
*   `scripts/` : Scripts de debug et benchmark (ne plus être à la racine).
*   `data/` : Données et ontologies.

**Action :** Ne pas modifier la structure actuellement pour ne pas briser l'application live. Attendre que la branche `backup-pre-refactor-mars-2026` soit fusionnée proprement.

---

## 5. Références Techniques

*   **HuggingFace Transformers Issue :** Migration de `grouped_entities` vers `aggregation_strategy`.
*   **LIME Documentation :** Impact du paramètre `num_samples` sur le temps d'inférence CPU.
*   **Gunicorn :** Configuration des timeouts pour les workers Python.
