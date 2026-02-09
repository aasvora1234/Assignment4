from pathlib import Path
import pandas as pd
from datetime import datetime as dt

try:
    SILVER_PATH = Path("/opt/data/delta-lake/silver")
    GOLD_PATH = Path("/opt/data/delta-lake/gold")
   
    def get_latest_csv(directory):
        csv_files = list(Path(directory).glob("*.csv"))
        if not csv_files:
            return None
        return max(csv_files, key=lambda x: x.stat().st_mtime)
    
    shipments_file = get_latest_csv(SILVER_PATH / "shipments_scd2")
    df = pd.read_csv(shipments_file)
    summary = df.groupby('status').size().reset_index(name='count')
    summary['created_at'] = dt.now()
    
    output_dir = GOLD_PATH / "shipment_summary"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"summary_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    summary.to_csv(str(output_file), index=False)
    print("SUCCESS: Gold layer executed!")
    print(summary)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
