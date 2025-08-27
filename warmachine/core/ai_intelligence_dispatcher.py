"""
AI Intelligence Dispatcher - AI智能调度器
负责调度和管理AI模型的执行
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.tg_bot.super_commander import SuperCommander
from core.abstractions.notifications import IAlertSender

logger = logging.getLogger(__name__)

class AIIntelligenceDispatcher:
    """AI智能调度器类"""
    
    def __init__(self, config: Dict[str, Any], commander: Optional[IAlertSender] = None):
        """
        初始化AI智能调度器
        
        Args:
            config: 配置字典
            commander: IAlertSender实例，用于命令集成
        """
        self.config = config
        self.commander = commander
        self.models = {}
        self.active_tasks = {}
        
        # 注册命令到SuperCommander
        if self.commander:
            self._register_commands()
            
        logger.info("AI Intelligence Dispatcher initialized")
    
    def _register_commands(self):
        """注册AI调度命令到SuperCommander"""
        if not self.commander:
            return
            
        # 注册任务调度命令
        self.commander.register_command(
            "dispatch_task",
            self.dispatch_task,
            "调度AI任务",
            ["task_type", "params"]
        )
        
        # 注册模型管理命令
        self.commander.register_command(
            "register_model",
            self.register_model,
            "注册AI模型",
            ["model_id", "model"]
        )
        
        self.commander.register_command(
            "unregister_model",
            self.unregister_model,
            "注销AI模型",
            ["model_id"]
        )
        
        # 注册模型列表命令
        self.commander.register_command(
            "list_models",
            self._list_models,
            "列出所有已注册的模型",
            []
        )
        
        logger.info("AI dispatcher commands registered with SuperCommander")
        
    def _list_models(self) -> Dict[str, Any]:
        """列出所有已注册的模型
        
        Returns:
            Dict[str, Any]: 模型列表
        """
        return {
            "models": list(self.models.keys()),
            "active_tasks": list(self.active_tasks.keys())
        }
    
    async def dispatch_task(self, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        调度AI任务
        
        Args:
            task_type: 任务类型
            params: 任务参数
            
        Returns:
            Dict[str, Any]: 任务结果
        """
        try:
            # 根据任务类型选择合适的模型
            model = self._select_model(task_type)
            if not model:
                return {"success": False, "error": f"No suitable model found for task type: {task_type}"}
            
            # 执行任务
            result = await model.execute(params)
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"Error dispatching task: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _select_model(self, task_type: str) -> Optional[Any]:
        """
        根据任务类型选择合适的模型
        
        Args:
            task_type: 任务类型
            
        Returns:
            Optional[Any]: 选中的模型实例
        """
        # TODO: 实现模型选择逻辑
        return None
    
    async def register_model(self, model_id: str, model: Any) -> bool:
        """
        注册AI模型
        
        Args:
            model_id: 模型ID
            model: 模型实例
            
        Returns:
            bool: 是否注册成功
        """
        try:
            self.models[model_id] = model
            logger.info(f"Model {model_id} registered successfully")
            return True
        except Exception as e:
            logger.error(f"Error registering model: {str(e)}")
            return False
    
    async def unregister_model(self, model_id: str) -> bool:
        """
        注销AI模型
        
        Args:
            model_id: 模型ID
            
        Returns:
            bool: 是否注销成功
        """
        try:
            if model_id in self.models:
                del self.models[model_id]
                logger.info(f"Model {model_id} unregistered successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Error unregistering model: {str(e)}")
            return False 