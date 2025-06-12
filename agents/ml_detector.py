import pickle
import numpy as np
from typing import Dict, Any, List

class MLDetector:
    def __init__(self, model_path: str):
        self.model = self.load_model(model_path)
        self.call_count = 0  # Counter to simulate 1 in every 20 transactions

    def load_model(self, model_path: str):
        """Load the trained ML model"""
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            print(f"✅ ML model loaded successfully")
            return model
        except Exception as e:
            print(f"❌ Error loading ML model: {e}")
            return None

    def extract_features(self, transaction: Dict[str, Any]) -> List[float]:
        """Extract 7 features from transaction for ML model"""
        features = [
            float(self.encode_bank(transaction.get('From Bank', ''))),
            float(self.encode_account(transaction.get('Account', ''))),
            float(self.encode_bank(transaction.get('To Bank', ''))),
            float(self.encode_account(transaction.get('Account.1', ''))),
            float(transaction.get('Amount Received', 0)),
            float(self.encode_currency(transaction.get('Receiving Currency', ''))),
            float(self.encode_payment_format(transaction.get('Payment Format', '')))
        ]
        return features

    def encode_bank(self, bank_name: str) -> int:
        """Encode bank name to numeric value"""
        return hash(bank_name) % 1000 if bank_name else 0

    def encode_account(self, account: str) -> int:
        """Encode account to numeric value"""
        if not account:
            return 0
        try:
            if account.startswith("ACC"):
                return int(account[3:]) % 100000
            else:
                return hash(account) % 100000
        except:
            return hash(account) % 100000

    def encode_currency(self, currency: str) -> int:
        """Encode currency to numeric value"""
        currency_map = {
            'USD': 1, 'EUR': 2, 'GBP': 3, 'JPY': 4,
            'CHF': 5, 'CAD': 6, 'AUD': 7, 'BTC': 8
        }
        return currency_map.get(currency.upper(), 0)

    def encode_payment_format(self, payment_format: str) -> int:
        """Encode payment format to numeric value"""
        format_map = {
            'WIRE': 1, 'ACH': 2, 'CHECK': 3, 'CASH': 4,
            'CRYPTO': 5, 'CARD': 6, 'TRANSFER': 7
        }
        return format_map.get(payment_format.upper(), 0)

    def predict(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Predict if transaction is money laundering"""
        if self.model is None:
            return {"is_laundering": False, "confidence": 0.0, "error": "Model not loaded"}
        
        try:
            # Increment call counter
            self.call_count += 1

            # Extract features
            features = self.extract_features(transaction)
            features_array = np.array(features).reshape(1, -1)

            # Make prediction
            prediction = self.model.predict(features_array)[0]

            # Force a positive (1) every 20 transactions
            if self.call_count % 20 == 0:
                prediction = 1

            # Get confidence
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(features_array)[0]
                confidence = max(probabilities)
            else:
                confidence = 0.8 if prediction == 1 else 0.2

            is_laundering = bool(prediction == 1)

            return {
                "is_laundering": is_laundering,
                "confidence": float(confidence),
                "features": features
            }

        except Exception as e:
            return {"is_laundering": False, "confidence": 0.0, "error": str(e)}
