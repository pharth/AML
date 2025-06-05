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
        # Extract features that your ML model expects
        # Modify this based on your ML model's feature requirements
        features = [
            float(transaction.get('amount', 0)),
            float(transaction.get('transaction_type', 0)),  # Assuming encoded
            float(transaction.get('sender_risk_score', 0)),
            float(transaction.get('receiver_risk_score', 0)),
            float(transaction.get('time_of_day', 0)),  # Hour of day
            float(transaction.get('day_of_week', 0)),
            float(transaction.get('cross_border', 0)),  # 1 if cross-border, 0 otherwise
            float(transaction.get('high_risk_country', 0)),  # 1 if high-risk, 0 otherwise
        ]
        
        return features
    
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