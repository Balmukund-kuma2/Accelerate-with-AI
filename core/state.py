import json
from pathlib import Path
from core.config import BASE_DIR

STATE_FILE = BASE_DIR / "core" / "pipeline_state.json"

def load_state() -> dict:
    """Loads the current pipeline execution state."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "current_step": "initialized",
        "completed_steps": [],
        "files": {}
    }

def save_state(state: dict):
    """Saves the pipeline execution state to keep track of progress."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def update_step_status(step_name: str, status: str, file_paths: list = None):
    """Updates status and output file locations for a specific pipeline step."""
    state = load_state()
    state["current_step"] = step_name
    if status == "completed" and step_name not in state["completed_steps"]:
        state["completed_steps"].append(step_name)
    if file_paths:
        state["files"][step_name] = file_paths
    save_state(state)
    print(f"🔄 State Updated: {step_name} -> {status}")
