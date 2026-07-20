import pandas as pd
from datetime import datetime
from core.config import SILVER_DIR, GOLD_DIR
from core.audit import log_action, log_error
from core.state import update_step_status

def process_to_gold():
    """Reads Silver data, joins tables, generates business aggregates, and saves to the Gold layer."""
    log_action("GoldAgent", "Starting Gold aggregation process")
    
    # Define input paths
    sales_path = SILVER_DIR / "sales_data.parquet"
    products_path = SILVER_DIR / "products.parquet"
    stores_path = SILVER_DIR / "stores.parquet"

    if not (sales_path.exists() and products_path.exists() and stores_path.exists()):
        log_error("GoldAgent", "One or more Silver files are missing.")
        print("⚠️ Missing Silver files. Please ensure silver_agent.py has completed successfully.")
        return

    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    try:
        print("🥇 Loading and joining Silver data tables...")
        df_sales = pd.read_parquet(sales_path)
        df_products = pd.read_parquet(products_path)
        df_stores = pd.read_parquet(stores_path)

        # 2. Perform the Joins
        df_merged = pd.merge(df_sales, df_products, on="product_id", how="inner")
        df_merged = pd.merge(df_merged, df_stores, on="store_id", how="inner")
        
        # DEBUG: Print columns so we can see what the AI named them if it fails again
        print(f"🔍 DEBUG - Available Columns: {list(df_merged.columns)}")

        log_action("GoldAgent", "Successfully joined Sales, Products, and Stores tables")

        # 3. Feature Engineering: Ultra-resilient dynamic column detection
        cols = [c.lower() for c in df_merged.columns]
        
        price_col = next((c for c in df_merged.columns if any(k in c.lower() for k in ['price', 'cost', 'amount'])), 'price')
        qty_col = next((c for c in df_merged.columns if any(k in c.lower() for k in ['quant', 'qty', 'count', 'units'])), 'quantity')
        category_col = next((c for c in df_merged.columns if any(k in c.lower() for k in ['categor', 'department', 'group', 'line'])), 'category')
        trans_id_col = next((c for c in df_merged.columns if any(k in c.lower() for k in ['trans', 'order', 'invoice'])), 'transaction_id')
        
        # Expanded search for the store type/format
        store_type_col = next((c for c in df_merged.columns if any(k in c.lower() for k in ['type', 'format', 'tier', 'size', 'classification'])), None)
        
        # Bulletproof fallback for store type
        if not store_type_col:
            store_type_col = next((c for c in df_merged.columns if 'name' in c.lower() or 'store' in c.lower()), 'store_id')

        # Ensure price and quantity are treated as numeric values
        df_merged[price_col] = pd.to_numeric(df_merged[price_col], errors="coerce").fillna(0.0)
        df_merged[qty_col] = pd.to_numeric(df_merged[qty_col], errors="coerce").fillna(0)
        df_merged["revenue"] = df_merged[price_col] * df_merged[qty_col]

        # 4. Save the Master joined table
        master_output_path = GOLD_DIR / "gold_master_sales_analytics.parquet"
        df_merged.to_parquet(master_output_path, index=False)

        # 5. Create structured aggregation
        print("🥇 Generating performance aggregations...")
        df_summary = df_merged.groupby([category_col, store_type_col]).agg(
            total_revenue=("revenue", "sum"),
            total_quantity_sold=(qty_col, "sum"),
            transaction_count=(trans_id_col, "count")
        ).reset_index()

        # Standardize names back so the Reporter Agent can build the charts perfectly
        df_summary.rename(columns={category_col: "category", store_type_col: "store_type"}, inplace=True)
        df_summary = df_summary.sort_values(by="total_revenue", ascending=False)
        df_summary["gold_aggregated_at"] = datetime.utcnow().isoformat()

        # Save the aggregated table
        summary_output_path = GOLD_DIR / "gold_sales_summary.parquet"
        df_summary.to_parquet(summary_output_path, index=False)
        
        output_files = [str(master_output_path), str(summary_output_path)]
        update_step_status("gold", "completed", output_files)
        print(f"✅ Gold layer aggregation complete! Datasets saved in: {GOLD_DIR}")

    except Exception as e:
        log_error("GoldAgent", f"Failed to process and aggregate Gold data: {str(e)}")
        raise e

if __name__ == "__main__":
    process_to_gold()
