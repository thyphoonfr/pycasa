import re

with open('docs/analysis/decomp_dir_scanner_ctor.c', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

strs = re.findall(r'"([^"]*)"', text)
print(f'Total strings: {len(strs)}')
for s in sorted(set(strs)):
    if len(s) > 2:
        print(' ', s)
