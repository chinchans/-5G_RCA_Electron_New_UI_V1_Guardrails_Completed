import random
import json
import pandas as pd

df_telecom = pd.read_json('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/CLEAN_NOTEBOOKLM_848_TELECOM_WORKBENCH_PROMPTS.json')
df_prompt_injection = pd.read_json('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/CLEAN_NOTEBOOKLM_1000_PROMPT_INJECTION_PROMPTS.json')
df_out_of_scope = pd.read_json('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/CLEAN_NOTEBOOKLM_1600_OUT_OF_SCOPE_PROMPTS.json')

all_data = pd.concat([df_telecom, df_prompt_injection, df_out_of_scope])
print(f"Total data points : {len(all_data)}")

print(f"\nCategory distribution :")
print(all_data["tier"].value_counts())
print(all_data["category"].value_counts())
print(all_data["attack_type"].value_counts())

all_data = all_data.sample(frac=1, random_state=42).reset_index(drop=True)

with open('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/CLEAN_NOTEBOOKLM_3370_MERGED_PROMPTS.json', 'w') as f:
    all_data.to_json(f, indent=2)

print(f"Merged data saved to CLEAN_NOTEBOOKLM_3370_MERGED_PROMPTS.json")