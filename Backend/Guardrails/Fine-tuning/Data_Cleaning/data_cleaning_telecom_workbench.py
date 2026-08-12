import json 
from collections import Counter 
import pandas as pd

with open('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/NOTEBOOKLM_1000_TELECOM_WORKBENCH_PROMPTS.json', 'r') as f:
    data = json.load(f)

print(f"Total number of data points: {len(data)}")

cleaned_data = []

for item in data:
    if(
        "text" in item 
        and "label" in item 
        and item["text"].strip() !="" 
        and item["label"].strip() != ""
    ):
        cleaned_data.append(item)

print(f"Data points after cleaning: {len(cleaned_data)}")

unique_data = []
seen = set()

#duplicate_count = 0
for item in cleaned_data:
    key = (
        item["text"].lower().strip(),
        item["label"].lower().strip()
    )

    if key not in seen:
        unique_data.append(item)
        seen.add(key)
    #else:
       # duplicate_count += 1
       # print(f"{duplicate_count} Duplicate found: {item['text']}")
    
print(f"Data points after removing duplicates: {len(unique_data)}")

labels = [
    item["tier"] for item in unique_data
]
print(f"\nCategory distribution :")
labels_count = Counter(labels)

for label, count in labels_count.items():
    print(f"{label}: {count}")

print(f"Total data points : {len(unique_data)}")

"""
with open('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/clean_notebookLm_848_TELECOM_WORKBENCH_PROMPTS.json', 'w') as f:
    json.dump(unique_data, f, indent=4)

print("Data cleaning is done and it's saved to clean_notebookLm_848_TELECOM_WORKBENCH_PROMPTS.json")


with open('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/CLEAN_NOTEBOOKLM_1000_TELECOM_WORKBENCH_PROMPTS_cleaned.json', 'w') as f:
    json.dump(unique_data, f, indent=2)

print("Data cleaning completed and saved to notebookLm_1000_TELECOM_WORKBENCH_PROMPTS_cleaned.json")"""

df_telecom = pd.DataFrame(unique_data)

if "tier" in df_telecom.columns:
    df_telecom["tier"] = df_telecom["tier"].replace({"tier_2_natural_phrasing": "tier_2_natural_slang"})


print(f"\nCategory distribution :")
print(df_telecom["tier"].value_counts())

df_telecom.to_json('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/CLEAN_NOTEBOOKLM_848_TELECOM_WORKBENCH_PROMPTS.json', indent=2)
print(f"Total data points : {len(unique_data)}")