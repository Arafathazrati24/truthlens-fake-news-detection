# TruthLens — Fake News Detection System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![HuggingFace](https://img.shields.io/badge/Hugging%20Face-Spaces-yellow?style=for-the-badge)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4+-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Scan any news article in real time, directly in your browser.**

[Live Demo](#live-demo) · [How It Works](#how-it-works) · [Results](#model-results) · [Installation](#installation) · [Limitations](#limitations-and-honest-evaluation)

---

## What Is TruthLens?

TruthLens is an end-to-end fake news detection system built as the final project for an MSc in Artificial Intelligence at London Metropolitan University (2026).

The goal was not just to train a model that achieves high accuracy — it was to understand why different models behave differently on this problem, and then ship something real: a live API, a working Chrome extension that scans articles as you browse, and a web app where anyone can paste text or a URL and get an instant verdict.

Six models were implemented and benchmarked, spanning the full spectrum from classical ML to state-of-the-art transformers. The results were surprising, and the explanation matters.

---

## Live Demo

**Web App:** [https://huggingface.co/spaces/rafat24/truthlens](https://huggingface.co/spaces/rafat24/truthlens)

**Chrome Extension:** See the Installation section below to load it locally.

---

## System Architecture

```
 Chrome Extension                    Web App
 Reads any webpage                   Paste text or URL
 Extracts article text               See verdict and confidence
 Shows popup verdict                 Submit feedback
       |                                   |
       +---------------+-------------------+
                       |
                  FastAPI Backend
                (Hugging Face Spaces)
                       |
              ML Model Layer
     Naive Bayes   |   Logistic Regression
     Linear SVM    |   Random Forest
     BiLSTM + CNN  |   DistilRoBERTa
```

---

## How It Works

### Data

Trained on the ISOT Fake News Dataset, one of the most widely used benchmarks in NLP misinformation research.

| Property | Detail |
|---|---|
| Total articles | ~44,000 |
| Real news source | Reuters.com |
| Fake news source | PolitiFact-flagged articles |
| Coverage period | 2016 to 2018 |
| Features used | Article title and body text, concatenated |
| Train/Test split | 80/20, stratified |

### Preprocessing Pipeline

Raw text goes through lowercasing, punctuation removal, stopword removal, and tokenisation. Classical models use TF-IDF vectorisation. Deep learning and transformer models use their respective tokenisers and embedding layers.

### Models

Six models were deliberately chosen to span the full ML spectrum, not just to find the best one, but to understand the tradeoffs between model complexity, training time, and performance on this specific problem.

| Model | Type | Notes |
|---|---|---|
| Naive Bayes | Classical ML | Probabilistic baseline; fast and interpretable |
| Logistic Regression | Classical ML | Strong linear classifier; good calibration |
| Linear SVM | Classical ML | Optimal margin classifier; best overall performer |
| Random Forest | Classical ML ensemble | Tree-based; robust to noise |
| BiLSTM + CNN | Deep Learning hybrid | Captures sequential and local patterns simultaneously |
| DistilRoBERTa | Transformer | Lightweight BERT variant; context-aware representations |

---

## Model Results

Evaluated on a held-out 20% test split of the ISOT dataset.

| Model | F1 Score | AUC-ROC | Training Time |
|---|---|---|---|
| Linear SVM (best) | 0.9948 | >0.99 | Fast, seconds |
| Logistic Regression | ~0.993 | >0.99 | Fast |
| Naive Bayes | ~0.990 | >0.99 | Very fast |
| Random Forest | ~0.991 | >0.99 | Moderate |
| BiLSTM + CNN | ~0.992 | >0.99 | Slow, requires GPU |
| DistilRoBERTa | 0.9905 | >0.99 | Slowest, requires GPU |

### Why Did SVM Beat DistilRoBERTa?

This is the most interesting finding in the project and worth explaining properly.

DistilRoBERTa is a far more powerful model in general. It was pre-trained on hundreds of gigabytes of text and understands context, semantics, and language nuance at a level no classical model can match. So why did SVM win here?

Three reasons:

**Dataset characteristics.** The ISOT dataset has a strong stylistic separation between Reuters journalism and PolitiFact-flagged content. Real and fake articles differ not just in content but in writing style, vocabulary, and structure — patterns that TF-IDF combined with SVM captures extremely well through linear decision boundaries.

**Domain signal strength.** DistilRoBERTa's contextual embeddings are powerful precisely because they model subtle, context-dependent meaning. On ISOT, the signal is less subtle. The vocabulary-level separation is so clean that a linear kernel on TF-IDF features finds the boundary almost perfectly without needing contextual modelling.

**Training data volume.** Deep learning models generally need more data to outperform classical methods. At around 44,000 samples with clean labels, the dataset is large enough for classical models to perform near-perfectly, but not large enough to fully leverage transformer capacity.

The lesson is that model selection should be driven by data characteristics, not by model prestige. A DistilRoBERTa fine-tuned on millions of diverse, noisy, real-world news samples would likely dominate. On ISOT, SVM is the right tool for the job.

---

## Features

### Chrome Extension

The extension automatically extracts article text from any webpage the user is reading, sends it to the FastAPI backend, and renders the result directly in the browser popup. No copy-pasting is needed. The response includes a Fake or Real verdict, a confidence tier (High, Medium, or Low), and a word-level explanation highlighting which words most influenced the prediction.

### Web App

Users can paste raw article text or enter a URL. The app returns a verdict with a confidence percentage and a breakdown of the key influencing words. Users can also submit feedback indicating whether the result was correct, which is stored for future model evaluation cycles.

### FastAPI Backend

The backend handles URL text extraction, text preprocessing, and model inference. It exposes a predict endpoint and a feedback endpoint. User feedback is stored in SQLite. Interactive API documentation is auto-generated and available at the /docs route when running locally.

---

## Repository Structure

```
truthlens-fake-news-detection/
│
├── Backend/
│   ├── files/
│   │   ├── main.py              # FastAPI app, all routes and prediction logic
│   │   ├── model_loader.py      # Loads and caches trained models at startup
│   │   ├── database.py          # SQLite feedback schema and write logic
│   │   └── models/
│   │       └── preprocessor.py  # Text cleaning and TF-IDF feature extraction
│   ├── requirements.txt         # All Python dependencies
│   └── files.zip                # Packaged model artefacts
│
├── Notebook file/
│   └── Kaggle_Fake_News_Final.ipynb  # Full pipeline: EDA, training, evaluation, comparison
│
├── TruthLens_extension/
│   ├── manifest.json            # Chrome Extension Manifest V3 configuration
│   ├── popup.html               # Extension popup UI
│   ├── popup.js                 # Popup logic, API calls, result rendering
│   ├── content.js               # Injected script that extracts article text from page
│   ├── background.js            # Service worker for extension lifecycle
│   └── icons/                   # Extension icon assets
│
└── index.html                   # Single-page web app, no build step required
```

---

## Installation

**Prerequisites:** Python 3.10 or higher, pip, and Google Chrome for the extension.

### Backend

```bash
git clone https://github.com/Arafathazrati24/truthlens-fake-news-detection.git
cd truthlens-fake-news-detection
pip install -r Backend/requirements.txt
cd Backend/files
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at https://rafat24-truthlens.hf.space and interactive docs at https://rafat24-truthlens.hf.space/docs.

### Web App

With the backend running locally, open index.html directly in your browser. If pointing to the Hugging Face Space, update the API URL in index.html accordingly.

### Chrome Extension

1. Open Chrome and go to chrome://extensions/
2. Enable Developer Mode using the toggle in the top-right corner
3. Click Load unpacked
4. Select the TruthLens_extension/ folder from this repository
5. The TruthLens icon will appear in your Chrome toolbar
6. Navigate to any news article and click the icon to scan it

---

## Limitations and Honest Evaluation

No responsible ML project should skip this section.

**Style detection, not fact-checking.** The ISOT dataset separates real from fake news largely by writing style. Models trained on it learn stylistic signals rather than factual inaccuracies. A well-written fake article that mimics Reuters style could fool the classifier. TruthLens is a misinformation risk screener, not a fact-checker.

**Temporal generalisation.** The dataset covers 2016 to 2018. Language, news topics, and misinformation tactics evolve. Performance on 2025 to 2026 articles has not been evaluated and may differ.

**English only.** All models were trained on English-language content. Non-English input will produce unreliable results.

**URL extraction reliability.** The URL-based extraction depends on page structure. Paywalled, JavaScript-rendered, or non-standard pages may not extract cleanly.

**No external fact verification.** TruthLens does not verify claims against external databases or sources. It detects patterns in text — it does not know whether specific facts are true or false.

---

## Future Work

- Retrain on a larger, more recent, and more diverse dataset such as FakeNewsNet or LIAR-PLUS
- Add multilingual support, particularly relevant given the multilingual context of this project
- Integrate a lightweight fact-checking API as a second verification layer
- Improve explainability from word-level attribution to sentence-level reasoning
- Add confidence calibration, since current probability outputs are not formally calibrated
- Use collected user feedback for iterative model improvement cycles

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10 |
| Classical ML | scikit-learn (Naive Bayes, Logistic Regression, SVM, Random Forest) |
| Deep Learning | TensorFlow and Keras (BiLSTM + CNN) |
| Transformers | Hugging Face Transformers (DistilRoBERTa) |
| Backend | FastAPI |
| Deployment | Hugging Face Spaces |
| Extension | Chrome Extension API Manifest V3, JavaScript |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Training | Kaggle Notebooks |
| Local development | VS Code |
| Database | SQLite for feedback storage |

---

## About

MSc Artificial Intelligence Final Project
London Metropolitan University, 2026

**Author:** Arafat Hazrati
**Email:** Arafathazrati24@gmail.com
**LinkedIn:** [Arafat Hazrati](https://linkedin.com/in/arafat-hazrati)

If you find this project useful or interesting, a star on the repo is appreciated.
