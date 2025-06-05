from typing import Dict, Any, List
from utils.llm_client import llm_client
from database.mongo_handler import mongo_handler
from utils.config import config
import json

class SARGeneratorAgent:
    def __init__(self):
        self.name = "SARGenerator"
    
    def get_historical_transactions(self, sender_account: str) -> List[Dict[str, Any]]:
        """Get last 10 transactions from the sender account"""
        try:
            transactions = mongo_handler.get_last_n_transactions_by_sender(
                sender_account, 
                config.LOOKBACK_TRANSACTIONS
            )
            print(f"[{self.name}] Retrieved {len(transactions)} historical transactions for {sender_account}")
            return transactions
        except Exception as e:
            print(f"[{self.name}] Error retrieving historical transactions: {e}")
            return []
    
    def format_transactions_for_analysis(self, transactions: List[Dict[str, Any]]) -> str:
        """Format transactions for LLM analysis"""
        if not transactions:
            return "No transaction history available."
        
        formatted_transactions = []
        for i, tx in enumerate(transactions, 1):
            tx_str = f"""
Transaction {i}:
- Amount: ${tx.get('amount', 0):,.2f}
- Receiver: {tx.get('receiver_account', 'Unknown')}
- Type: {tx.get('transaction_type', 'Unknown')}
- Timestamp: {tx.get('timestamp', 'Unknown')}
- Cross-border: {'Yes' if tx.get('cross_border', False) else 'No'}
- High-risk country: {'Yes' if tx.get('high_risk_country', False) else 'No'}
"""
            formatted_transactions.append(tx_str)
        
        return "\n".join(formatted_transactions)
    
    def generate_sar_report(self, sender_account: str, current_transaction: Dict[str, Any], 
                          ml_prediction: Dict[str, Any], historical_transactions: List[Dict[str, Any]]) -> str:
        """Generate SAR report using LLM"""
        
        system_prompt = """You are an expert financial crime analyst tasked with generating Suspicious Activity Reports (SARs). 
        Analyze the provided transaction data and create a comprehensive SAR report that identifies potential money laundering patterns, 
        unusual transaction behaviors, and regulatory concerns. Be thorough, professional, and specific in your analysis."""
        
        historical_data = self.format_transactions_for_analysis(historical_transactions)
        
        user_prompt = f"""
SUSPICIOUS ACTIVITY DETECTED

Current Flagged Transaction:
- Sender Account: {sender_account}
- Amount: ${current_transaction.get('amount', 0):,.2f}
- Receiver: {current_transaction.get('receiver_account', 'Unknown')}
- ML Model Confidence: {ml_prediction.get('confidence', 0):.2%}

Historical Transaction Pattern (Last {len(historical_transactions)} transactions):
{historical_data}

Please generate a comprehensive Suspicious Activity Report (SAR) that includes:

1. EXECUTIVE SUMMARY
   - Brief overview of suspicious activity
   - Key risk indicators identified

2. ACCOUNT HOLDER INFORMATION
   - Account details and profile
   - Previous activity patterns

3. SUSPICIOUS ACTIVITY DESCRIPTION
   - Detailed description of concerning transactions
   - Timeline of suspicious activities
   - Patterns and anomalies identified

4. ANALYSIS AND INDICATORS
   - Red flags and warning signs
   - Comparison to normal transaction patterns
   - ML model insights and confidence levels

5. REGULATORY IMPLICATIONS
   - Potential violations identified
   - Recommended actions
   - Risk level assessment (LOW/MEDIUM/HIGH)

6. SUPPORTING DOCUMENTATION
   - Transaction references
   - Additional evidence needed

Please format the report professionally and ensure all sections are comprehensive and actionable.
"""
        
        try:
            sar_content = llm_client.generate_response(user_prompt, system_prompt)
            print(f"[{self.name}] SAR report generated for account {sender_account}")
            return sar_content
        except Exception as e:
            print(f"[{self.name}] Error generating SAR report: {e}")
            return f"Error generating SAR report: {str(e)}"
    
    def save_sar_report(self, sender_account: str, sar_content: str, 
                       current_transaction: Dict[str, Any], ml_prediction: Dict[str, Any]) -> str:
        """Save SAR report to database"""
        try:
            sar_report = {
                "sender_account": sender_account,
                "flagged_transaction_id": str(current_transaction.get("_id", "")),
                "flagged_amount": current_transaction.get("amount", 0),
                "ml_confidence": ml_prediction.get("confidence", 0),
                "sar_content": sar_content,
                "status": "PENDING_REVIEW",
                "risk_level": "HIGH" if ml_prediction.get("confidence", 0) > 0.8 else "MEDIUM"
            }
            
            sar_id = mongo_handler.insert_sar_report(sar_report)
            print(f"[{self.name}] SAR report saved with ID: {sar_id}")
            return sar_id
            
        except Exception as e:
            print(f"[{self.name}] Error saving SAR report: {e}")
            return ""
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node execution"""
        if not state.get("requires_investigation", False):
            return {"sar_generated": False, "sar_id": None}
        
        sender_account = state.get("sender_account", "")
        current_transaction = state.get("current_transaction", {})
        ml_prediction = state.get("ml_prediction", {})
        
        if not sender_account:
            return {"sar_generated": False, "sar_id": None, "error": "No sender account"}
        
        # Get historical transactions
        historical_transactions = self.get_historical_transactions(sender_account)
        
        # Generate SAR report
        sar_content = self.generate_sar_report(
            sender_account, current_transaction, ml_prediction, historical_transactions
        )
        
        # Save SAR report
        sar_id = self.save_sar_report(sender_account, sar_content, current_transaction, ml_prediction)
        
        return {
            "sar_generated": True,
            "sar_id": sar_id,
            "sar_content": sar_content[:500] + "..." if len(sar_content) > 500 else sar_content
        }