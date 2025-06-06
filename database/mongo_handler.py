from pymongo import MongoClient, DESCENDING
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.config import config

class MongoHandler:
    def __init__(self):
        self.client = MongoClient(config.MONGO_URI)
        self.db = self.client[config.MONGO_DB_NAME]
        self.transactions_collection = self.db[config.MONGO_COLLECTION_NAME]
        self.sar_collection = self.db["sar_reports"]
        
        # Create indexes for better performance based on your data columns
        self.transactions_collection.create_index("Timestamp")
        self.transactions_collection.create_index("Account")  # From Account
        self.transactions_collection.create_index("processed")
        self.transactions_collection.create_index("From Bank")
        self.transactions_collection.create_index("To Bank")
    
    def insert_transaction(self, transaction: Dict[str, Any]) -> str:
        """Insert a new transaction into MongoDB"""
        # Add processing flag, keep original timestamp
        transaction['processed'] = False
        if 'Timestamp' not in transaction:
            transaction['Timestamp'] = datetime.utcnow().isoformat() + "Z"
        
        result = self.transactions_collection.insert_one(transaction)
        return str(result.inserted_id)
    
    def get_unprocessed_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get unprocessed transactions"""
        return list(self.transactions_collection.find(
            {"processed": False}
        ).limit(limit))
    
    def mark_transaction_processed(self, transaction_id: str):
        """Mark transaction as processed"""
        from bson import ObjectId
        self.transactions_collection.update_one(
            {"_id": ObjectId(transaction_id)},
            {"$set": {"processed": True}}
        )
    
    def get_last_n_transactions_by_sender(self, sender_account: str, n: int = 10) -> List[Dict[str, Any]]:
        """Get last N transactions by sender account (using 'Account' field)"""
        return list(self.transactions_collection.find(
            {"Account": sender_account}  # Changed from "sender_account" to "Account"
        ).sort("Timestamp", DESCENDING).limit(n))
    
    def insert_sar_report(self, sar_report: Dict[str, Any]) -> str:
        """Insert SAR report into MongoDB"""
        sar_report['created_at'] = datetime.utcnow()
        result = self.sar_collection.insert_one(sar_report)
        return str(result.inserted_id)
    
    def close_connection(self):
        """Close MongoDB connection"""
        self.client.close()

# Global MongoDB handler instance
mongo_handler = MongoHandler()