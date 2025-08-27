"""


Web API - REST API endpoints for WarMachine platform





This module provides RESTful API endpoints for the WarMachine trading platform,


allowing users to interact with the platform through HTTP requests.


"""





import os


import logging


import json


import time


import hashlib


from datetime import datetime, timedelta


from typing import Dict, Any, Optional, List, Union


from pathlib import Path





import uvicorn


from fastapi import FastAPI, Depends, HTTPException, status, Request, Body, BackgroundTasks


from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


from fastapi.middleware.cors import CORSMiddleware


from fastapi.responses import JSONResponse


from pydantic import BaseModel, Field, EmailStr


import threading





# Set up logging


logger = logging.getLogger(__name__)





# Import platform modules


try:


    from ai_engine.ai_model_router import AIModelRouter


    from community.community_manager import CommunityManager


    from notifiers.unified_notifier import UnifiedNotifier


except ImportError:


    logger.warning("Could not import some platform modules. Some API features may be limited.")





# Authentication models


class UserLogin(BaseModel):


    email: EmailStr


    password: str





class UserRegistration(BaseModel):


    username: str


    email: EmailStr


    password: str





# Strategy models


class StrategySubscription(BaseModel):


    strategy_id: str


    


class StrategyBase(BaseModel):


    id: str


    name: str


    description: str


    type: str


    is_public: bool


    


class StrategyDetail(StrategyBase):


    performance: Dict[str, float]


    creation_date: str


    last_update: str


    signals: List[Dict[str, Any]]


    


# Portfolio models


class PortfolioCreate(BaseModel):


    name: str


    description: str


    initial_balance: float


    


class PortfolioBase(BaseModel):


    id: str


    name: str


    description: str


    


class PortfolioDetail(PortfolioBase):


    balance: float


    positions: List[Dict[str, Any]]


    performance: Dict[str, float]


    creation_date: str


    last_update: str





# API response models


class SuccessResponse(BaseModel):


    success: bool = True


    message: str


    data: Any = None


    


class ErrorResponse(BaseModel):


    success: bool = False


    message: str


    error_code: str = "error"





# Security scheme


security = HTTPBearer()





class WebAPI:


    """FastAPI web server for the WarMachine platform"""


    


    def __init__(self, config: Dict[str, Any]):


        """


        Initialize the Web API


        


        Args:


            config: Configuration dictionary


        """


        self.config = config


        self.web_config = config.get("web_api", {})


        self.thread = None


        self.running = False


        self._shutdown_event = threading.Event()


        


        # Server configuration


        self.host = self.web_config.get("host", "localhost")


        self.port = self.web_config.get("port", 8000)


        self.debug = self.web_config.get("debug", False)


        


        # Initialize FastAPI app


        self.app = FastAPI(


            title="WarMachine API",


            description="API for the WarMachine trading platform",


            version="1.0.0"


        )


        


        # Enable CORS


        self.app.add_middleware(


            CORSMiddleware,


            allow_origins=["*"],


            allow_credentials=True,


            allow_methods=["*"],


            allow_headers=["*"]


        )


        


        # Initialize platform modules


        self.community_manager = CommunityManager(config)


        self.notifier = UnifiedNotifier(config)


        self.ai_router = AIModelRouter(config)


        


        # Register routes


        self._register_routes()


        


        logger.info(f"Web API initialized on {self.host}:{self.port}")


        


    async def start(self):


        """Start the Web API in non-blocking mode"""


        if not self.thread:


            self.running = True


            self._shutdown_event.clear()


            


            self.thread = threading.Thread(


                target=self._run_server,


                daemon=True,


                name="WebAPIThread"


            )


            self.thread.start()


            logger.info("Web API started in background thread")


            return True


        return False


        


    async def shutdown(self):


        """Gracefully shutdown the Web API"""


        logger.info("Shutting down Web API...")


        self.running = False


        self._shutdown_event.set()


        


        if self.thread and self.thread.is_alive():


            # Wait for thread to finish


            self.thread.join(timeout=5.0)


            if self.thread.is_alive():


                logger.warning("Web API thread did not stop gracefully")


        


        logger.info("Web API shutdown complete")


        


    def _run_server(self):


        """Run the FastAPI server"""


        try:


            uvicorn.run(


                self.app,


                host=self.host,


                port=self.port,


                log_level="info" if self.debug else "warning"


            )


            except Exception as e:


            logger.error(f"Failed to start web server: {str(e)}")


            self.running = False


            


    async def is_running(self) -> bool:


        """Check if the API server is running"""


        return self.running and self.thread and self.thread.is_alive()


        


    async def get_status(self) -> Dict[str, Any]:


        """Get API server status"""


                return {


            "running": self.running,


            "thread_alive": self.thread and self.thread.is_alive(),


            "host": self.host,


            "port": self.port


        }


        


    def _register_routes(self):


        """Register API routes with FastAPI app"""


        # Health check endpoint (no authentication required)


        @self.app.get("/health")


        async def health_check():


            """Health check endpoint"""


                return {


                "status": "ok",


                "version": "1.0.0",


                "running": self.running


            }


            


        # System status endpoint


        @self.app.get("/api/status")


        async def system_status():


            """Get system status"""


                return {


                "status": "ok",


                "components": {


                    "web_api": await self.get_status(),


                    "web_dashboard": None,  # Will be populated by WarMachine


                    "market_data": None,    # Will be populated by WarMachine


                    "strategies": None,     # Will be populated by WarMachine


                    "ai": None,            # Will be populated by WarMachine


                    "notifiers": None      # Will be populated by WarMachine


                }


            }


            


        # Market data endpoints


        @self.app.get("/api/market-data/{symbol}")


        async def get_market_data(symbol: str):


            """Get market data for a symbol"""


            try:


                # This will be implemented by WarMachine


                return {"symbol": symbol, "data": None}


            except Exception as e:


                raise HTTPException(status_code=500, detail=str(e))


                


        # Strategy endpoints


        @self.app.get("/api/strategies")


        async def get_strategies():


            """Get list of strategies"""


            try:


                # This will be implemented by WarMachine


                return {"strategies": []}


            except Exception as e:


                raise HTTPException(status_code=500, detail=str(e))


                


        # AI analysis endpoints


        @self.app.post("/api/analyze")


        async def analyze_market(data: Dict[str, Any]):


            """Analyze market data"""


            try:


                # This will be implemented by WarMachine


                return {"analysis": None}


            except Exception as e:


                raise HTTPException(status_code=500, detail=str(e))


                


        # Notification endpoints


        @self.app.post("/api/notify")


        async def send_notification(data: Dict[str, Any]):


            """Send a notification"""


            try:


                # This will be implemented by WarMachine


                return {"status": "sent"}


            except Exception as e:


                raise HTTPException(status_code=500, detail=str(e))


            


    def run(self):


        """Run the web server"""


        try:


            uvicorn.run(


                self.app,


                host=self.host,


                port=self.port,


                log_level="info" if self.debug else "warning"


            )


        except Exception as e:


            logger.error(f"Failed to start web server: {str(e)}")


            


    def run_in_thread(self):


        """Run the web server in a thread (non-blocking)"""


        try:


            import threading


            


            thread = threading.Thread(


                target=self.run,


                daemon=True


            )


            thread.start()


            logger.info(f"Web API started in thread on {self.host}:{self.port}")


            return thread


            


        except Exception as e:


            logger.error(f"Failed to start web server in thread: {str(e)}")


            return None 