import os
import sys

# Set environment variables
os.environ['DEEPSEEK_API_KEY'] = "sk-uvbjgxuaigsbjpebfthckspmnpfjixhwuwapwsrrqprfvarl"
os.environ['DEEPSEEK_API_BASE'] = "https://api.siliconflow.cn/v1"
os.environ['DEEPSEEK_MODEL'] = "deepseek-ai/DeepSeek-V3"

# Create directory if it doesn't exist
os.makedirs('utils/ai', exist_ok=True)

# Create the DeepSeek client file
with open('utils/ai/deepseek_client.py', 'w', encoding='utf-8') as f:
    f.write("""# DeepSeek API Client
import os
import json
import requests

class DeepSeekClient:
    \"\"\"Simplified DeepSeek client implementation supporting custom API endpoints\"\"\"
    
    def __init__(self, api_key=None, api_base=None, model=None):
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        self.api_base = api_base or os.environ.get('DEEPSEEK_API_BASE') or "https://api.siliconflow.cn/v1"
        self.model = model or os.environ.get('DEEPSEEK_MODEL') or "deepseek-ai/DeepSeek-V3"
        
    def completion(self, prompt, model=None, temperature=0.7, max_tokens=2000):
        \"\"\"Generate text completion\"\"\"
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
    \"\"\"Create client\"\"\"
    return DeepSeekClient(api_key, api_base, model)
""")

print("Fixed DeepSeek client file and set environment variables")
print("Environment variables:")
print(f"DEEPSEEK_API_KEY: {'Set' if os.environ.get('DEEPSEEK_API_KEY') else 'Not set'}")
print(f"DEEPSEEK_API_BASE: {os.environ.get('DEEPSEEK_API_BASE', 'Not set')}")
print(f"DEEPSEEK_MODEL: {os.environ.get('DEEPSEEK_MODEL', 'Not set')}") 