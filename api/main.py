# api/main.py
import sys
import os

# Point Python to your backend folder
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app # This imports your 'app = FastAPI()' from backend/main.py