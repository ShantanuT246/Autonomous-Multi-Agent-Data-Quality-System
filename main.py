import os
import sys
import uvicorn

# Ensure the project root directory is in sys.path
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

if __name__ == "__main__":
    print(f"Starting Autonomous Multi-Agent Data Quality System on http://localhost:8000 ...")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
