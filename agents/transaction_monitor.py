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
        """Prepare transaction data for ML model input - exactly 7 features"""
        
        # Extract the exact 7 features your model was trained on
        features = [
            # Feature 1: From Bank (encoded)
            float(self.encode_bank_name(transaction.get('From Bank', ''))),
            
            # Feature 2: Account (encoded)
            float(self.encode_account(transaction.get('Account', ''))),
            
            # Feature 3: To Bank (encoded) 
            float(self.encode_bank_name(transaction.get('To Bank', ''))),
            
            # Feature 4: Account.1 (encoded)
            float(self.encode_account(transaction.get('Account.1', ''))),
            
            # Feature 5: Amount Received
            float(transaction.get('Amount Received', 0)),
            
            # Feature 6: Receiving Currency (encoded)
            float(self.encode_currency(transaction.get('Receiving Currency', ''))),
            
            # Feature 7: Payment Format (encoded)
            float(self.encode_payment_format(transaction.get('Payment Format', '')))
        ]
        
        print(f"[{self.name}] Prepared {len(features)} features for ML model")
        return features
    
    def encode_bank_name(self, bank_name: str) -> int:
        """Encode bank name to numeric value"""
        # Simple hash-based encoding for bank names
        if not bank_name:
            return 0
        return hash(bank_name) % 1000
    
    def encode_account(self, account: str) -> int:
        """Encode account number to numeric value"""
        if not account:
            return 0
        # Extract numeric part from account or use hash
        try:
            # If account is like "ACC12345678", extract the number
            if account.startswith("ACC"):
                return int(account[3:]) % 100000
            else:
                return hash(account) % 100000
        except:
            return hash(account) % 100000
    
    def encode_currency(self, currency: str) -> int:
        """Encode currency to numeric value"""
        currency_mapping = {
            'USD': 1, 'EUR': 2, 'GBP': 3, 'JPY': 4, 
            'CHF': 5, 'CAD': 6, 'AUD': 7, 'BTC': 8, 
            'ETH': 9, 'XMR': 10
        }
        return currency_mapping.get(currency.upper(), 0)
    
    def encode_payment_format(self, payment_format: str) -> int:
        """Encode payment format to numeric value"""
        format_mapping = {
            'WIRE': 1, 'ACH': 2, 'CHECK': 3, 'CASH': 4,
            'CRYPTO': 5, 'CARD': 6, 'TRANSFER': 7
        }
        return format_mapping.get(payment_format.upper(), 0)
    
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