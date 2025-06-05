import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from database.mongo_handler import mongo_handler
from utils.config import config

class TransactionGenerator:
    def __init__(self):
        self.sender_accounts = [f"ACC{str(i).zfill(6)}" for i in range(1000, 1100)]
        self.receiver_accounts = [f"ACC{str(i).zfill(6)}" for i in range(2000, 2200)]
        self.transaction_types = ["WIRE", "ACH", "CHECK", "CASH", "CRYPTO"]
        self.countries = ["US", "UK", "CH", "LU", "HK", "SG", "BS", "KY"]  # Including high-risk countries
        self.high_risk_countries = ["BS", "KY", "LU"]  # Bahamas, Cayman Islands, Luxembourg
    
    def generate_clean_transaction(self) -> Dict[str, Any]:
        """Generate a clean (non-suspicious) transaction"""
        return {
            "sender_account": random.choice(self.sender_accounts),
            "receiver_account": random.choice(self.receiver_accounts),
            "amount": round(random.uniform(100, 50000), 2),
            "transaction_type": random.choice(self.transaction_types[:3]),  # Normal types
            "sender_risk_score": random.uniform(0.1, 0.4),  # Low risk
            "receiver_risk_score": random.uniform(0.1, 0.4),  # Low risk
            "time_of_day": random.randint(8, 18),  # Business hours
            "day_of_week": random.randint(1, 5),  # Weekdays
            "cross_border": 0,  # Domestic
            "high_risk_country": 0,  # Not high-risk
            "sender_country": "US",
            "receiver_country": "US",
            "description": "Regular business transaction"
        }
    
    def generate_suspicious_transaction(self) -> Dict[str, Any]:
        """Generate a suspicious (potentially money laundering) transaction"""
        sender = random.choice(self.sender_accounts)
        receiver_country = random.choice(self.high_risk_countries)
        
        return {
            "sender_account": sender,
            "receiver_account": random.choice(self.receiver_accounts),
            "amount": round(random.uniform(50000, 500000), 2),  # Large amounts
            "transaction_type": random.choice(["CRYPTO", "WIRE", "CASH"]),  # Risky types
            "sender_risk_score": random.uniform(0.6, 0.9),  # High risk
            "receiver_risk_score": random.uniform(0.7, 0.95),  # High risk
            "time_of_day": random.choice([2, 3, 23, 1]),  # Odd hours
            "day_of_week": random.choice([6, 7]),  # Weekends
            "cross_border": 1,  # Cross-border
            "high_risk_country": 1,  # High-risk country
            "sender_country": "US",
            "receiver_country": receiver_country,
            "description": f"Large transfer to {receiver_country}"
        }
    
    def generate_structured_suspicious_pattern(self, sender_account: str, num_transactions: int = 5) -> List[Dict[str, Any]]:
        """Generate a series of transactions that form a suspicious pattern (structuring)"""
        transactions = []
        base_amount = 9500  # Just under $10,000 reporting threshold
        
        for i in range(num_transactions):
            amount_variation = random.uniform(-500, 500)
            transaction = {
                "sender_account": sender_account,
                "receiver_account": random.choice(self.receiver_accounts),
                "amount": round(base_amount + amount_variation, 2),
                "transaction_type": "WIRE",
                "sender_risk_score": random.uniform(0.7, 0.9),
                "receiver_risk_score": random.uniform(0.6, 0.8),
                "time_of_day": random.randint(1, 23),
                "day_of_week": random.randint(1, 7),
                "cross_border": random.choice([0, 1]),
                "high_risk_country": random.choice([0, 1]),
                "sender_country": "US",
                "receiver_country": random.choice(self.countries),
                "description": f"Structured transaction {i+1} - potential layering"
            }
            transactions.append(transaction)
        
        return transactions
    
    def generate_single_transaction(self) -> Dict[str, Any]:
        """Generate a single transaction (clean or suspicious based on probability)"""
        if random.random() < config.SIMULATION_LAUNDERING_PROBABILITY:
            return self.generate_suspicious_transaction()
        else:
            return self.generate_clean_transaction()
    
    def insert_transaction_to_db(self, transaction: Dict[str, Any]) -> str:
        """Insert transaction into MongoDB"""
        try:
            transaction_id = mongo_handler.insert_transaction(transaction)
            print(f"Transaction inserted: {transaction['sender_account']} -> ${transaction['amount']:,.2f}")
            return transaction_id
        except Exception as e:
            print(f"Error inserting transaction: {e}")
            return ""
    
    def generate_batch_transactions(self, count: int = 10) -> List[str]:
        """Generate a batch of transactions"""
        transaction_ids = []
        
        print(f"Generating {count} transactions...")
        
        for i in range(count):
            transaction = self.generate_single_transaction()
            transaction_id = self.insert_transaction_to_db(transaction)
            
            if transaction_id:
                transaction_ids.append(transaction_id)
            
            # Small delay between transactions
            time.sleep(0.1)
        
        print(f"Generated {len(transaction_ids)} transactions successfully")
        return transaction_ids
    
    def generate_suspicious_account_pattern(self, sender_account: str = None) -> List[str]:
        """Generate a pattern of suspicious transactions from one account"""
        if sender_account is None:
            sender_account = random.choice(self.sender_accounts)
        
        print(f"Generating suspicious pattern for account: {sender_account}")
        
        # Generate structuring pattern
        structured_transactions = self.generate_structured_suspicious_pattern(sender_account, 5)
        
        # Add one large suspicious transaction
        large_suspicious = self.generate_suspicious_transaction()
        large_suspicious["sender_account"] = sender_account
        structured_transactions.append(large_suspicious)
        
        transaction_ids = []
        for transaction in structured_transactions:
            transaction_id = self.insert_transaction_to_db(transaction)
            if transaction_id:
                transaction_ids.append(transaction_id)
            time.sleep(0.2)  # Spread out over time
        
        return transaction_ids
    
    def simulate_real_time_transactions(self, duration_minutes: int = 10, 
                                      transactions_per_minute: int = 2):
        """Simulate real-time transaction generation"""
        print(f"Starting real-time simulation for {duration_minutes} minutes...")
        print(f"Rate: {transactions_per_minute} transactions per minute")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        transaction_count = 0
        
        while datetime.now() < end_time:
            # Generate transactions for this minute
            for _ in range(transactions_per_minute):
                transaction = self.generate_single_transaction()
                self.insert_transaction_to_db(transaction)
                transaction_count += 1
            
            # Wait for next minute
            time.sleep(60 / transactions_per_minute)
        
        print(f"Simulation completed. Generated {transaction_count} transactions")
        return transaction_count

# Global transaction generator instance
transaction_generator = TransactionGenerator()