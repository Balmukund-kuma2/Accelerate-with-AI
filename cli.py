import os
import shutil
import subprocess
from pathlib import Path

# Import the 'run' function from each agent
from agents.profiler_agent import run_profiler
from agents.sttm_generator_agent import run_sttm_generator
from agents.bronze_agent import process_to_bronze
from agents.silver_agent import process_to_silver
from agents.gold_agent import process_to_gold
from agents.reporter_agent import run_reporter
from core.audit import log_action

def hitl_gate(layer_name: str, sttm_path: Path) -> bool:
    """
    Human-in-the-Loop (HITL) gate to allow review and approval.
    """
    log_action("Orchestrator", f"Waiting for human approval for {layer_name} layer.")
    print("\n" + "="*50)
    print(f" GATE: REVIEW {layer_name.upper()} TRANSFORMATION PLAN")
    print("="*50)
    print(f"The proposed transformation rules are located at:\n👉 {sttm_path}")
    
    while True:
        choice = input("Do you [y]es, approve | [e]dit the file | [n]o, abort? ").lower().strip()
        if choice == 'y':
            log_action("HITL", f"Approved {layer_name} STTM")
            return True
        elif choice == 'n':
            log_action("HITL", f"Aborted at {layer_name} STTM")
            print("❌ Pipeline run aborted by user.")
            return False
        elif choice == 'e':
            log_action("HITL", f"User is editing {layer_name} STTM")
            print("Opening the file in your default text editor. Save and close the editor to continue...")
            # Open file in default editor - platform dependent
            try:
                if os.name == 'nt': # Windows
                    os.startfile(sttm_path)
                elif os.name == 'posix': # macOS, Linux
                    subprocess.call(('open', sttm_path))
            except Exception as e:
                print(f"Could not open editor automatically: {e}. Please open it manually.")
            
            input("Press Enter after you have saved your changes to re-review...")
            # Loop back to re-evaluate the file
        else:
            print("Invalid input. Please choose 'y', 'n', or 'e'.")


def run_pipeline():
    """
    Executes the full agentic medallion pipeline from start to finish.
    """
    run_id = log_action("Orchestrator", "Starting new pipeline run")
    
    # --- Phase 1: Profiling and Bronze STTM ---
    run_profiler()
    run_sttm_generator()

    # --- HITL Gate 1: Bronze ---
    sttm_path = Path("data/bronze/sttm_rules.json")
    if not hitl_gate("Bronze", sttm_path):
        return

    # --- Phase 2: Bronze Execution ---
    process_to_bronze()

    # --- HITL Gate 2: Silver ---
    if not hitl_gate("Silver", sttm_path):
        return
        
    # --- Phase 3: Silver Execution ---
    process_to_silver()

    # --- HITL Gate 3: Gold ---
    if not hitl_gate("Gold", sttm_path):
        return

    # --- Phase 4: Gold Execution & Reporting ---
    process_to_gold()
    run_reporter()
    
    log_action("Orchestrator", "Pipeline run completed successfully.")
    print("\n🎉🎉🎉")
    print("PIPELINE RUN COMPLETED SUCCESSFULLY!")
    print("Check the `reports/` folder for your Executive Sales Report.")
    print("🎉🎉🎉\n")


if __name__ == "__main__":
    # Before running, ensure the raw data is in place
    landing_dir = Path("data/landing")
    if not any(landing_dir.glob("*.csv")):
        print("⚠️ No raw CSV files found in `data/landing/`.")
        print("Please add `sales_data.csv`, `products.csv`, and `stores.csv` to that folder before running.")
    else:
        run_pipeline()
