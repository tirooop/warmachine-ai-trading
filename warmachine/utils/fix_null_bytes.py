"""
Utility to fix files containing null bytes
"""
import os
import sys

def find_and_fix_null_bytes(directory='.', extensions=('.py',), preview_only=False):
    """
    Recursively find and fix files with null bytes
    
    Args:
        directory: Directory to search recursively
        extensions: File extensions to check
        preview_only: Only preview problems, don't fix
    """
    print(f"Scanning directory: {os.path.abspath(directory)}")
    print(f"Looking for file types: {', '.join(extensions)}")
    print(f"Preview only: {preview_only}")
    print("-" * 50)
    
    fixed_count = 0
    problem_count = 0
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(extensions):
                filepath = os.path.join(root, filename)
                try:
                    # Try to open and read the file
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    
                    # Check for null bytes
                    if b'\x00' in content:
                        problem_count += 1
                        print(f"Found file with null bytes: {filepath}")
                        
                        if not preview_only:
                            # Fix the file by removing null bytes
                            clean_content = content.replace(b'\x00', b'')
                            with open(filepath, 'wb') as f:
                                f.write(clean_content)
                            fixed_count += 1
                            print(f"  - Fixed: Removed {content.count(b'\x00')} null bytes")
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
    
    print("-" * 50)
    print(f"Found {problem_count} files with null bytes")
    if not preview_only:
        print(f"Fixed {fixed_count} files")
    
    return problem_count, fixed_count

def recreate_deepseek_client():
    """Creates a clean DeepSeek client implementation"""
    # Ensure directory exists
    os.makedirs('utils/ai', exist_ok=True)
    
    # Define the clean implementation
    source_code = '''"""
DeepSeek AI API Client
"""
import os
import json
import requests

class DeepSeekClient:
    """DeepSeek client implementation"""
    
    def __init__(self, api_key=None, api_base=None, model=None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.api_base = api_base or os.environ.get("DEEPSEEK_API_BASE") or "https://api.siliconflow.cn/v1"
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-ai/DeepSeek-V3"
        
    def completion(self, prompt, model=None, temperature=0.7, max_tokens=2000):
        """Generate text completion"""
        if not self.api_key:
            return {"error": "API key not set"}
        
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
                return {"error": f"API call failed: HTTP {response.status_code}"}
                
            return response.json()
        except Exception as e:
            print(f"Call exception: {str(e)}")
            return {"error": f"API call failed: {str(e)}"}

def create_client(api_key=None, api_base=None, model=None):
    """Create client"""
    return DeepSeekClient(api_key, api_base, model)
'''
    
    # Remove old file if it exists
    client_path = 'utils/ai/deepseek_client.py'
    if os.path.exists(client_path):
        try:
            os.remove(client_path)
            print(f"Removed existing file: {client_path}")
        except Exception as e:
            print(f"Error removing file: {e}")
    
    # Write the new implementation
    try:
        with open(client_path, 'w', encoding='utf-8') as f:
            f.write(source_code)
        print(f"Created new DeepSeek client implementation")
        print(f"File size: {os.path.getsize(client_path)} bytes")
    except Exception as e:
        print(f"Error creating file: {e}")

if __name__ == "__main__":
    # Find and fix null bytes in all Python files
    print("STEP 1: Finding and fixing null bytes in Python files")
    find_and_fix_null_bytes(preview_only=False)
    
    # Recreate the DeepSeek client
    print("\nSTEP 2: Creating a clean DeepSeek client implementation")
    recreate_deepseek_client() 