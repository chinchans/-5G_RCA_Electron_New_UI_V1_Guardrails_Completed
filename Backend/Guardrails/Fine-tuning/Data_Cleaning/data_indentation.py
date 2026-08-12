import json

with open('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/sample.json','r')as f:
    data=json.load(f)
sample_data=[]
for item in data:
    sample_data.append(item)
with open('/home/tcs/genai_setups/5G_RCA_Electron_New_UI_V1/Backend/Guardrails/Fine-tuning/Datasets/sample_indented.json', 'w')as f:
    json.dump(sample_data,f,indent=2)