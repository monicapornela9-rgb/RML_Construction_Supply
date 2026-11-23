import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3488\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

pos = code.find("Delivery Slot")
if pos == -1:
    pos = code.find("Order Summary")
print(code[pos-100:pos+2500])
