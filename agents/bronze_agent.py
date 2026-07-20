import pandas as pd
from datetime import datetime
from core.config import LANDING_DIR, BRONZE_DIR
from core.audit import log_action, log_error
from core.state import update_step_status

def process_to_bronze():
    """Ingests raw CSV landing files, adds metadata, and saves as Parquet in the Bronze layer."""
    log_action("BronzeAgent", "Starting Bronze ingestion process")
    
    # Locate all raw CSV files in the landing directory
    csv_files = list(LANDING_DIR.glob("*.csv"))
    if not csv_files:
        log_error("BronzeAgent", "No CSV files found in data/landing/")
        print("⚠️ No raw CSV files found in data/landing/. Add sales_data.csv, products.csv, and stores.csv first.")
        return

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    ingested_files = []

    for file_path in csv_files:
        try:
            print(f"🥉 Ingesting {file_path.name} to Bronze...")
            
            # 1. Read the raw data
            df = pd.read_csv(file_path)
            
            # 2. Append standard audit metadata
            df["bronze_ingested_at"] = datetime.utcnow().isoformat()
            df["source_file_name"] = file_path.name
            
            # 3. Create output Parquet path
            parquet_filename = file_path.stem + ".parquet"
            output_path = BRONZE_DIR / parquet_filename
            
            # 4. Save to Bronze
            df.to_parquet(output_path, index=False)
            ingested_files.append(str(output_path))
            
            log_action("BronzeAgent", "Ingested file successfully", f"{file_path.name} -> {parquet_filename}")
            
        except Exception as e:
            log_error("BronzeAgent", f"Failed to ingest {file_path.name}: {str(e)}")
            raise e

    log_action("BronzeAgent", "Completed Bronze ingestion", f"Ingested {len(ingested_files)} files.")
    update_step_status("bronze", "completed", ingested_files)
    print(f"✅ Bronze layer ingestion complete! Files saved in: {BRONZE_DIR}")

if __name__ == "__main__":
    process_to_bronze()
