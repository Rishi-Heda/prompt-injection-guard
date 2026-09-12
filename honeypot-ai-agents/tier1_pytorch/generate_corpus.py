import json
import random
import numpy as np
import os

# Tool ID Mapping
PAD = 0
READ_FILE = 1
SUMMARIZE = 2
QUERY_DB = 3
SEND_EMAIL = 4
SEARCH_WEB = 5
CALCULATE_MATH = 6
WRITE_FILE = 7

def generate_complex_trajectories(num_samples=25000, window_size=5):
    trajectories = []
    
    tasks = [
        "fact_check", "financial_audit", "news_agg", "email_triage", 
        "daily_brief", "budget_plan", "log_analysis", "data_migration", 
        "customer_support", "competitor_analysis", "inventory_check",
        "basic_research", "data_analysis", "report_gen", "health_check"
    ]
    
    for _ in range(num_samples):
        task_type = random.choice(tasks)
        seq = []
        
        if task_type == "fact_check":
            seq.append(READ_FILE)
            for _ in range(random.randint(1, 3)): seq.append(SEARCH_WEB)
            seq.append(SUMMARIZE)
            
        elif task_type == "financial_audit":
            seq.append(QUERY_DB)
            for _ in range(random.randint(2, 4)): seq.append(CALCULATE_MATH)
            seq.append(WRITE_FILE)
            
        elif task_type == "news_agg":
            for _ in range(random.randint(2, 4)): seq.append(SEARCH_WEB)
            seq.extend([SUMMARIZE, WRITE_FILE])
            
        elif task_type == "email_triage":
            seq.extend([READ_FILE, SUMMARIZE, QUERY_DB, SEND_EMAIL])
            
        elif task_type == "daily_brief":
            seq.extend([SEARCH_WEB, QUERY_DB, SUMMARIZE, SEND_EMAIL])
            
        elif task_type == "budget_plan":
            seq.append(READ_FILE)
            for _ in range(random.randint(1, 3)): seq.append(CALCULATE_MATH)
            seq.append(WRITE_FILE)
            
        elif task_type == "log_analysis":
            for _ in range(random.randint(2, 5)): seq.append(READ_FILE)
            seq.extend([SUMMARIZE, WRITE_FILE])
            
        elif task_type == "data_migration":
            for _ in range(random.randint(1, 3)): seq.append(QUERY_DB)
            for _ in range(random.randint(1, 3)): seq.append(WRITE_FILE)
            
        elif task_type == "customer_support":
            seq.extend([READ_FILE, SEARCH_WEB, SUMMARIZE, SEND_EMAIL])
            
        elif task_type == "competitor_analysis":
            for _ in range(random.randint(1, 3)): seq.append(SEARCH_WEB)
            seq.extend([CALCULATE_MATH, WRITE_FILE])
            
        elif task_type == "inventory_check":
            seq.extend([QUERY_DB, CALCULATE_MATH, WRITE_FILE, SEND_EMAIL])
            
        elif task_type == "basic_research":
            for _ in range(random.randint(1, 3)):
                seq.extend([SEARCH_WEB, READ_FILE])
            seq.extend([SUMMARIZE, WRITE_FILE])
            
        elif task_type == "data_analysis":
            seq.extend([QUERY_DB, CALCULATE_MATH, SUMMARIZE, WRITE_FILE])
            
        elif task_type == "report_gen":
            seq.extend([READ_FILE, SUMMARIZE, SEND_EMAIL])
            
        elif task_type == "health_check":
            seq.extend([QUERY_DB, SUMMARIZE, WRITE_FILE])
            
        # Convert the generated sequence into sliding windows of size N
        for i in range(1, len(seq) + 1):
            window = seq[:i]
            padded = [PAD] * (window_size - len(window)) + window
            trajectories.append(padded[-window_size:])
            
     # Deduplicate and shuffle
    unique_trajectories = np.unique(trajectories, axis=0)
    np.random.shuffle(unique_trajectories)

    # Held-out split: calibrate on data the model never trained on
    split_idx = int(len(unique_trajectories) * 0.85)
    train_set = unique_trajectories[:split_idx]
    val_set = unique_trajectories[split_idx:]

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data", "traces")
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(os.path.join(DATA_DIR, "clean_windows_train.json"), "w") as f:
        json.dump(train_set.tolist(), f)
    with open(os.path.join(DATA_DIR, "clean_windows_val.json"), "w") as f:
        json.dump(val_set.tolist(), f)

    print(f"Train windows: {len(train_set)} | Val windows (held out): {len(val_set)}")
if __name__ == "__main__":
    generate_complex_trajectories()