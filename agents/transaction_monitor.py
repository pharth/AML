from typing import Dict, Any, List
from database.mongo_handler import mongo_handler
from utils.config import config

class TransactionMonitorAgent:
    def __init__(self):
        self.name = "TransactionMonitor"
    
    def monitor_new_transactions(self) -> List[Dict[str, Any]]:
        """Monitor for new unprocessed transactions"""
        try:
            unprocessed_transactions = mongo_handler.get_unprocessed_transactions(
                limit=config.TRANSACTION_BATCH_SIZE
            )
            
            print(f"[{self.name}] Found {len(unprocessed_transactions)} unprocessed transactions")
            return unprocessed_transactions
            
        except Exception as e:
            print(f"[{self.name}] Error monitoring transactions: {e}")
            return []
    
    def prepare_transaction_for_ml(self, transaction: Dict[str, Any]) -> List[float]:
        """Prepare transaction data for ML model input"""
        # Extract features based on your data columns
        features = [
            float(transaction.get('Amount Received', 0)),
            float(transaction.get('Amount Paid', 0)),
            # Convert payment format to numeric (you may need to adjust encoding)
            float(self.encode_payment_format(transaction.get('Payment Format', ''))),
            # Add basic risk scores based on banks (placeholder - you can enhance this)
            float(self.calculate_bank_risk_score(transaction.get('From Bank', ''))),
            float(self.calculate_bank_risk_score(transaction.get('To Bank', ''))),
            # Time-based features from timestamp
            float(self.extract_hour_from_timestamp(transaction.get('Timestamp', ''))),
            float(self.extract_day_of_week_from_timestamp(transaction.get('Timestamp', ''))),
            # Currency risk (1 if different currencies, 0 if same)
            float(1 if transaction.get('Receiving Currency', '') != transaction.get('Payment Currency', '') else 0),
        ]
        
        return features
    
    def encode_payment_format(self, payment_format: str) -> int:
        """Encode payment format to numeric value"""
        format_mapping = {
            'WIRE': 1,
            'ACH': 2,
            'CHECK': 3,
            'CASH': 4,
            'CRYPTO': 5,
            'CARD': 6,
            'TRANSFER': 7
        }
        return format_mapping.get(payment_format.upper(), 0)
    
    def calculate_bank_risk_score(self, bank: str) -> float:
        """Calculate risk score for a bank (placeholder implementation)"""
        # You can enhance this with actual bank risk data
        high_risk_keywords = ['offshore', 'private', 'anonymous', 'crypto']
        if any(keyword in bank.lower() for keyword in high_risk_keywords):
            return 0.8
        return 0.3
    
    def extract_hour_from_timestamp(self, timestamp: str) -> int:
        """Extract hour from timestamp"""
        try:
            from datetime import datetime
            if isinstance(timestamp, str):
                # Adjust format based on your timestamp format
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            return dt.hour
        except:
            return 12  # Default to noon
    
    def extract_day_of_week_from_timestamp(self, timestamp: str) -> int:
        """Extract day of week from timestamp (1=Monday, 7=Sunday)"""
        try:
            from datetime import datetime
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            return dt.weekday() + 1
        except:
            return 1  # Default to Monday
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node execution"""
        transactions = self.monitor_new_transactions()
        
        if transactions:
            # Process the first transaction
            current_transaction = transactions[0]
            ml_features = self.prepare_transaction_for_ml(current_transaction)
            
            return {
                "current_transaction": current_transaction,
                "ml_features": ml_features,
                "has_transaction": True
            }
        
        return {
            "current_transaction": None,
            "ml_features": None,
            "has_transaction": False
        }