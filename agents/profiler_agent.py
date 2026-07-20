import pandas as pd
import json
from pathlib import Path
from core.config import LANDING_DIR, BRONZE_DIR
from core.audit import log_action, log_error
from core.state import update_step_status

def profile_file(file_path: Path) -> dict:
    """Reads a CSV file and generates basic column statistics and quality metrics."""
    try:
        df = pd.read_csv(file_path)
        profile = {
            "file_name": file_path.name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": {}
        }
        
        for col in df.columns:
            missing_count = int(df[col].isnull().sum())
            missing_percentage = (missing_count / len(df)) * 100
            
            profile["columns"][col] = {
                "data_type": str(df[col].dtype),
                "null_count": missing_count,
                "null_percentage": round(missing_percentage, 2),
                "unique_values": int(df[col].nunique())
            }
            
        return profile
    except Exception as e:
        log_error("ProfilerAgent", f"Failed to profile {file_path.name}: {str(e)}")
        raise e

def run_profiler():
    """Profiles all raw CSV files inside the landing directory."""
    log_action("ProfilerAgent", "Starting data profiling process")
    
    # Ensure landing directory has files
    csv_files = list(LANDING_DIR.glob("*.csv"))
    if not csv_files:
        log_error("ProfilerAgent", "No CSV files found in data/landing/")
        print("⚠️ No raw CSV files found in data/landing/. Please add sales_data.csv, products.csv, and stores.csv.")
        return

    profiles = {}
    for file_path in csv_files:
        print(f"📊 Profiling {file_path.name}...")
        profile_data = profile_file(file_path)
        profiles[file_path.name] = profile_data
        log_action("ProfilerAgent", "Profiled file", file_path.name)

    # Save profiles as a JSON file in the bronze directory
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    profile_output_path = BRONZE_DIR / "data_profile_summary.json"
    
    with open(profile_output_path, "w") as f:
        json.dump(profiles, f, indent=4)

    log_action("ProfilerAgent", "Completed profiling", f"Summary saved to {profile_output_path}")
    update_step_status("profiler", "completed", [str(profile_output_path)])
    print(f"✅ Data profiling complete! Summary saved to {profile_output_path}")

if __name__ == "__main__":
    run_profiler()
