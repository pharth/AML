import os
import json
from mongo_handler import MongoHandler  # Make sure this is your class file
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables if needed
load_dotenv()

# Configuration
MONGO_URI: str = "mongodb+srv://pkhhanchate:pkh123@cluster0.zthr0kd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
REPORTS_DIR = "reports"

def save_sar_reports():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    mongo = MongoHandler(MONGO_URI)
    reports = mongo.get_all_sar_reports()
    
    print(f"📦 Found {len(reports)} SAR reports. Saving to '{REPORTS_DIR}'...")

    def custom_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)  # handles ObjectId and others

    for report in reports:
        report_id = str(report.get("_id"))
        filepath = os.path.join(REPORTS_DIR, f"{report_id}.json")
        report["_id"] = report_id  # ensure _id is string

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, default=custom_serializer)

    mongo.close()
    print(f"✅ All SAR reports saved in '{REPORTS_DIR}'.")


if __name__ == "__main__":
    save_sar_reports()
