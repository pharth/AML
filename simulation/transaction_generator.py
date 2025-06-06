import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from database.mongo_handler import mongo_handler
from utils.config import config

class TransactionGenerator:
    def __init__(self):
        self.from_banks = [f"Bank_{chr(65+i)}" for i in range(20)]  # Bank_A to Bank_T
        self.to_banks = [f"Bank_{chr(65+i)}" for i in range(20)]
        self.from_accounts = [f"ACC{str(i).zfill(8)}" for i in range(10000000, 10001000)]
        self.to_accounts = [f"ACC{str(i).zfill(8)}" for i in range(20000000, 20001000)]
        self.payment_formats = ["WIRE", "ACH", "CHECK", "CASH", "CRYPTO", "CARD", "TRANSFER"]
        self.currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"]
    
    def generate_clean_transaction(self) -> Dict[str, Any]:
        """Generate a clean (non-suspicious) transaction"""
        currency = random.choice(self.currencies)
        amount = round(random.uniform(100, 10000), 2)
        
        return {
            "From Bank": random.choice(self.from_banks),
            "Account": random.choice(self.from_accounts),
            "To Bank": random.choice(self.to_banks),
            "Account.1": random.choice(self.to_accounts),
            "Amount Received": amount,
            "Receiving Currency": currency,
            "Payment Format": random.choice(["WIRE", "ACH", "CHECK"]),  # Normal formats
            "Is Laundering": 0  # Clean transaction
        }
    
    def generate_suspicious_transaction(self) -> Dict[str, Any]:
        """Generate a suspicious (potentially money laundering) transaction"""
        # Large amount transactions
        amount_received = round(random.uniform(50000, 500000), 2)
        
        # High-risk currency and format combinations
        receiving_currency = random.choice(self.currencies)
        
        return {
            "From Bank": random.choice(self.from_banks),
            "Account": random.choice(self.from_accounts),
            "To Bank": random.choice(self.to_banks),
            "Account.1": random.choice(self.to_accounts),
            "Amount Received": amount_received,
            "Receiving Currency": receiving_currency,
            "Payment Format": random.choice(["CRYPTO", "CASH", "WIRE"]),  # High-risk formats
            "Is Laundering": 1  # Suspicious transaction
        }
    
    def generate_structured_suspicious_pattern(self, from_account: str, num_transactions: int = 5) -> List[Dict[str, Any]]:
        """Generate a series of transactions that form a suspicious pattern (structuring)"""
        transactions = []
        base_amount = 9500  # Just under $10,000 reporting threshold
        
        for i in range(num_transactions):
            amount_variation = random.uniform(-500, 500)
            amount = round(base_amount + amount_variation, 2)
               
            transaction = {
                "From Bank": random.choice(self.from_banks),
                "Account": from_account,
                "To Bank": random.choice(self.to_banks),
                "Account.1": random.choice(self.to_accounts),
                "Amount Received": amount,
                "Receiving Currency": "USD",
                "Payment Format": "WIRE",
                "Is Laundering": 1  # Structured transactions are suspicious
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
            sender_account = transaction.get('Account', 'Unknown')
            amount = transaction.get('Amount Received', 0)
            print(f"Transaction inserted: {sender_account} -> ${amount:,.2f}")
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
    
    def generate_suspicious_account_pattern(self, from_account: str = None) -> List[str]:
        """Generate a pattern of suspicious transactions from one account"""
        if from_account is None:
            from_account = random.choice(self.from_accounts)
        
        print(f"Generating suspicious pattern for account: {from_account}")
        
        # Generate structuring pattern
        structured_transactions = self.generate_structured_suspicious_pattern(from_account, 5)
        
        # Add one large suspicious transaction
        large_suspicious = self.generate_suspicious_transaction()
        large_suspicious["Account"] = from_account
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