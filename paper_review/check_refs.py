import re

tex = open(r'C:\Users\27443\Desktop\andes-rl-kundur\paper_review\icems2026\main.tex', encoding='utf-8').read()
bib = open(r'C:\Users\27443\Desktop\andes-rl-kundur\paper_review\icems2026\references.bib', encoding='utf-8').read()

cited = set()
for grp in re.findall(r'\\cite\{([^}]+)\}', tex):
    cited.update(k.strip() for k in grp.split(','))
bibkeys = set(re.findall(r'@\w+\{([^,]+),', bib))

print('cited count:', len(cited))
print('missing from bib:', sorted(cited - bibkeys))
print('uncited in bib:', sorted(bibkeys - cited))

log = open(r'C:\Users\27443\Desktop\andes-rl-kundur\paper_review\icems2026\main.log', encoding='utf-8', errors='replace').read()
issues = [l.strip() for l in log.splitlines() if 'undefined' in l.lower() or 'multiply defined' in l.lower()]
print('undefined/multiply issues:', issues[:10])
print('overfull hbox count:', len([l for l in log.splitlines() if 'Overfull \\hbox' in l]))
print('output line:', [l for l in log.splitlines() if 'Output written' in l])
