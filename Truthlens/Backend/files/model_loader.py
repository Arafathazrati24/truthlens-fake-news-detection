"""
Model Loader
============
Loads all trained models at startup and keeps them in memory.
Handles prediction and LIME explanation generation.
"""

import pickle
import time
import os
import numpy as np
from lime.lime_text import LimeTextExplainer
from preprocessor import clean_text


class ModelLoader:
    """
    Loads and manages all trained models.
    Models are loaded once at startup for fast inference.
    """

    def __init__(self):
        self._start_time = time.time()
        self._ready      = False

        # Primary model for deployment
        self.primary_model_name = "Support Vector Machine"

        # Model and vectoriser references
        self.svm   = None
        self.tfidf = None

        # LIME explainer
        self.explainer = None

        # Load everything
        self._load_models()

    def _load_models(self):
        """Load SVM and TF-IDF vectoriser from disk."""
        models_dir = os.path.join(
            os.path.dirname(__file__), "models")

        try:
            print("Loading TF-IDF vectoriser...")
            tfidf_path = os.path.join(
                models_dir, "tfidf_vectorizer.pkl")
            with open(tfidf_path, "rb") as f:
                self.tfidf = pickle.load(f)
            print("  TF-IDF loaded ✓")

            print("Loading SVM model...")
            svm_path = os.path.join(
                models_dir, "model_svm.pkl")
            with open(svm_path, "rb") as f:
                self.svm = pickle.load(f)
            print("  SVM loaded ✓")

            # Initialise LIME explainer
            self.explainer = LimeTextExplainer(
                class_names=["Real News", "Fake News"],
                random_state=42
            )
            print("  LIME explainer ready ✓")

            self._ready = True
            print("\nAll models loaded successfully.")
            print(f"Primary model: {self.primary_model_name}")

        except FileNotFoundError as e:
            print(f"\nERROR: Model file not found — {e}")
            print("Make sure model files are in the models/ directory.")
            self._ready = False

        except Exception as e:
            print(f"\nERROR loading models: {e}")
            self._ready = False

    def is_ready(self) -> bool:
        """Returns True if all models loaded successfully."""
        return self._ready

    def uptime(self) -> float:
        """Returns seconds since startup."""
        return round(time.time() - self._start_time, 1)

    def predict(self, clean_text_input: str) -> dict:
        """
        Run prediction on preprocessed text.
        Returns prediction label and confidence scores.
        """
        if not self._ready:
            raise RuntimeError(
                "Models not loaded. Check server logs.")

        # Transform text using fitted TF-IDF vectoriser
        features = self.tfidf.transform([clean_text_input])

        # Get prediction and probability
        prediction = int(self.svm.predict(features)[0])
        proba      = self.svm.predict_proba(features)[0]

        # proba[0] = probability of Real (class 0)
        # proba[1] = probability of Fake (class 1)
        confidence_fake = float(proba[1])

        return {
            "prediction"     : prediction,
            "confidence_fake": confidence_fake,
            "confidence_real": float(proba[0]),
            "model_used"     : self.primary_model_name
        }

    def _predict_proba_for_lime(self, texts: list) -> np.ndarray:
        """
        Prediction function formatted for LIME.
        LIME requires a function that accepts a list of texts
        and returns a 2D probability array.
        """
        cleaned    = [clean_text(t) for t in texts]
        features   = self.tfidf.transform(cleaned)
        return self.svm.predict_proba(features)

    def explain(self, raw_text: str,
                num_features: int = 12,
                num_samples: int = 300) -> dict:
        """
        Generate LIME explanation for a prediction.
        Returns top words pushing towards fake and real.
        """
        if not self._ready:
            raise RuntimeError("Models not loaded.")

        exp = self.explainer.explain_instance(
            raw_text,
            self._predict_proba_for_lime,
            num_features=num_features,
            num_samples=num_samples,
            labels=[0, 1]
        )

        # Extract feature weights for fake class (label=1)
        feature_weights = exp.as_list(label=1)

        top_fake_words = [
            {"word": w, "weight": round(v, 4)}
            for w, v in feature_weights if v > 0
        ]
        top_real_words = [
            {"word": w, "weight": round(abs(v), 4)}
            for w, v in feature_weights if v < 0
        ]

        # Sort by weight descending
        top_fake_words = sorted(
            top_fake_words,
            key=lambda x: x["weight"],
            reverse=True)[:6]
        top_real_words = sorted(
            top_real_words,
            key=lambda x: x["weight"],
            reverse=True)[:6]

        return {
            "top_fake_words": top_fake_words,
            "top_real_words": top_real_words,
            "all_features"  : [
                {"word": w, "weight": round(v, 4)}
                for w, v in feature_weights
            ]
        }
