import os
import json
from pathlib import Path
from openai import OpenAI
from core.config import GITHUB_TOKEN, BRONZE_DIR
from core.audit import log_action, log_error
from core.state import update_step_status

# Configure client to use GitHub's free model hosting endpoints
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN
)

def generate_sttm_with_llm(profile_data: dict) -> dict:
    """Uses the LLM to design transformation rules for Bronze, Silver, and Gold layers."""
    
    prompt = f"""
    You are an expert Data Architect. Review this source data profile and generate a clean transformation plan for a Medallion pipeline (Bronze -> Silver -> Gold).
    
    Source Data Profile:
    {json.dumps(profile_data, indent=2)}

    Generate a single JSON object with the following structural rules:
    1. "bronze": Specify column-by-column renaming or basic type casting (e.g., convert floats to ints or string dates to datetimes).
    2. "silver": Specify data cleaning and quality rules (e.g., standardizing values, removing duplicates on primary keys, or default values for nulls).
    3. "gold": Design business-level aggregation rules. You should plan to join the datasets (sales, products, stores) to answer key business questions like "What are the total sales per store category?".

    Respond ONLY with a valid JSON block containing "bronze", "silver", and "gold" keys. Do not include markdown code block syntax (like ```json).
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional data engineering assistant that outputs raw JSON only."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o-mini", # Free tier model hosted on GitHub Models
            temperature=0.2
        )
        
        raw_content = response.choices[0].message.content.strip()
        # Clean up in case markdown block format was returned anyway
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            
        return json.loads(raw_content)
        
    except Exception as e:
        log_error("STTMGeneratorAgent", f"LLM STTM Generation failed: {str(e)}")
        raise e

def run_sttm_generator():
    """Reads the profiler summary and generates STTM files for the pipeline."""
    log_action("STTMGeneratorAgent", "Starting STTM generation process")
    
    profile_path = BRONZE_DIR / "data_profile_summary.json"
    if not profile_path.exists():
        log_error("STTMGeneratorAgent", f"Profile summary not found at {profile_path}. Please run profiler_agent.py first.")
        print("⚠️ Profile data missing. Make sure to run profiler_agent.py first.")
        return

    with open(profile_path, "r") as f:
        profile_data = json.load(f)

    print("🤖 Prompting AI to generate Source-to-Target mapping rules...")
    sttm_rules = generate_sttm_with_llm(profile_data)

    sttm_output_path = BRONZE_DIR / "sttm_rules.json"
    with open(sttm_output_path, "w") as f:
        json.dump(sttm_rules, f, indent=4)

    log_action("STTMGeneratorAgent", "Completed STTM Generation", f"Rules saved to {sttm_output_path}")
    update_step_status("sttm_generator", "completed", [str(sttm_output_path)])
    print(f"✅ STTM Generation complete! Rules successfully saved to {sttm_output_path}")

if __name__ == "__main__":
    run_sttm_generator()
