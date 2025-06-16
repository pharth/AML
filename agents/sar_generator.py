from typing import Dict, Any, List, TypedDict
import ollama
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool


class SARState(TypedDict):
    flagged_transaction: Dict[str, Any]
    ml_confidence: float
    mongo_handler: Any
    account_history: List[Dict[str, Any]]
    sar_content: str
    sar_id: str
    account_id: str
    result: Dict[str, Any]


@tool
def get_account_history_tool(account_id: str, mongo_handler) -> List[Dict[str, Any]]:
    """Get last 10 transactions from the same account"""
    try:
        transactions = mongo_handler.get_account_transactions(account_id, limit=10)
        print(f"📊 Retrieved {len(transactions)} transactions for account {account_id}")
        return transactions
    except Exception as e:
        print(f"❌ Error getting account history: {e}")
        return []


@tool
def format_transaction_history_tool(transactions: List[Dict[str, Any]]) -> str:
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


@tool
def generate_sar_report_tool(flagged_transaction: Dict[str, Any], history_text: str, 
                           ml_confidence: float, ollama_client, model: str) -> str:
    """Generate SAR report using LLM"""
    account_id = flagged_transaction.get('Account', 'Unknown')
    
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
        response = ollama_client.chat(
            model=model,
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


@tool
def save_sar_report_tool(flagged_transaction: Dict[str, Any], sar_content: str, 
                        ml_confidence: float, account_id: str, mongo_handler) -> str:
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


class SARAgent:
    def __init__(self, ollama_model: str = "tinyllama:1.1b"):
        self.client = ollama.Client()
        self.model = ollama_model
        self.graph = self._create_graph()
    
    def _create_graph(self):
        """Create the LangGraph workflow"""
        workflow = StateGraph(SARState)
        
        # Add agent nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_edge("agent", END)
        workflow.set_entry_point("agent")
        
        return workflow.compile()
    
    def _agent_node(self, state: SARState) -> SARState:
        """Main agent node that orchestrates the SAR generation process"""
        account_id = state["flagged_transaction"].get('Account', 'Unknown')
        state["account_id"] = account_id
        
        print(f"🚨 Processing suspicious transaction for account: {account_id}")
        
        # Step 1: Get account history using tool
        account_history = get_account_history_tool.invoke({
            "account_id": account_id,
            "mongo_handler": state["mongo_handler"]
        })
        state["account_history"] = account_history
        
        # Step 2: Format transaction history using tool
        history_text = format_transaction_history_tool.invoke({
            "transactions": account_history
        })
        
        # Step 3: Generate SAR report using tool
        sar_content = generate_sar_report_tool.invoke({
            "flagged_transaction": state["flagged_transaction"],
            "history_text": history_text,
            "ml_confidence": state["ml_confidence"],
            "ollama_client": self.client,
            "model": self.model
        })
        state["sar_content"] = sar_content
        
        # Step 4: Save SAR report using tool
        sar_id = save_sar_report_tool.invoke({
            "flagged_transaction": state["flagged_transaction"],
            "sar_content": sar_content,
            "ml_confidence": state["ml_confidence"],
            "account_id": account_id,
            "mongo_handler": state["mongo_handler"]
        })
        state["sar_id"] = sar_id
        
        # Step 5: Prepare result
        state["result"] = {
            "sar_id": sar_id,
            "account_id": account_id,
            "sar_content": sar_content,
            "transaction_count": len(account_history)
        }
        
        return state
    
    def process_suspicious_transaction(self, flagged_transaction: Dict[str, Any], 
                                    ml_confidence: float, mongo_handler) -> Dict[str, Any]:
        """Complete SAR generation process using agent and tools"""
        
        # Create initial state
        initial_state = SARState(
            flagged_transaction=flagged_transaction,
            ml_confidence=ml_confidence,
            mongo_handler=mongo_handler,
            account_history=[],
            sar_content="",
            sar_id="",
            account_id="",
            result={}
        )
        
        # Run the agent
        final_state = self.graph.invoke(initial_state)
        
        return final_state["result"]