from .state import Agent4State
from .service import agent4_service

# Import router directly - let errors propagate so we can fix them
from .router import agent4_router

# Lazy imports for graph to avoid circular import issues
def get_app():
    from .graph import app
    return app

def get_run_agent4():
    from .graph import run_agent4
    return run_agent4

def get_router():
    return agent4_router

from .schemas import (
    GenerateResumeRequest,
    GenerateResumeResponse,
    AnalyzeRejectionRequest,
    AnalyzeRejectionResponse,
    GenerateApplicationResponsesRequest,
    GenerateApplicationResponsesResponse,
    ApplicationResponses
)

__all__ = [
    # Graph
    "get_app",
    "get_run_agent4",
    "Agent4State",
    # Service
    "agent4_service",
    # Router
    "agent4_router",
    "get_router",
    # Schemas
    "GenerateResumeRequest",
    "GenerateResumeResponse",
    "AnalyzeRejectionRequest",
    "AnalyzeRejectionResponse",
    "GenerateApplicationResponsesRequest",
    "GenerateApplicationResponsesResponse",
    "ApplicationResponses",
]
