import time
import threading
from typing import Dict, Any
from simulation.transaction_generator import transaction_generator
from workflows.aml_workflow import aml_workflow
from utils.llm_client import llm_client
from database.mongo_handler import mongo_handler

class AMLSimulation:
    def __init__(self):
        self.running = False
        self.stats = {
            "transactions_processed": 0,
            "suspicious_detected": 0,
            "sars_generated": 0,
            "clean_transactions": 0
        }
    
    def check_system_health(self) -> Dict[str, bool]:
        """Check if all system components are ready"""
        health_status = {
            "mongodb": False,
            "ollama": False,
            "ml_model": False
        }
        
        try:
            # Check MongoDB
            mongo_handler.transactions_collection.find_one()
            health_status["mongodb"] = True
            print("✅ MongoDB connection: OK")
        except Exception as e:
            print(f"❌ MongoDB connection: FAILED - {e}")
        
        try:
            # Check Ollama
            health_status["ollama"] = llm_client.is_available()
            if health_status["ollama"]:
                print("✅ Ollama LLM service: OK")
            else:
                print("❌ Ollama LLM service: FAILED")
        except Exception as e:
            print(f"❌ Ollama LLM service: FAILED - {e}")
        
        try:
            # Check ML Model
            from agents.ml_detector import MLDetectorAgent
            detector = MLDetectorAgent()
            health_status["ml_model"] = detector.model is not None
            if health_status["ml_model"]:
                print("✅ ML Model: OK")
            else:
                print("❌ ML Model: FAILED")
        except Exception as e:
            print(f"❌ ML Model: FAILED - {e}")
        
        return health_status
    
    def setup_initial_data(self, num_transactions: int = 20):
        """Setup initial transaction data for simulation"""
        print(f"\n🏗️  Setting up initial data ({num_transactions} transactions)...")
        
        # Generate mix of clean and suspicious transactions
        transaction_generator.generate_batch_transactions(num_transactions)
        
        # Generate one suspicious account pattern
        transaction_generator.generate_suspicious_account_pattern()
        
        print("✅ Initial data setup complete")
    
    def run_transaction_generator_thread(self, duration_minutes: int = 30):
        """Run transaction generator in separate thread"""
        def generate_continuously():
            while self.running:
                try:
                    # Generate 1-3 transactions every 30 seconds
                    num_transactions = random.randint(1, 3)
                    transaction_generator.generate_batch_transactions(num_transactions)
                    time.sleep(30)
                except Exception as e:
                    print(f"Error in transaction generation: {e}")
                    time.sleep(10)
        
        import random
        generator_thread = threading.Thread(target=generate_continuously, daemon=True)
        generator_thread.start()
        return generator_thread
    
    def run_aml_monitoring_thread(self):
        """Run AML monitoring in separate thread"""
        def monitor_continuously():
            while self.running:
                try:
                    result = aml_workflow.run()
                    
                    if result.get("error"):
                        print(f"Workflow error: {result['error']}")
                        time.sleep(5)
                        continue
                    
                    if result.get("has_transaction", False):
                        self.stats["transactions_processed"] += 1
                        
                        transaction = result.get("current_transaction", {})
                        ml_pred = result.get("ml_prediction", {})
                        
                        if ml_pred.get("is_laundering", False):
                            self.stats["suspicious_detected"] += 1
                            print(f"⚠️  SUSPICIOUS: {transaction.get('sender_account', 'Unknown')} -> ${transaction.get('amount', 0):,.2f}")
                            print(f"   Confidence: {ml_pred.get('confidence', 0):.2%}")
                            
                            if result.get("sar_generated", False):
                                self.stats["sars_generated"] += 1
                                print(f"🚨 SAR Generated: {result.get('sar_id', 'Unknown')}")
                        else:
                            self.stats["clean_transactions"] += 1
                            print(f"✅ CLEAN: {transaction.get('sender_account', 'Unknown')} -> ${transaction.get('amount', 0):,.2f}")
                    
                    time.sleep(2)  # Check every 2 seconds
                    
                except Exception as e:
                    print(f"Error in AML monitoring: {e}")
                    time.sleep(5)
        
        monitoring_thread = threading.Thread(target=monitor_continuously, daemon=True)
        monitoring_thread.start()
        return monitoring_thread
    
    def print_stats(self):
        """Print current statistics"""
        print("\n" + "="*50)
        print("AML SYSTEM STATISTICS")
        print("="*50)
        print(f"Transactions Processed: {self.stats['transactions_processed']}")
        print(f"Clean Transactions: {self.stats['clean_transactions']}")
        print(f"Suspicious Detected: {self.stats['suspicious_detected']}")
        print(f"SAR Reports Generated: {self.stats['sars_generated']}")
        
        if self.stats['transactions_processed'] > 0:
            suspicious_rate = (self.stats['suspicious_detected'] / self.stats['transactions_processed']) * 100
            print(f"Suspicious Rate: {suspicious_rate:.1f}%")
        
        print("="*50)
    
    def run_full_simulation(self, duration_minutes: int = 10):
        """Run complete AML simulation"""
        print("\n🚀 Starting AML Detection System Simulation")
        print("="*60)
        
        # Check system health
        health = self.check_system_health()
        if not all(health.values()):
            print("\n❌ System health check failed. Please fix the issues before running simulation.")
            return
        
        # Setup initial data
        self.setup_initial_data()
        
        # Start simulation
        self.running = True
        
        # Start background threads
        print(f"\n🔄 Starting continuous monitoring for {duration_minutes} minutes...")
        generator_thread = self.run_transaction_generator_thread(duration_minutes)
        monitoring_thread = self.run_aml_monitoring_thread()
        
        # Run for specified duration
        try:
            for minute in range(duration_minutes):
                time.sleep(60)  # Wait 1 minute
                print(f"\n📊 Minute {minute + 1}/{duration_minutes} completed")
                self.print_stats()
                
        except KeyboardInterrupt:
            print("\n⏹️  Simulation interrupted by user")
        
        finally:
            self.running = False
            print(f"\n🏁 Simulation completed")
            self.print_stats()
    
    def run_single_test(self):
        """Run a single test cycle"""
        print("\n🧪 Running single test cycle...")
        
        # Check system health
        health = self.check_system_health()
        if not all(health.values()):
            print("❌ System health check failed")
            return
        
        # Generate a few test transactions
        print("Generating test transactions...")
        transaction_generator.generate_batch_transactions(5)
        transaction_generator.generate_suspicious_account_pattern()
        
        # Run AML workflow a few times
        print("Running AML detection...")
        for i in range(10):
            result = aml_workflow.run()
            if result.get("has_transaction"):
                transaction = result.get("current_transaction", {})
                ml_pred = result.get("ml_prediction", {})
                print(f"Test {i+1}: {transaction.get('sender_account', 'Unknown')} -> "
                      f"{'SUSPICIOUS' if ml_pred.get('is_laundering') else 'CLEAN'}")
                
                if result.get("sar_generated"):
                    print(f"  🚨 SAR Generated: {result.get('sar_id')}")
            else:
                print(f"Test {i+1}: No transactions to process")
            
            time.sleep(1)
        
        print("✅ Single test completed")

# Global simulation instance
aml_simulation = AMLSimulation()

if __name__ == "__main__":
    # Run simulation
    aml_simulation.run_full_simulation(duration_minutes=5)