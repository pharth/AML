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
        
        # Check MongoDB
        try:
            mongo_handler.transactions_collection.find_one()
            health_status["mongodb"] = True
            print("✅ MongoDB connection: OK")
        except Exception as e:
            print(f"❌ MongoDB connection: FAILED - {e}")
        
        # Check Ollama
        try:
            health_status["ollama"] = llm_client.is_available()
            if health_status["ollama"]:
                print("✅ Ollama LLM service: OK")
            else:
                print("❌ Ollama LLM service: FAILED")
        except Exception as e:
            print(f"❌ Ollama LLM service: FAILED - {e}")
        
        # Check ML Model with enhanced testing
        try:
            from agents.ml_detector import MLDetectorAgent
            detector = MLDetectorAgent()
            
            if detector.model is not None:
                # Test the model with dummy data
                test_result = detector.test_model()
                health_status["ml_model"] = test_result
                if test_result:
                    print("✅ ML Model: OK")
                else:
                    print("❌ ML Model: LOADED but failed test")
            else:
                health_status["ml_model"] = False
                print("❌ ML Model: FAILED to load")
                
        except Exception as e:
            print(f"❌ ML Model: FAILED - {e}")
            health_status["ml_model"] = False
        
        return health_status
    
    def install_missing_dependencies(self):
        """Install missing dependencies"""
        print("\n🔧 Checking and installing missing dependencies...")
        
        try:
            import subprocess
            import sys
            
            # Check for XGBoost
            try:
                import xgboost
                print("✅ XGBoost already installed")
            except ImportError:
                print("📦 Installing XGBoost...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost"])
                print("✅ XGBoost installed successfully")
            
            # Check for other common ML dependencies
            dependencies = ["scikit-learn", "numpy", "pandas"]
            for dep in dependencies:
                try:
                    __import__(dep.replace("-", "_"))
                    print(f"✅ {dep} already installed")
                except ImportError:
                    print(f"📦 Installing {dep}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                    print(f"✅ {dep} installed successfully")
                    
        except Exception as e:
            print(f"❌ Error installing dependencies: {e}")
            return False
        
        return True
    
    def setup_initial_data(self, num_transactions: int = 20):
        """Setup initial transaction data for simulation"""
        print(f"\n🏗️  Setting up initial data ({num_transactions} transactions)...")
        
        try:
            # Generate mix of clean and suspicious transactions
            transaction_generator.generate_batch_transactions(num_transactions)
            
            # Generate one suspicious account pattern
            transaction_generator.generate_suspicious_account_pattern()
            
            print("✅ Initial data setup complete")
        except Exception as e:
            print(f"❌ Error setting up initial data: {e}")
    
    def run_transaction_generator_thread(self, duration_minutes: int = 30):
        """Run transaction generator in separate thread"""
        def generate_continuously():
            import random
            while self.running:
                try:
                    # Generate 1-3 transactions every 30 seconds
                    num_transactions = random.randint(1, 3)
                    transaction_generator.generate_batch_transactions(num_transactions)
                    print(f"🔄 Generated {num_transactions} new transactions")
                    time.sleep(30)
                except Exception as e:
                    print(f"Error in transaction generation: {e}")
                    time.sleep(10)
        
        generator_thread = threading.Thread(target=generate_continuously, daemon=True)
        generator_thread.start()
        return generator_thread
    
    def run_aml_monitoring_thread(self):
        """Run AML monitoring in separate thread"""
        def monitor_continuously():
            consecutive_errors = 0
            while self.running:
                try:
                    result = aml_workflow.run()
                    consecutive_errors = 0  # Reset error counter on success
                    
                    if result.get("error"):
                        print(f"Workflow error: {result['error']}")
                        time.sleep(5)
                        continue
                    
                    if result.get("has_transaction", False):
                        self.stats["transactions_processed"] += 1
                        
                        transaction = result.get("current_transaction", {})
                        ml_pred = result.get("ml_prediction", {})
                        
                        # Handle case where ML prediction might have errors
                        if ml_pred and not ml_pred.get("error"):
                            if ml_pred.get("is_laundering", False):
                                self.stats["suspicious_detected"] += 1
                                sender = transaction.get("Account", transaction.get("sender_account", "Unknown"))
                                amount = transaction.get("Amount", transaction.get("amount", 0))
                                print(f"⚠️  SUSPICIOUS: {sender} -> ${amount:,.2f}")
                                print(f"   Confidence: {ml_pred.get('confidence', 0):.2%}")
                                
                                if result.get("sar_generated", False):
                                    self.stats["sars_generated"] += 1
                                    print(f"🚨 SAR Generated: {result.get('sar_id', 'Unknown')}")
                            else:
                                self.stats["clean_transactions"] += 1
                                sender = transaction.get("Account", transaction.get("sender_account", "Unknown"))
                                amount = transaction.get("Amount", transaction.get("amount", 0))
                                print(f"✅ CLEAN: {sender} -> ${amount:,.2f}")
                        else:
                            # Handle ML prediction errors
                            error_msg = ml_pred.get("error", "Unknown ML error") if ml_pred else "No ML prediction"
                            print(f"⚠️  ML Prediction Error: {error_msg}")
                    
                    time.sleep(2)  # Check every 2 seconds
                    
                except Exception as e:
                    consecutive_errors += 1
                    print(f"Error in AML monitoring: {e}")
                    
                    # If too many consecutive errors, increase sleep time
                    if consecutive_errors > 5:
                        print("⚠️  Multiple consecutive errors detected, slowing down monitoring...")
                        time.sleep(15)
                    else:
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
        
        # Install missing dependencies first
        if not self.install_missing_dependencies():
            print("❌ Failed to install dependencies. Please install manually.")
            return
        
        # Check system health
        health = self.check_system_health()
        
        if not health["ml_model"]:
            print("\n❌ ML Model health check failed. Attempting to fix...")
            # Try to reload the ML model after installing dependencies
            try:
                from agents.ml_detector import MLDetectorAgent
                detector = MLDetectorAgent()
                if detector.model is not None and detector.test_model():
                    print("✅ ML Model fixed successfully")
                    health["ml_model"] = True
                else:
                    print("❌ ML Model still not working")
            except Exception as e:
                print(f"❌ Could not fix ML Model: {e}")
        
        if not all(health.values()):
            print("\n⚠️  Some system components failed health check:")
            for component, status in health.items():
                print(f"  {component}: {'✅ OK' if status else '❌ FAILED'}")
            
            # Ask user if they want to continue
            response = input("\nContinue with partial system? (y/n): ").lower().strip()
            if response != 'y':
                print("Simulation cancelled.")
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
        
        # Install dependencies and check health
        self.install_missing_dependencies()
        health = self.check_system_health()
        
        if not health["ml_model"]:
            print("❌ ML Model not available for testing")
        
        # Generate a few test transactions
        print("Generating test transactions...")
        try:
            transaction_generator.generate_batch_transactions(5)
            transaction_generator.generate_suspicious_account_pattern()
        except Exception as e:
            print(f"❌ Error generating test transactions: {e}")
            return
        
        # Run AML workflow a few times
        print("Running AML detection...")
        for i in range(10):
            try:
                result = aml_workflow.run()
                if result.get("has_transaction"):
                    transaction = result.get("current_transaction", {})
                    ml_pred = result.get("ml_prediction", {})
                    
                    sender = transaction.get("Account", transaction.get("sender_account", "Unknown"))
                    
                    if ml_pred and not ml_pred.get("error"):
                        status = "SUSPICIOUS" if ml_pred.get("is_laundering") else "CLEAN"
                        confidence = ml_pred.get("confidence", 0)
                        print(f"Test {i+1}: {sender} -> {status} (confidence: {confidence:.2f})")
                    else:
                        error_msg = ml_pred.get("error", "No prediction") if ml_pred else "No ML prediction"
                        print(f"Test {i+1}: {sender} -> ERROR: {error_msg}")
                    
                    if result.get("sar_generated"):
                        print(f"  🚨 SAR Generated: {result.get('sar_id')}")
                else:
                    print(f"Test {i+1}: No transactions to process")
                
            except Exception as e:
                print(f"Test {i+1}: Error - {e}")
            
            time.sleep(1)
        
        print("✅ Single test completed")

# Global simulation instance
aml_simulation = AMLSimulation()

if __name__ == "__main__":
    # Run simulation
    aml_simulation.run_full_simulation(duration_minutes=5)