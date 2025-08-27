"""
Clean and create a new DeepSeek implementation
"""
import os
import sys

def create_clean_file():
    """Create a clean implementation file for DeepSeek"""
    # Ensure directory exists
    os.makedirs('utils/ai', exist_ok=True)
    
    # Remove existing file if it exists
    if os.path.exists('utils/ai/deepseek_client.py'):
        os.remove('utils/ai/deepseek_client.py')
    
    # Create a new implementation file
    source_code = '''"""
DeepSeek AI API Client
Provides a simple interface to the DeepSeek API
"""
import os
import json
import requests

class DeepSeekClient:
    """DeepSeek client implementation supporting custom API endpoints"""
    
    def __init__(self, api_key=None, api_base=None, model=None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.api_base = api_base or os.environ.get("DEEPSEEK_API_BASE") or "https://api.siliconflow.cn/v1"
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-ai/DeepSeek-V3"
        
    def completion(self, prompt, model=None, temperature=0.7, max_tokens=2000):
        """Generate text completion"""
        if not self.api_key:
            return {"error": "API key not set, please set DEEPSEEK_API_KEY environment variable"}
        
        model_to_use = model or self.model
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model_to_use,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            # Use custom API endpoint
            endpoint = f"{self.api_base}/chat/completions"
            print(f"Calling API: {endpoint}")
            print(f"Using model: {model_to_use}")
            
            response = requests.post(
                endpoint, 
                headers=headers, 
                json=data,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"API error: {response.status_code}")
                print(f"Response: {response.text}")
                return {"error": f"API call failed: HTTP {response.status_code}", "details": response.text}
                
            return response.json()
        except Exception as e:
            print(f"Call exception: {str(e)}")
            return {"error": f"API call failed: {str(e)}"}

# Helper function
def create_client(api_key=None, api_base=None, model=None):
    """Create client"""
    return DeepSeekClient(api_key, api_base, model)
'''
    
    # Write the implementation file using binary mode to avoid encoding issues
    with open('utils/ai/deepseek_client.py', 'wb') as f:
        f.write(source_code.encode('utf-8'))
    
    # Create an __init__.py file if it doesn't exist
    if not os.path.exists('utils/ai/__init__.py'):
        with open('utils/ai/__init__.py', 'wb') as f:
            f.write(b'# AI utilities package\n')
    
    print(f"Created clean DeepSeek client implementation")
    print(f"File size: {os.path.getsize('utils/ai/deepseek_client.py')} bytes")

if __name__ == "__main__":
    create_clean_file() 