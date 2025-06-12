from pymongo import MongoClient, DESCENDING
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd

class MongoHandler:
    def __init__(self, mongo_uri: str, db_name: str = "aml_system"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.transactions = self.db["transactions"]
        self.sar_reports = self.db["sar_reports"]
        
        # Create indexes
        self.transactions.create_index("Account")
        self.transactions.create_index("processed")
        self.transactions.create_index("Timestamp")
    
    def load_csv_to_mongo(self, csv_path: str) -> int:
        """Load CSV file to MongoDB"""
        try:
            # Read CSV
            df = pd.read_csv(csv_path)
            print(f"📁 Loading {len(df)} transactions from CSV...")
            
            # Convert to records and add processing flag
            transactions = df.to_dict('records')
            for tx in transactions:
                tx['processed'] = False
                tx['Timestamp'] = datetime.utcnow().isoformat() + "Z"
            
            # Insert to MongoDB
            result = self.transactions.insert_many(transactions)
            count = len(result.inserted_ids)
            
            print(f"✅ Loaded {count} transactions to MongoDB")
            return count
            
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            return 0
    
    def get_unprocessed_transactions(self, limit: int = 1) -> List[Dict[str, Any]]:
        """Get unprocessed transactions"""
        return list(self.transactions.find(
            {"processed": False}
        ).limit(limit))
    
    def mark_transaction_processed(self, transaction_id: str):
        """Mark transaction as processed"""
        from bson import ObjectId
        self.transactions.update_one(
            {"_id": ObjectId(transaction_id)},
            {"$set": {"processed": True}}
        )
    
    def get_account_transactions(self, account_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get last N transactions for an account"""
        return list(self.transactions.find(
            {"Account": account_id}
        ).sort("Timestamp", DESCENDING).limit(limit))
    
    def save_sar_report(self, sar_data: Dict[str, Any]) -> str:
        """Save SAR report to MongoDB"""
        result = self.sar_reports.insert_one(sar_data)
        return str(result.inserted_id)
    
    def get_all_sar_reports(self) -> List[Dict[str, Any]]:
        """Retrieve all SAR reports from MongoDB"""
        return list(self.sar_reports.find())

    
    def get_statistics(self) -> Dict[str, int]:
        """Get processing statistics"""
        total = self.transactions.count_documents({})
        processed = self.transactions.count_documents({"processed": True})
        unprocessed = self.transactions.count_documents({"processed": False})
        sar_count = self.sar_reports.count_documents({})
        
        return {
            "total_transactions": total,
            "processed": processed,
            "unprocessed": unprocessed,
            "sar_reports": sar_count
        }
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()