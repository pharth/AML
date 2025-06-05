import os
from dataclasses import dataclass

@dataclass
class Config:
    # MongoDB Configuration
    MONGO_URI: str = "mongodb+srv://pkhhanchate:pkh123@cluster0.zthr0kd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    MONGO_DB_NAME: str = "aml_system"
    MONGO_COLLECTION_NAME: str = "transactions"
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"  # Change to your preferred local model
    
    # ML Model Configuration
    ML_MODEL_PATH: str = "models/aml_model.pkl"
    
    # System Configuration
    TRANSACTION_BATCH_SIZE: int = 1
    LOOKBACK_TRANSACTIONS: int = 10
    
    # Simulation Configuration
    SIMULATION_TRANSACTION_COUNT: int = 100
    SIMULATION_LAUNDERING_PROBABILITY: float = 0.1

# Global config instance
config = Config()