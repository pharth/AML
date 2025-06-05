import ollama
from typing import Dict, Any
from utils.config import config

class OllamaClient:
    def __init__(self):
        self.client = ollama.Client(host=config.OLLAMA_BASE_URL)
        self.model = config.OLLAMA_MODEL
    
    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        """Generate response using local Ollama LLM"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=False
            )
            
            return response['message']['content']
            
        except Exception as e:
            print(f"Error generating LLM response: {e}")
            return "Error generating response"
    
    def is_available(self) -> bool:
        """Check if Ollama service is available"""
        try:
            self.client.list()
            return True
        except:
            return False

# Global LLM client instance
llm_client = OllamaClient()