import pandas as pd
import json
import base64
from pathlib import Path
from openai import OpenAI
import matplotlib.pyplot as plt
from datetime import datetime
from core.config import GITHUB_TOKEN, GOLD_DIR, REPORTS_DIR
from core.audit import log_action, log_error
from core.state import update_step_status

# Configure client to use GitHub's free model hosting endpoints
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN
)

def generate_chart(df: pd.DataFrame) -> str:
    """Generates a sales performance chart and returns it as a Base64 encoded string."""
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # Pivot data for grouped bar chart: Store Type vs Category
    pivot_df = df.pivot(index='category', columns='store_type', values='total_revenue').fillna(0)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    pivot_df.plot(kind='bar', ax=ax, width=0.8)
    
    plt.title("Revenue by Product Category and Store Type", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Product Category", fontsize=11, labelpad=10)
    plt.ylabel("Total Revenue ($)", fontsize=11, labelpad=10)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save the plot to a temporary path, encode it to Base64, then clean up
    temp_chart_path = REPORTS_DIR / "temp_sales_chart.png"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(temp_chart_path, dpi=150)
    plt.close()
    
    with open(temp_chart_path, "rb") as f:
        encoded_image = base64.b64encode(f.read()).decode('utf-8')
        
    temp_chart_path.unlink() # Delete temporary chart image
    return encoded_image

def generate_insights_with_llm(data_summary: list) -> str:
    """Uses LLM to write an executive summary and business recommendation based on Gold metrics."""
    prompt = f"""
    You are an expert Business Intelligence Analyst. Review these sales performance metrics:
    
    {json.dumps(data_summary, indent=2)}

    Write an executive report containing:
    1. A bold, 1-paragraph summary highlighting the top performing category and store-type combination.
    2. 3 bulleted key insights regarding sales distribution, underperforming combinations, or potential efficiency improvements.
    3. 2 action-oriented business recommendations for next quarter based strictly on this data.

    Output your entire response formatted in beautiful HTML (use headings, paragraphs, lists, and bold text). 
    Do NOT include any external HTML, HEAD, or BODY tags. Only output the nested content tags (e.g., <h2>, <p>, <ul>, <li>).
    """
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional retail consultant that formats outputs in clean HTML tags only."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o-mini",
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log_error("ReporterAgent", f"LLM Insights generation failed: {str(e)}")
        raise e

def create_html_report(insights_html: str, chart_base64: str, summary_df: pd.DataFrame):
    """Combines LLM insights, Base64 charts, and standard tables into a styled HTML document."""
    # Convert dataframe summary into an HTML table with Bootstrap classes
    table_html = summary_df.to_html(index=False, classes="table table-striped table-hover", float_format=lambda x: f"${x:,.2f}" if isinstance(x, (int, float)) else str(x))

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sales Analytics & Intelligence Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .card {{ border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px; }}
            .card-header {{ background-color: #4a5568; color: white; font-weight: bold; }}
            .dashboard-title {{ color: #2d3748; font-weight: 800; margin-top: 30px; margin-bottom: 5px; }}
            .meta-text {{ color: #718096; font-size: 0.9rem; margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="dashboard-title">⚡ Intent-Driven Sales Analytics Dashboard</h1>
            <p class="meta-text">Pipeline Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Medallion Gold Layer Report</p>
            
            <div class="row">
                <!-- AI Insights Card -->
                <div class="col-lg-7">
                    <div class="card">
                        <div class="card-header">🧠 AI-Generated Insights & Recommendations</div>
                        <div class="card-body">
                            {insights_html}
                        </div>
                    </div>
                </div>
                
                <!-- Performance Chart Card -->
                <div class="col-lg-5">
                    <div class="card">
                        <div class="card-header">📊 Visual Revenue Breakdown</div>
                        <div class="card-body text-center">
                            <img src="data:image/png;base64,{chart_base64}" class="img-fluid rounded" alt="Sales Performance Chart">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Detailed Metrics Table Card -->
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">📋 Summary Performance Metrics</div>
                        <div class="card-body">
                            <div class="table-responsive">
                                {table_html}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    report_path = REPORTS_DIR / "executive_sales_report.html"
    
    # -------------------------------------------------------------
    # THIS IS THE FIX: Added encoding="utf-8" to handle the emojis!
    # -------------------------------------------------------------
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    return report_path

def run_reporter():
    """Generates the performance chart, LLM insights, and compiles the final HTML dashboard report."""
    log_action("ReporterAgent", "Starting reporting process")
    
    gold_summary_path = GOLD_DIR / "gold_sales_summary.parquet"
    if not gold_summary_path.exists():
        log_error("ReporterAgent", f"Gold summary dataset not found at {gold_summary_path}. Run gold_agent.py first.")
        print("⚠️ Missing gold summary. Run gold_agent.py first.")
        return

    # Load Gold summary data
    print("📊 Loading summary records from Gold layer...")
    df_summary = pd.read_parquet(gold_summary_path)

    # Convert dataframe into JSON dictionary format for the LLM
    data_list = df_summary.to_dict(orient="records")

    # Generate visual chart
    print("📊 Generating matplotlib performance chart...")
    chart_base64 = generate_chart(df_summary)

    # Generate LLM analysis content
    print("🤖 Consulting AI for analysis & recommendations...")
    insights_html = generate_insights_with_llm(data_list)

    # Build final report file
    print("📋 Compiling final executive dashboard...")
    report_output_path = create_html_report(insights_html, chart_base64, df_summary)

    log_action("ReporterAgent", "Successfully generated HTML dashboard report", str(report_output_path))
    update_step_status("reporter", "completed", [str(report_output_path)])
    print(f"✅ Executive dashboard compiled successfully! Report generated at:\n👉 {report_output_path}")

if __name__ == "__main__":
    run_reporter()
