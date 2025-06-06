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
            # Try to import xgboost first
            try:
                import xgboost as xgb
                print(f"[{self.name}] XGBoost version: {xgb.__version__}")
            except ImportError:
                print(f"[{self.name}] Warning: XGBoost not installed. Installing...")
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost"])
                import xgboost as xgb
                print(f"[{self.name}] XGBoost installed successfully, version: {xgb.__version__}")
            
            # Load the model
            with open(config.ML_MODEL_PATH, 'rb') as f:
                model = pickle.load(f)
            print(f"[{self.name}] ML model loaded successfully")
            print(f"[{self.name}] Model type: {type(model)}")
            return model
            
        except ImportError as e:
            print(f"[{self.name}] Error installing XGBoost: {e}")
            print(f"[{self.name}] Please install XGBoost manually: pip install xgboost")
            return None
        except FileNotFoundError:
            print(f"[{self.name}] Model file not found: {config.ML_MODEL_PATH}")
            return None
        except Exception as e:
            print(f"[{self.name}] Error loading ML model: {e}")
            print(f"[{self.name}] Model path: {config.ML_MODEL_PATH}")
            return None
    
    def predict_money_laundering(self, features: List[float]) -> Dict[str, Any]:
        """Predict if transaction involves money laundering"""
        if self.model is None:
            return {"is_laundering": False, "confidence": 0.0, "error": "Model not loaded"}
        
        try:
            # Ensure we have exactly 7 features
            if len(features) != 7:
                print(f"[{self.name}] Warning: Expected 7 features, got {len(features)}")
                # Pad or truncate to 7 features
                if len(features) < 7:
                    features.extend([0.0] * (7 - len(features)))
                else:
                    features = features[:7]
            
            # Reshape features for prediction
            features_array = np.array(features).reshape(1, -1)
            
            # Get prediction and probability
            prediction = self.model.predict(features_array)[0]
            
            # Get prediction probability if available
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(features_array)[0]
                confidence = max(probabilities)
            else:
                # For XGBoost models, try predict_proba or use default confidence
                try:
                    probabilities = self.model.predict_proba(features_array)[0]
                    confidence = max(probabilities)
                except:
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
            print(f"[{self.name}] Features shape: {np.array(features).shape}")
            print(f"[{self.name}] Features: {features}")
            return {"is_laundering": False, "confidence": 0.0, "error": str(e)}
    
    def test_model(self):
        """Test the model with dummy data matching the 7 feature structure"""
        if self.model is None:
            print(f"[{self.name}] Cannot test - model not loaded")
            return False
            
        try:
            # Create dummy features matching your 7-feature structure:
            # [From Bank, Account, To Bank, Account.1, Amount Received, Receiving Currency, Payment Format]
            dummy_features = [
                100.0,    # From Bank (encoded)
                12345.0,  # Account (encoded) 
                200.0,    # To Bank (encoded)
                67890.0,  # Account.1 (encoded)
                5000.0,   # Amount Received
                1.0,      # Receiving Currency (USD=1)
                1.0       # Payment Format (WIRE=1)
            ]
            
            result = self.predict_money_laundering(dummy_features)
            print(f"[{self.name}] Model test successful: {result}")
            return True
        except Exception as e:
            print(f"[{self.name}] Model test failed: {e}")
            return False
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node execution"""
        if not state.get("has_transaction", False):
            return {"ml_prediction": None, "requires_investigation": False}
        
        ml_features = state.get("ml_features", [])
        current_transaction = state.get("current_transaction", {})
        
        if not ml_features:
            print(f"[{self.name}] No ML features provided")
            return {"ml_prediction": None, "requires_investigation": False}
        
        # Make prediction
        prediction_result = self.predict_money_laundering(ml_features)
        
        # Mark transaction as processed
        if current_transaction and "_id" in current_transaction:
            try:
                mongo_handler.mark_transaction_processed(str(current_transaction["_id"]))
            except Exception as e:
                print(f"[{self.name}] Error marking transaction as processed: {e}")
        
        # Update state
        requires_investigation = prediction_result.get("is_laundering", False)
        
        # Extract sender account using your data column names
        sender_account = current_transaction.get("Account", "")
        
        return {
            "ml_prediction": prediction_result,
            "requires_investigation": requires_investigation,
            "sender_account": sender_account
        }