from typing import Dict, Any, List
import ollama
from datetime import datetime

class SARGenerator:
    def __init__(self, ollama_model: str = "dolphin-mistral:latest"):
        self.client = ollama.Client()
        self.model = ollama_model
    
    def get_account_history(self, account_id: str, mongo_handler) -> List[Dict[str, Any]]:
        """Get last 10 transactions from the same account"""
        try:
            transactions = mongo_handler.get_account_transactions(account_id, limit=10)
            print(f"📊 Retrieved {len(transactions)} transactions for account {account_id}")
            return transactions
        except Exception as e:
            print(f"❌ Error getting account history: {e}")
            return []
    
    def format_transaction_history(self, transactions: List[Dict[str, Any]]) -> str:
        """Format transaction history for SAR report"""
        if not transactions:
            return "No transaction history available."
        
        formatted = []
        for i, tx in enumerate(transactions, 1):
            tx_str = f"""
Transaction {i}:
- From: {tx.get('From Bank', 'Unknown')} (Account: {tx.get('Account', 'Unknown')})
- To: {tx.get('To Bank', 'Unknown')} (Account: {tx.get('Account.1', 'Unknown')})
- Amount: ${tx.get('Amount Received', 0):,.2f} {tx.get('Receiving Currency', 'USD')}
- Format: {tx.get('Payment Format', 'Unknown')}
- Date: {tx.get('Timestamp', 'Unknown')}
"""
            formatted.append(tx_str)
        
        return "\n".join(formatted)
    
    def generate_sar_report(self, flagged_transaction: Dict[str, Any], 
                          account_history: List[Dict[str, Any]], 
                          ml_confidence: float) -> str:
        """Generate SAR report using LLM"""
        
        account_id = flagged_transaction.get('Account', 'Unknown')
        history_text = self.format_transaction_history(account_history)
        
        prompt = f"""
Generate a comprehensive Suspicious Activity Report (SAR) for the following flagged transaction:

FLAGGED TRANSACTION:
- Account: {account_id}
- From Bank: {flagged_transaction.get('From Bank', 'Unknown')}
- To Bank: {flagged_transaction.get('To Bank', 'Unknown')}
- Amount: ${flagged_transaction.get('Amount Received', 0):,.2f} {flagged_transaction.get('Receiving Currency', 'USD')}
- Payment Format: {flagged_transaction.get('Payment Format', 'Unknown')}
- ML Confidence: {ml_confidence:.2%}

ACCOUNT TRANSACTION HISTORY (Last 10 transactions):
{history_text}

Please generate a professional SAR report with the following sections:

1. EXECUTIVE SUMMARY
2. ACCOUNT INFORMATION
3. SUSPICIOUS ACTIVITY DESCRIPTION
4. PATTERN ANALYSIS
5. RISK ASSESSMENT
6. RECOMMENDED ACTIONS

Be specific about suspicious patterns, amounts, timing, and any red flags identified.
"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial crime analyst. Generate comprehensive, professional SAR reports."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"❌ Error generating SAR report: {e}")
            return f"Error generating SAR report: {str(e)}"
    
    def save_sar_report(self, account_id: str, flagged_transaction: Dict[str, Any], 
                       sar_content: str, ml_confidence: float, mongo_handler) -> str:
        """Save SAR report to MongoDB"""
        try:
            sar_data = {
                "account_id": account_id,
                "flagged_transaction_id": str(flagged_transaction.get('_id', '')),
                "from_bank": flagged_transaction.get('From Bank', ''),
                "to_bank": flagged_transaction.get('To Bank', ''),
                "amount": flagged_transaction.get('Amount Received', 0),
                "currency": flagged_transaction.get('Receiving Currency', ''),
                "payment_format": flagged_transaction.get('Payment Format', ''),
                "ml_confidence": ml_confidence,
                "sar_content": sar_content,
                "created_at": datetime.utcnow(),
                "status": "PENDING_REVIEW"
            }
            
            sar_id = mongo_handler.save_sar_report(sar_data)
            print(f"💾 SAR report saved with ID: {sar_id}")
            return sar_id
            
        except Exception as e:
            print(f"❌ Error saving SAR report: {e}")
            return ""
    
    def process_suspicious_transaction(self, flagged_transaction: Dict[str, Any], 
                                    ml_confidence: float, mongo_handler) -> Dict[str, Any]:
        """Complete SAR generation process"""
        account_id = flagged_transaction.get('Account', 'Unknown')
        
        print(f"🚨 Processing suspicious transaction for account: {account_id}")
        
        # Get account history
        account_history = self.get_account_history(account_id, mongo_handler)
        
        # Generate SAR report
        sar_content = self.generate_sar_report(flagged_transaction, account_history, ml_confidence)
        
        # Save SAR report
        sar_id = self.save_sar_report(account_id, flagged_transaction, sar_content, ml_confidence, mongo_handler)
        
        return {
            "sar_id": sar_id,
            "account_id": account_id,
            "sar_content": sar_content,
            "transaction_count": len(account_history)
        }