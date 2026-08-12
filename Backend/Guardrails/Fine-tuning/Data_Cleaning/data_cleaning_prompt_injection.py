import json
from collections import Counter

with open('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/NOTEBOOKLM_1000_PROMPT_INJECTION_PROMPTS.json', 'r')as f:
    data=json.load(f)

print(f"Total number of data points : {len(data)}")
cleaned_data = []

for item in data:
    if(
        "text" in item 
        and "label" in item
        and item["text"].strip() != ""
        and item["label"].strip() != ""
    ):
        cleaned_data.append(item)

print(f"Data points after removing empty sets : {len(cleaned_data)}")

unique_data = []
seen = set()

for item in cleaned_data:
    key=(item["text"].strip(),item["label"].strip())

    if key not in seen:
        unique_data.append(item)
        seen.add(key)

print(f"Data points after removing duplicates : {len(unique_data)}")

with open('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/CLEAN_NOTEBOOKLM_1000_PROMPT_INJECTION_PROMPTS.json', 'w') as f:
    json.dump(unique_data, f, indent = 2)
print(f"Unique data saved into : CLEAN_NOTEBOOKLM_1000_PROMPT_INJECTION_PROMPTS")

print("\nCategory distribution")
labels = [
    item["attack_type"] for item in unique_data
]

labels_count = Counter(labels)

for label, count in labels_count.items():
    print(f"{label} : {count}")

print(f"Total data points : {len(unique_data)}")
