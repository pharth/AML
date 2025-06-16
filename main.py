import argparse
import time
from pathlib import Path

from agents.ml_detector import MLDetectorAgent
from agents.sar_generator import SARAgent
from database.mongo_handler import MongoHandler

from dotenv import load_dotenv
import os

class AMLSimulation:
    def __init__(self):
        # Configuration
        load_dotenv()

        self.mongo_uri = os.getenv("MONGO_URI")
        self.model_path = os.getenv("MODEL_PATH")
        self.csv_path = os.getenv("CSV_PATH")
        
        # Initialize components
        self.mongo = MongoHandler(self.mongo_uri)
        self.ml_detector = MLDetectorAgent(self.model_path)
        self.sar_generator = SARAgent()
        
        # Statistics
        self.stats = {
            "processed": 0,
            "suspicious": 0,
            "clean": 0,
            "sars_generated": 0,
            "errors": 0
        }
    
    def load_csv_data(self):
        """Load CSV data to MongoDB"""
        print("🔄 Loading CSV data to MongoDB...")
        
        if not Path(self.csv_path).exists():
            print(f"❌ CSV file not found: {self.csv_path}")
            return False
        
        count = self.mongo.load_csv_to_mongo(self.csv_path)
        if count > 0:
            print(f"✅ Successfully loaded {count} transactions")
            return True
        else:
            print("❌ Failed to load CSV data")
            return False
    
    def process_single_transaction(self, transaction):
        """Process a single transaction through both agents"""
        try:
            transaction_id = str(transaction.get('_id', ''))
            account_id = transaction.get('Account', 'Unknown')
            amount = transaction.get('Amount Received', 0)
            
            print(f"\n🔍 Processing: {account_id} -> ${amount:,.2f}")
            
            # Agent 1: ML Detection
            ml_result = self.ml_detector.predict(transaction)
            
            if ml_result.get("error"):
                print(f"❌ ML Error: {ml_result['error']}")
                self.stats["errors"] += 1
                return
            
            is_laundering = ml_result.get("is_laundering", False)
            confidence = ml_result.get("confidence", 0)
            
            if is_laundering:
                print(f"🚨 SUSPICIOUS - Confidence: {confidence:.2%}")
                self.stats["suspicious"] += 1
                
                # Agent 2: SAR Generation
                sar_result = self.sar_generator.process_suspicious_transaction(
                    transaction, confidence, self.mongo
                )
                
                if sar_result.get("sar_id"):
                    self.stats["sars_generated"] += 1
                    print(f"📄 SAR Generated: {sar_result['sar_id']}")
                
            else:
                print(f"✅ CLEAN - Confidence: {confidence:.2%}")
                self.stats["clean"] += 1
            
            # Mark as processed
            self.mongo.mark_transaction_processed(transaction_id)
            self.stats["processed"] += 1
            
        except Exception as e:
            print(f"❌ Error processing transaction: {e}")
            self.stats["errors"] += 1
    
    def run_simulation(self):
        """Run the main simulation"""
        print("\n🚀 Starting AML Detection Simulation")
        print("=" * 50)
        
        # Check if we have data
        db_stats = self.mongo.get_statistics()
        print(f"📊 Database Status:")
        print(f"   Total transactions: {db_stats['total_transactions']}")
        print(f"   Unprocessed: {db_stats['unprocessed']}")
        print(f"   Existing SARs: {db_stats['sar_reports']}")
        
        if db_stats['unprocessed'] == 0:
            print("\n⚠️  No unprocessed transactions found!")
            print("   Use --load-csv to load data first")
            return
        
        # Process transactions
        print(f"\n🔄 Processing {db_stats['unprocessed']} transactions...")
        
        while True:
            # Get next unprocessed transaction
            transactions = self.mongo.get_unprocessed_transactions(limit=1)
            
            if not transactions:
                print("\n✅ All transactions processed!")
                break
            
            # Process the transaction
            self.process_single_transaction(transactions[0])
            
            # Small delay to see progress
            time.sleep(0.5)
        
        # Show final results
        self.show_results()
    
    def show_results(self):
        """Display simulation results"""
        print("\n" + "=" * 50)
        print("🎯 SIMULATION RESULTS")
        print("=" * 50)
        print(f"Transactions Processed: {self.stats['processed']}")
        print(f"Clean Transactions: {self.stats['clean']}")
        print(f"Suspicious Detected: {self.stats['suspicious']}")
        print(f"SAR Reports Generated: {self.stats['sars_generated']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['processed'] > 0:
            suspicious_rate = (self.stats['suspicious'] / self.stats['processed']) * 100
            print(f"Suspicious Rate: {suspicious_rate:.1f}%")
        
        # Database stats
        db_stats = self.mongo.get_statistics()
        print(f"\n📊 Database Status:")
        print(f"Total Transactions: {db_stats['total_transactions']}")
        print(f"Total SAR Reports: {db_stats['sar_reports']}")
        print("=" * 50)
    
    def health_check(self):
        """Check system health"""
        print("🏥 System Health Check")
        print("=" * 30)
        
        # Check MongoDB
        try:
            self.mongo.get_statistics()
            print("✅ MongoDB: Connected")
        except Exception as e:
            print(f"❌ MongoDB: {e}")
        
        # Check ML Model
        try:
            with open(self.model_path, 'rb') as f:
                import pickle
                pickle.load(f)
            print("✅ ML Model: Loaded")
        except Exception as e:
            print(f"❌ ML Model: {e}")
        
        # Check CSV file
        if Path(self.csv_path).exists():
            print("✅ CSV File: Found")
        else:
            print("❌ CSV File: Not found")
        
        # Check Ollama
        try:
            self.sar_generator.client.list()
            print("✅ Ollama: Connected")
        except Exception as e:
            print(f"❌ Ollama: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.mongo.close()

def main():
    parser = argparse.ArgumentParser(description="Simplified AML Detection System")
    parser.add_argument('--load-csv', action='store_true', help='Load CSV data to MongoDB')
    parser.add_argument('--simulate', action='store_true', help='Run simulation')
    parser.add_argument('--health', action='store_true', help='Check system health')
    parser.add_argument('--results', action='store_true', help='Show current results')
    
    args = parser.parse_args()
    
    simulation = AMLSimulation()
    
    try:
        if args.load_csv:
            simulation.load_csv_data()
        
        elif args.simulate:
            simulation.run_simulation()
        
        elif args.health:
            simulation.health_check()
        
        elif args.results:
            simulation.show_results()
        
        else:
            print("🏦 AML Detection System")
            print("Usage:")
            print("  --load-csv    Load CSV data to MongoDB")
            print("  --simulate    Run detection simulation")
            print("  --health      Check system health")
            print("  --results     Show current results")
    
    except KeyboardInterrupt:
        print("\n⏹️  Simulation interrupted")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    finally:
        simulation.cleanup()

if __name__ == "__main__":
    main()