import xml.etree.ElementTree as ET
import re

# Read step 3179 output (FINAL DRAFT UI/UX)
path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3179\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Let's find top-level frames directly under the root or canvas
# Typically, top level frames have level 1 indentation or are direct children of the page
lines = content.split('\n')
print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines[:100]):
    print(line)
    if i > 50:
        break
