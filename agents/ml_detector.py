import pickle
import numpy as np
from typing import Dict, Any, List
from utils.config import config
from database.mongo_handler import mongo_handler

class MLDetectorAgent:
    def __init__(self):
        self.name = "MLDetector"
        self.model = self.load_ml_model()
    
    def load_ml_model(self):
        """Load the trained ML model from pickle file"""
        try:
            with open(config.ML_MODEL_PATH, 'rb') as f:
                model = pickle.load(f)
            print(f"[{self.name}] ML model loaded successfully")
            return model
        except Exception as e:
            print(f"[{self.name}] Error loading ML model: {e}")
            return None
    
    def predict_money_laundering(self, features: List[float]) -> Dict[str, Any]:
        """Predict if transaction involves money laundering"""
        if self.model is None:
            return {"is_laundering": False, "confidence": 0.0, "error": "Model not loaded"}
        
        try:
            # Reshape features for prediction
            features_array = np.array(features).reshape(1, -1)
            
            # Get prediction and probability
            prediction = self.model.predict(features_array)[0]
            
            # Get prediction probability if available
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(features_array)[0]
                confidence = max(probabilities)
            else:
                confidence = 0.8 if prediction == 1 else 0.2
            
            is_laundering = bool(prediction == 1)
            
            print(f"[{self.name}] Prediction: {'LAUNDERING' if is_laundering else 'CLEAN'}, Confidence: {confidence:.2f}")
            
            return {
                "is_laundering": is_laundering,
                "confidence": float(confidence),
                "prediction_value": int(prediction)
            }
            
        except Exception as e:
            print(f"[{self.name}] Error in prediction: {e}")
            return {"is_laundering": False, "confidence": 0.0, "error": str(e)}
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node execution"""
        if not state.get("has_transaction", False):
            return {"ml_prediction": None, "requires_investigation": False}
        
        ml_features = state.get("ml_features", [])
        current_transaction = state.get("current_transaction", {})
        
        if not ml_features:
            return {"ml_prediction": None, "requires_investigation": False}
        
        # Make prediction
        prediction_result = self.predict_money_laundering(ml_features)
        
        # Mark transaction as processed
        if current_transaction and "_id" in current_transaction:
            mongo_handler.mark_transaction_processed(str(current_transaction["_id"]))
        
        # Update state
        requires_investigation = prediction_result.get("is_laundering", False)
        
        return {
            "ml_prediction": prediction_result,
            "requires_investigation": requires_investigation,
            "sender_account": current_transaction.get("sender_account", "")
        }