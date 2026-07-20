import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Load environment variables from the .env file
load_dotenv()

# 2. Define the Base Directory (Root of the project)
BASE_DIR = Path(__file__).resolve().parent.parent

# 3. Define standard data and report paths
DATA_DIR = BASE_DIR / "data"
LANDING_DIR = DATA_DIR / "landing"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
REPORTS_DIR = BASE_DIR / "reports"
LOG_DIR = BASE_DIR / "logs"

# 4. Fetch the GitHub Token for LLM usage
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Simple validation to make sure the token loaded correctly
if not GITHUB_TOKEN:
    print("⚠️ Warning: GITHUB_TOKEN not found in environment. Please check your .env file.")


