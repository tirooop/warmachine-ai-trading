"""


AI Model Router - Unified interface for multiple AI models





This module provides a unified interface for interacting with different AI models


(DeepSeek, OpenAI, Claude). It allows for dynamic switching between models based


on configuration or specific needs.


"""





import os


import logging


import json


import time


import requests


from typing import Dict, Any, Optional, List





# Set up logging


logger = logging.getLogger(__name__)





class BaseAIAgent:


    """Base class for AI agents"""


    


    def __init__(self, api_key: str = "", base_url: str = ""):


        self.api_key = api_key


        self.base_url = base_url


        


    def ask(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:


        """


        Send a prompt to the AI model and get a response


        


        Args:


            prompt: The user prompt


            system_prompt: Optional system prompt


            temperature: Sampling temperature


            


        Returns:


            Model response as string


        """


        raise NotImplementedError("Subclasses must implement ask()")


        


    def generate_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:


        """


        Generate a completion from a list of messages


        


        Args:


            messages: List of message dictionaries (role, content)


            temperature: Sampling temperature


            


        Returns:


            Model completion as string


        """


        raise NotImplementedError("Subclasses must implement generate_completion()")





class DeepSeekAgent(BaseAIAgent):


    """Agent for DeepSeek AI models"""


    


    def __init__(self, api_key: str = "", base_url: str = "https://api.siliconflow.cn/v1"):


        super().__init__(api_key, base_url)


        self.model = "deepseek-ai/DeepSeek-V3"


        


    def ask(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:


        """


        Send a prompt to DeepSeek and get a response


        


        Args:


            prompt: The user prompt


            system_prompt: Optional system prompt


            temperature: Sampling temperature


            


        Returns:


            Model response as string


        """


        messages = []


        


        if system_prompt:


            messages.append({"role": "system", "content": system_prompt})


            


        messages.append({"role": "user", "content": prompt})


        


        return self.generate_completion(messages, temperature)


        


    def generate_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:


        """


        Generate a completion from DeepSeek


        


        Args:


            messages: List of message dictionaries


            temperature: Sampling temperature


            


        Returns:


            Model completion as string


        """


        try:


            headers = {


                "Content-Type": "application/json",


                "Authorization": f"Bearer {self.api_key}"


            }


            


            data = {


                "model": self.model,


                "messages": messages,


                "temperature": temperature


            }


            


            response = requests.post(


                f"{self.base_url}/chat/completions",


                headers=headers,


                json=data,


                timeout=60


            )


            


            if response.status_code == 200:


                result = response.json()


                return result["choices"][0]["message"]["content"]


            else:


                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")


                return f"Error: {response.status_code}"


                


        except Exception as e:


            logger.error(f"Failed to generate completion with DeepSeek: {str(e)}")


            return f"Error: {str(e)}"





class OpenAIAgent(BaseAIAgent):


    """Agent for OpenAI models"""


    


    def __init__(self, api_key: str = "", base_url: str = "https://api.openai.com/v1"):


        super().__init__(api_key, base_url)


        self.model = "gpt-4-turbo"


        


    def ask(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:


        """


        Send a prompt to OpenAI and get a response


        


        Args:


            prompt: The user prompt


            system_prompt: Optional system prompt


            temperature: Sampling temperature


            


        Returns:


            Model response as string


        """


        messages = []


        


        if system_prompt:


            messages.append({"role": "system", "content": system_prompt})


            


        messages.append({"role": "user", "content": prompt})


        


        return self.generate_completion(messages, temperature)


        


    def generate_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:


        """


        Generate a completion from OpenAI


        


        Args:


            messages: List of message dictionaries


            temperature: Sampling temperature


            


        Returns:


            Model completion as string


        """


        try:


            headers = {


                "Content-Type": "application/json",


                "Authorization": f"Bearer {self.api_key}"


            }


            


            data = {


                "model": self.model,


                "messages": messages,


                "temperature": temperature


            }


            


            response = requests.post(


                f"{self.base_url}/chat/completions",


                headers=headers,


                json=data,


                timeout=60


            )


            


            if response.status_code == 200:


                result = response.json()


                return result["choices"][0]["message"]["content"]


            else:


                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")


                return f"Error: {response.status_code}"


                


        except Exception as e:


            logger.error(f"Failed to generate completion with OpenAI: {str(e)}")


            return f"Error: {str(e)}"





class ClaudeAgent(BaseAIAgent):


    """Agent for Anthropic Claude models"""


    


    def __init__(self, api_key: str = "", base_url: str = "https://api.anthropic.com/v1"):


        super().__init__(api_key, base_url)


        self.model = "claude-3-opus-20240229"


        


    def ask(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:


        """


        Send a prompt to Claude and get a response


        


        Args:


            prompt: The user prompt


            system_prompt: Optional system prompt


            temperature: Sampling temperature


            


        Returns:


            Model response as string


        """


        try:


            headers = {


                "Content-Type": "application/json",


                "x-api-key": self.api_key,


                "anthropic-version": "2023-06-01"


            }


            


            data = {


                "model": self.model,


                "temperature": temperature,


                "max_tokens": 4000,


                "messages": [{"role": "user", "content": prompt}]


            }


            


            if system_prompt:


                data["system"] = system_prompt


                


            response = requests.post(


                f"{self.base_url}/messages",


                headers=headers,


                json=data,


                timeout=60


            )


            


            if response.status_code == 200:


                result = response.json()


                return result["content"][0]["text"]


            else:


                logger.error(f"Claude API error: {response.status_code} - {response.text}")


                return f"Error: {response.status_code}"


                


        except Exception as e:


            logger.error(f"Failed to generate completion with Claude: {str(e)}")


            return f"Error: {str(e)}"


            


    def generate_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:


        """


        Generate a completion from Claude


        


        Args:


            messages: List of message dictionaries


            temperature: Sampling temperature


            


        Returns:


            Model completion as string


        """


        try:


            # Extract system message if present


            system_prompt = ""


            user_messages = []


            


            for msg in messages:


                if msg["role"] == "system":


                    system_prompt = msg["content"]


                else:


                    user_messages.append(msg)


                    


            # Combine user messages


            combined_prompt = ""


            for msg in user_messages:


                role_prefix = "Human: " if msg["role"] == "user" else "Assistant: "


                combined_prompt += f"{role_prefix}{msg['content']}\n\n"


                


            if not combined_prompt:


                combined_prompt = "Please provide market analysis."


                


            return self.ask(combined_prompt, system_prompt, temperature)


            


        except Exception as e:


            logger.error(f"Failed to generate completion with Claude: {str(e)}")


            return f"Error: {str(e)}"





class AIModelRouter:


    """Router for multiple AI models"""


    


    def __init__(self, config: Dict[str, Any]):


        """


        Initialize the AI Model Router


        


        Args:


            config: Configuration dictionary


        """


        self.config = config


        self.ai_config = config.get("ai", {})


        


        # Initialize agents


        self.agents = {


            "deepseek": DeepSeekAgent(


                api_key=self.ai_config.get("api_key", ""),


                base_url=self.ai_config.get("base_url", "https://api.siliconflow.cn/v1")


            ),


            "openai": OpenAIAgent(


                api_key=self.ai_config.get("fallback_api_key", ""),


                base_url="https://api.openai.com/v1"


            ),


            "claude": ClaudeAgent(


                api_key=self.ai_config.get("claude_api_key", ""),


                base_url="https://api.anthropic.com/v1"


            )


        }


        


        # Set default model from config


        self.default_model = self.ai_config.get("provider", "deepseek")


        self.fallback_model = self.ai_config.get("fallback_provider", "openai")


        


        logger.info(f"AI Model Router initialized with default model: {self.default_model}")


        


    def ask(self, prompt: str, model: str = None, system_prompt: str = "", temperature: float = 0.7) -> str:


        """


        Send a prompt to an AI model and get a response


        


        Args:


            prompt: The user prompt


            model: Model to use (deepseek, openai, claude)


            system_prompt: Optional system prompt


            temperature: Sampling temperature


            


        Returns:


            Model response as string


        """


        # Use specified model or default


        model = model or self.default_model


        


        # Get the agent


        agent = self.agents.get(model)


        


        if not agent:


            logger.warning(f"Unknown model: {model}, using default: {self.default_model}")


            agent = self.agents.get(self.default_model)


            


        # Try primary model


        try:


            response = agent.ask(prompt, system_prompt, temperature)


            


            # If there's an error response, try fallback


            if response.startswith("Error:") and model != self.fallback_model:


                logger.warning(f"Primary model {model} failed, trying fallback: {self.fallback_model}")


                fallback_agent = self.agents.get(self.fallback_model)


                return fallback_agent.ask(prompt, system_prompt, temperature)


                


            return response


            


        except Exception as e:


            logger.error(f"Error using model {model}: {str(e)}")


            


            # Try fallback if different from current model


            if model != self.fallback_model:


                logger.info(f"Trying fallback model: {self.fallback_model}")


                try:


                    fallback_agent = self.agents.get(self.fallback_model)


                    return fallback_agent.ask(prompt, system_prompt, temperature)


                except Exception as fallback_error:


                    logger.error(f"Fallback model also failed: {str(fallback_error)}")


                    


            return f"Error: Unable to get response from AI models - {str(e)}"


            


    def generate_completion(self, messages: List[Dict[str, str]], model: str = None, temperature: float = 0.7) -> str:


        """


        Generate a completion from a list of messages


        


        Args:


            messages: List of message dictionaries (role, content)


            model: Model to use (deepseek, openai, claude)


            temperature: Sampling temperature


            


        Returns:


            Model completion as string


        """


        # Use specified model or default


        model = model or self.default_model


        


        # Get the agent


        agent = self.agents.get(model)


        


        if not agent:


            logger.warning(f"Unknown model: {model}, using default: {self.default_model}")


            agent = self.agents.get(self.default_model)


            


        # Try primary model


        try:


            response = agent.generate_completion(messages, temperature)


            


            # If there's an error response, try fallback


            if response.startswith("Error:") and model != self.fallback_model:


                logger.warning(f"Primary model {model} failed, trying fallback: {self.fallback_model}")


                fallback_agent = self.agents.get(self.fallback_model)


                return fallback_agent.generate_completion(messages, temperature)


                


            return response


            


        except Exception as e:


            logger.error(f"Error using model {model}: {str(e)}")


            


            # Try fallback if different from current model


            if model != self.fallback_model:


                logger.info(f"Trying fallback model: {self.fallback_model}")


                try:


                    fallback_agent = self.agents.get(self.fallback_model)


                    return fallback_agent.generate_completion(messages, temperature)


                except Exception as fallback_error:


                    logger.error(f"Fallback model also failed: {str(fallback_error)}")


                    


            return f"Error: Unable to get completion from AI models - {str(e)}"


            


    def get_available_models(self) -> List[str]:


        """


        Get list of available models


        


        Returns:


            List of model names


        """


        return list(self.agents.keys())


        


    def switch_default_model(self, model: str) -> bool:


        """


        Switch the default model


        


        Args:


            model: Model to set as default


            


        Returns:


            Success status


        """


        if model in self.agents:


            self.default_model = model


            logger.info(f"Default model switched to: {model}")


            return True


        else:


            logger.warning(f"Cannot switch to unknown model: {model}")


            return False


    async def start(self):
        """Async start method for compatibility with system startup."""
        pass 