import json

with open(r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        step_idx = data.get('step_index')
        if step_idx in [3174, 3178, 3196]:
            print(f"Step {step_idx}:")
            tool_calls = data.get('tool_calls', [])
            for tc in tool_calls:
                print(f"  Tool: {tc.get('name')}")
                print(f"  Args: {json.dumps(tc.get('arguments'), indent=2)}")
