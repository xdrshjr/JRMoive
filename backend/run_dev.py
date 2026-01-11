"""Development server runner script"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from backend.config import settings


if __name__ == "__main__":
    print("=" * 60)
    print(f"Starting {settings.api_title} (Development Mode)")
    print(f"Server: http://{settings.host}:{settings.port}")
    print(f"Docs: http://{settings.host}:{settings.port}/docs")
    print(f"ReDoc: http://{settings.host}:{settings.port}/redoc")
    print("=" * 60)
    print()
    
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
        access_log=True
    )

