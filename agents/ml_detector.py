import pickle
import numpy as np
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool


class MLState(TypedDict):
    transaction: Dict[str, Any]
    model_path: str
    result: Dict[str, Any]


@tool
def predict_transaction_tool(transaction: Dict[str, Any], model_path: str, call_count: int) -> Dict[str, Any]:
    """Predict if transaction is money laundering using ML model"""
    try:
        # Load model
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        # Extract features
        features = [
            float(hash(transaction.get('From Bank', '')) % 1000 if transaction.get('From Bank', '') else 0),
            float(_encode_account(transaction.get('Account', ''))),
            float(hash(transaction.get('To Bank', '')) % 1000 if transaction.get('To Bank', '') else 0),
            float(_encode_account(transaction.get('Account.1', ''))),
            float(transaction.get('Amount Received', 0)),
            float(_encode_currency(transaction.get('Receiving Currency', ''))),
            float(_encode_payment_format(transaction.get('Payment Format', '')))
        ]
        
        features_array = np.array(features).reshape(1, -1)
        prediction = model.predict(features_array)[0]
        
        # Get confidence
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(features_array)[0]
            confidence = max(probabilities)
        else:
            confidence = 0.8 if prediction == 1 else 0.2
        
        return {
            "is_laundering": bool(prediction == 1),
            "confidence": float(confidence),
            "features": features
        }
        
    except Exception as e:
        return {"is_laundering": False, "confidence": 0.0, "error": str(e)}


def _encode_account(account: str) -> int:
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


def _encode_currency(currency: str) -> int:
    """Encode currency to numeric value"""
    currency_map = {
        'USD': 1, 'EUR': 2, 'GBP': 3, 'JPY': 4,
        'CHF': 5, 'CAD': 6, 'AUD': 7, 'BTC': 8
    }
    return currency_map.get(currency.upper(), 0)


def _encode_payment_format(payment_format: str) -> int:
    """Encode payment format to numeric value"""
    format_map = {
        'WIRE': 1, 'ACH': 2, 'CHECK': 3, 'CASH': 4,
        'CRYPTO': 5, 'CARD': 6, 'TRANSFER': 7
    }
    return format_map.get(payment_format.upper(), 0)


class MLDetectorAgent:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.call_count = 0
        self.graph = self._create_graph()
    
    def _create_graph(self):
        """Create the LangGraph workflow"""
        workflow = StateGraph(MLState)
        
        workflow.add_node("agent", self._agent_node)
        workflow.add_edge("agent", END)
        workflow.set_entry_point("agent")
        
        return workflow.compile()
    
    def _agent_node(self, state: MLState) -> MLState:
        """Main agent node that processes ML prediction"""
        self.call_count += 1
        
        account_id = state["transaction"].get('Account', 'Unknown')
        amount = state["transaction"].get('Amount Received', 0)
        
        print(f"🤖 ML analyzing: {account_id} -> ${amount:,.2f}")
        
        # Make prediction using tool
        result = predict_transaction_tool.invoke({
            "transaction": state["transaction"],
            "model_path": state["model_path"],
            "call_count": self.call_count
        })
        
        state["result"] = result
        return state
    
    def predict(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Predict if transaction is money laundering"""
        initial_state = MLState(
            transaction=transaction,
            model_path=self.model_path,
            result={}
        )
        
        final_state = self.graph.invoke(initial_state)
        return final_state["result"]