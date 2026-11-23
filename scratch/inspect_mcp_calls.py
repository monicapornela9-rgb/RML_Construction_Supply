import json

# Check transcript around step 3170-3210
with open(r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        step_idx = data.get('step_index')
        if step_idx in [3174, 3175, 3176, 3177, 3178, 3179, 3195, 3196, 3197]:
            print(f"Step {step_idx}: type={data.get('type')}, source={data.get('source')}")
            tool_calls = data.get('tool_calls', [])
            if tool_calls:
                for tc in tool_calls:
                    print(f"   Tool: {tc.get('name')}, args keys={list(tc.get('arguments', {}).keys())}")
                    if tc.get('name') == 'call_mcp_tool':
                        print(f"      Server: {tc.get('arguments', {}).get('ServerName')}, Tool: {tc.get('arguments', {}).get('ToolName')}")
                        print(f"      Args: {tc.get('arguments', {}).get('Arguments')}")
