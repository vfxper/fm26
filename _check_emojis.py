import re, sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'C:\Users\sin3\Documents\fm26\fm26\frontend\index.html', 'r', encoding='utf-8') as f:
    s = f.read()
emojis = ['\U0001f3e0','\u2708','\U0001f4c5','\u23f0','\u23f3','\U0001f91d','\U0001f310','\U0001f6aa','\U0001f3c1','\u2705','\U0001f4cb','\U0001f3c6','\U0001f4f0','\U0001f4ca','\U0001f4cc','\U0001f4be','\U0001f3ae','\U0001f50d','\U0001f4dd','\U0001f511','\U0001f3af','\U0001f7e8','\u23ed','\U0001f4b0','\U0001f504','\U0001f9e4','\u26bd','\U0001f945','\U0001f4e2','\U0001f4e3','\U0001f4c8','\U0001f4c9','\U0001f4bc','\U0001f5d3','\U0001f393','\U0001f49b','\u274c','\U0001f4f8','\U0001f4cb']
for e in emojis:
    c = s.count(e)
    if c > 0:
        print(f'{e}: {c}')
print('---')
# Also check arbitrary emojis
for m in re.finditer(r'[\U0001F000-\U0001FFFF\u2600-\u27BF]', s):
    line = s[:m.start()].count('\n') + 1
    print(f'line {line}: {m.group(0)!r}')
