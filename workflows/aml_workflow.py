from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from agents.transaction_monitor import TransactionMonitorAgent
from agents.ml_detector import MLDetectorAgent
from agents.sar_generator import SARGeneratorAgent

# Define the state structure
class AMLState(TypedDict):
    # Transaction monitoring
    current_transaction: Dict[str, Any]
    ml_features: list
    has_transaction: bool
    
    # ML detection
    ml_prediction: Dict[str, Any]
    requires_investigation: bool
    sender_account: str
    
    # SAR generation
    sar_generated: bool
    sar_id: str
    sar_content: str
    
    # Error handling
    error: str

class AMLWorkflow:
    def __init__(self):
        self.transaction_monitor = TransactionMonitorAgent()
        self.ml_detector = MLDetectorAgent()
        self.sar_generator = SARGeneratorAgent()
        
        self.workflow = self.build_workflow()
    
    def build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create the workflow graph
        workflow = StateGraph(AMLState)
        
        # Add nodes
        workflow.add_node("monitor_transactions", self.transaction_monitor)
        workflow.add_node("detect_laundering", self.ml_detector)
        workflow.add_node("generate_sar", self.sar_generator)
        
        # Define the workflow flow
        workflow.set_entry_point("monitor_transactions")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "monitor_transactions",
            self.should_process_transaction,
            {
                "process": "detect_laundering",
                "skip": END
            }
        )
        
        workflow.add_conditional_edges(
            "detect_laundering",
            self.should_generate_sar,
            {
                "generate_sar": "generate_sar",
                "clean": END
            }
        )
        
        workflow.add_edge("generate_sar", END)
        
        return workflow.compile()
    
    def should_process_transaction(self, state: AMLState) -> str:
        """Determine if we should process the transaction"""
        return "process" if state.get("has_transaction", False) else "skip"
    
    def should_generate_sar(self, state: AMLState) -> str:
        """Determine if we should generate SAR report"""
        return "generate_sar" if state.get("requires_investigation", False) else "clean"
    
    def run(self, initial_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the AML workflow"""
        if initial_state is None:
            initial_state = {}
        
        try:
            result = self.workflow.invoke(initial_state)
            return result
        except Exception as e:
            print(f"Workflow error: {e}")
            return {"error": str(e)}
    
    def run_continuous(self, max_iterations: int = 100):
        """Run the workflow continuously for simulation"""
        print("Starting continuous AML monitoring...")
        
        for i in range(max_iterations):
            print(f"\n--- Iteration {i+1} ---")
            
            result = self.run()
            
            if result.get("error"):
                print(f"Error in iteration {i+1}: {result['error']}")
                continue
            
            if result.get("has_transaction", False):
                transaction = result.get("current_transaction", {})
                ml_pred = result.get("ml_prediction", {})
                
                print(f"Processed transaction: {transaction.get('sender_account', 'Unknown')} -> ${transaction.get('amount', 0):,.2f}")
                print(f"ML Prediction: {'SUSPICIOUS' if ml_pred.get('is_laundering', False) else 'CLEAN'} (Confidence: {ml_pred.get('confidence', 0):.2%})")
                
                if result.get("sar_generated", False):
                    print(f"🚨 SAR Report Generated! ID: {result.get('sar_id', 'Unknown')}")
                    print(f"SAR Preview: {result.get('sar_content', '')[:200]}...")
            else:
                print("No new transactions to process")
            
            # Small delay to prevent overwhelming the system
            import time
            time.sleep(1)
        
        print(f"\nCompleted {max_iterations} monitoring iterations")

# Create workflow instance
aml_workflow = AMLWorkflow()