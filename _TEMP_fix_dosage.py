import re
p = 'core/dosage.py'
s = open(p, encoding='utf-8').read()
s = s.replace('import yaml\n\n', '')
s = s.replace('_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "agronomy.yaml"\n\n', '')
s = re.sub(r'\n    sd = float\(cfg\.get\("sample_depth_m", 0\.15\)\)\n    return bd \* sd \* 10  # = 1\.95\n?$', '', s)
open(p, 'w', encoding='utf-8').write(s)
print('done')
