import aiohttp
from typing import Dict, Any, List, Optional
import logging
import json

logger = logging.getLogger(__name__)

class AIProcessor:
    """AI处理类，负责生成AI分析结果和预警建议"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化AI处理器"""
        self.config = config["ai"]
        self.provider = self.config["provider"]
        self.provider_priority = self.config["provider_priority"]
        self.fallback_provider = self.config["fallback_provider"]
        self.api_key = self.config["api_key"]
        self.base_url = self.config["base_url"]
        self.model = self.config["model"]
        self.system_prompt = self.config["system_prompt"]
        self.temperature = self.config["temperature"]
        self.max_tokens = self.config["max_tokens"]
        self.session = None
        
    async def _ensure_session(self):
        """确保HTTP会话已初始化"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
    async def generate_response(self, prompt: str) -> str:
        """生成AI响应"""
        try:
            await self._ensure_session()
            
            async with self.session.post(
                "/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    logger.error(f"AI API error: {error_text}")
                    raise Exception(f"AI API error: {response.status}")
        except Exception as e:
            logger.error(f"生成AI响应失败: {str(e)}")
            return "AI分析生成失败，请稍后重试。"
            
    async def generate_alert_recommendations(self, analysis: str) -> List[str]:
        """生成预警建议"""
        try:
            prompt = f"""
            基于以下分析结果，生成3-5条具体的预警建议：
            
            {analysis}
            
            请以列表形式返回预警建议，每条建议应该：
            1. 具体且可操作
            2. 包含触发条件
            3. 包含建议操作
            """
            
            response = await self.generate_response(prompt)
            recommendations = [line.strip() for line in response.split('\n') if line.strip()]
            return recommendations[:5]  # 最多返回5条建议
        except Exception as e:
            logger.error(f"生成预警建议失败: {str(e)}")
            return [] 