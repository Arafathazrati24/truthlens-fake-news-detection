"""
Fake News Detection API
=======================
MSc Project | Arafat Hazrati | 24015414
London Metropolitan University | 2024-2025
Supervisor: Professor Karim Ouazzane

Endpoints:
  POST /predict   — Predict fake or real for submitted text or URL
  POST /explain   — LIME explanation for a prediction
  GET  /health    — System health check
  POST /feedback  — Log user correction
  GET  /stats     — Prediction statistics
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time
import uvicorn

from model_loader import ModelLoader
from preprocessor import clean_text, fetch_url_text
from database import Database

# ── App Initialisation ─────────────────────────────────────

app = FastAPI(
    title="Fake News Detection API",
    description="AI-powered fake news detection using SVM, BiLSTM and RoBERTa",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── CORS — allows browser extension to connect ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load models at startup ─────────────────────────────────
loader = ModelLoader()
db     = Database()

# ── Request / Response Models ──────────────────────────────

class PredictRequest(BaseModel):
    text: Optional[str] = None
    url:  Optional[str] = None

class ExplainRequest(BaseModel):
    text: str

class FeedbackRequest(BaseModel):
    prediction_id: int
    correct:       bool
    comment:       Optional[str] = None

# ── Confidence Tier Logic ──────────────────────────────────

def get_confidence_tier(confidence_fake: float) -> dict:
    """
    Four-tier uncertainty system.
    Returns tier, label, action, and colour for UI display.
    """
    conf_real = 1 - confidence_fake
    max_conf  = max(confidence_fake, conf_real)
    is_fake   = confidence_fake > 0.5

    if max_conf < 0.55:
        return {
            "tier"   : "UNCERTAIN",
            "label"  : "Cannot Determine",
            "action" : "Model cannot reliably classify this content. Verify with trusted fact-checking sources.",
            "color"  : "#888888",
            "emoji"  : "❓"
        }
    elif max_conf < 0.65:
        return {
            "tier"   : "LOW_CONFIDENCE",
            "label"  : "Likely Fake" if is_fake else "Likely Real",
            "action" : "Low confidence prediction. Treat with caution and cross-check with multiple sources.",
            "color"  : "#FFC000",
            "emoji"  : "⚠️"
        }
    elif max_conf < 0.85:
        return {
            "tier"   : "MEDIUM_CONFIDENCE",
            "label"  : "Probably Fake" if is_fake else "Probably Real",
            "action" : "Moderate confidence. Cross-checking with trusted sources recommended.",
            "color"  : "#C00000" if is_fake else "#2E75B6",
            "emoji"  : "🟠" if is_fake else "🟡"
        }
    else:
        return {
            "tier"   : "HIGH_CONFIDENCE",
            "label"  : "FAKE NEWS" if is_fake else "REAL NEWS",
            "action" : "High confidence verdict. For fake news: do not share without verification.",
            "color"  : "#C00000" if is_fake else "#2E75B6",
            "emoji"  : "🔴" if is_fake else "🟢"
        }

# ── Routes ─────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message"  : "Fake News Detection API",
        "version"  : "1.0.0",
        "author"   : "Arafat Hazrati | 24015414 | LMU",
        "endpoints": ["/predict", "/explain", "/health",
                      "/feedback", "/stats", "/docs"]
    }


@app.get("/health")
def health():
    """System health check — confirms models are loaded."""
    return {
        "status"      : "healthy",
        "models_loaded": loader.is_ready(),
        "primary_model": loader.primary_model_name,
        "uptime_seconds": loader.uptime(),
        "total_predictions": db.total_predictions()
    }


@app.post("/predict")
def predict(request: PredictRequest):
    """
    Main prediction endpoint.
    Accepts either raw text or a URL.
    Returns verdict, confidence score, and tier.
    """
    start_time = time.time()

    # ── Input validation ───────────────────────────────────
    if not request.text and not request.url:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'text' or 'url' in request body."
        )

    # ── Fetch URL content if URL provided ──────────────────
    raw_text = request.text
    source   = "text_input"

    if request.url:
        raw_text = fetch_url_text(request.url)
        source   = request.url
        if not raw_text:
            raise HTTPException(
                status_code=422,
                detail="Could not extract text from the provided URL. Try pasting the article text directly."
            )

    # ── Length validation ──────────────────────────────────
    if len(raw_text.split()) < 10:
        raise HTTPException(
            status_code=422,
            detail="Text too short for reliable analysis. Please provide at least 10 words."
        )

    # ── Preprocessing ──────────────────────────────────────
    clean   = clean_text(raw_text)
    if len(clean.split()) < 5:
        raise HTTPException(
            status_code=422,
            detail="After preprocessing, insufficient text remains. Please provide a longer article."
        )

    # ── Prediction ─────────────────────────────────────────
    result   = loader.predict(clean)
    tier     = get_confidence_tier(result["confidence_fake"])
    elapsed  = round((time.time() - start_time) * 1000, 1)

    # ── Log to database ────────────────────────────────────
    pred_id = db.log_prediction(
        source         = source,
        text_length    = len(raw_text.split()),
        prediction     = result["prediction"],
        confidence     = result["confidence_fake"],
        tier           = tier["tier"],
        model_used     = result["model_used"],
        processing_ms  = elapsed
    )

    return {
        "prediction_id"   : pred_id,
        "verdict"         : tier["label"],
        "is_fake"         : result["prediction"] == 1,
        "confidence_fake" : round(result["confidence_fake"], 4),
        "confidence_real" : round(1 - result["confidence_fake"], 4),
        "confidence_pct"  : round(max(result["confidence_fake"],
                                      1 - result["confidence_fake"]) * 100, 1),
        "tier"            : tier["tier"],
        "action"          : tier["action"],
        "color"           : tier["color"],
        "emoji"           : tier["emoji"],
        "model_used"      : result["model_used"],
        "processing_ms"   : elapsed,
        "text_length_words": len(raw_text.split())
    }


@app.post("/explain")
def explain(request: ExplainRequest):
    """
    LIME explainability endpoint.
    Returns the top words that drove the prediction.
    """
    start_time = time.time()

    if len(request.text.split()) < 10:
        raise HTTPException(
            status_code=422,
            detail="Text too short for explanation. Provide at least 10 words."
        )

    clean  = clean_text(request.text)
    result = loader.predict(clean)
    tier   = get_confidence_tier(result["confidence_fake"])

    # Generate LIME explanation
    explanation = loader.explain(request.text)
    elapsed     = round((time.time() - start_time) * 1000, 1)

    return {
        "verdict"         : tier["label"],
        "is_fake"         : result["prediction"] == 1,
        "confidence_fake" : round(result["confidence_fake"], 4),
        "confidence_pct"  : round(max(result["confidence_fake"],
                                      1 - result["confidence_fake"]) * 100, 1),
        "tier"            : tier["tier"],
        "top_fake_words"  : explanation["top_fake_words"],
        "top_real_words"  : explanation["top_real_words"],
        "all_features"    : explanation["all_features"],
        "processing_ms"   : elapsed
    }


@app.post("/feedback")
def feedback(request: FeedbackRequest):
    """
    User feedback endpoint.
    Logs whether the prediction was correct or not.
    Builds dataset for future retraining.
    """
    success = db.log_feedback(
        prediction_id = request.prediction_id,
        correct       = request.correct,
        comment       = request.comment
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Prediction ID {request.prediction_id} not found."
        )

    return {
        "acknowledged"  : True,
        "prediction_id" : request.prediction_id,
        "feedback"      : "correct" if request.correct else "incorrect",
        "message"       : "Thank you. Your feedback helps improve the system."
    }


@app.get("/stats")
def stats():
    """Returns prediction statistics for monitoring."""
    return db.get_stats()


# ── Entry Point ────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
