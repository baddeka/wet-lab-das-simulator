from docx import Document
from docx.oxml.ns import qn
d = Document('wet lab das calculations.docx')
print("=== structure check ===")
for i, p in enumerate(d.paragraphs):
    if not p.text.strip(): continue
    pPr = p._p.find(qn('w:pPr'))
    num = pPr.find(qn('w:numPr')) if pPr is not None else None
    nid = num.find(qn('w:numId')).get(qn('w:val')) if num is not None else '-'
    sz = [(r.font.size.pt if r.font.size else None, bool(r.font.bold)) for r in p.runs][:2]
    kind = 'HEAD' if sz and sz[0][0] == 12.0 else ('LIST%s' % nid if nid != '-' else 'body')
    if kind == 'HEAD' or p.text.startswith('Table ') or p.text.startswith('Lever ') or p.text.startswith('Bottom'):
        print('%-6s %s' % (kind, p.text[:96]))
print()
print("=== tables ===")
for i, t in enumerate(d.tables):
    print('Table element %d: %d rows x %d cols | header: %s' % (i, len(t.rows), len(t.columns), ' | '.join(c.text for c in t.rows[0].cells)))
print()
print("=== formatting fidelity ===")
heads = [p for p in d.paragraphs if p.runs and p.runs[0].font.size and p.runs[0].font.size.pt == 12.0]
bodies = [p for p in d.paragraphs if p.runs and p.runs[0].font.size and p.runs[0].font.size.pt == 11.0]
lists  = [p for p in d.paragraphs if p.style.name == 'List Paragraph']
print('12pt bold headings: %d | 11pt body runs: %d | List Paragraph items: %d' % (len(heads), len(bodies), len(lists)))
numids = set()
for p in lists:
    pPr = p._p.find(qn('w:pPr')); num = pPr.find(qn('w:numPr'))
    numids.add(num.find(qn('w:numId')).get(qn('w:val')))
print('numbering ids in use:', sorted(numids), '(2 = bullets, 3 = numbered, as in the original)')
