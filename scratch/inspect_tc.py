import json

with open(r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        step_idx = data.get('step_index')
        if step_idx == 3178:
            print("Step 3178 tool_calls:")
            print(json.dumps(data.get('tool_calls'), indent=2))
            break
