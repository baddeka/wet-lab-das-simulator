from docx import Document
from docx.oxml.ns import qn
d = Document(r'C:\Users\mi\Downloads\wet lab das calculations.docx')
for i, p in enumerate(d.paragraphs):
    pPr = p._p.find(qn('w:pPr'))
    bits = []
    if pPr is not None:
        num = pPr.find(qn('w:numPr'))
        if num is not None:
            ilvl = num.find(qn('w:ilvl')); nid = num.find(qn('w:numId'))
            bits.append('numId=%s ilvl=%s' % (nid.get(qn('w:val')) if nid is not None else '?',
                                              ilvl.get(qn('w:val')) if ilvl is not None else '?'))
        ind = pPr.find(qn('w:ind'))
        if ind is not None: bits.append('ind=%s' % dict(ind.attrib).__str__()[:60])
        spc = pPr.find(qn('w:spacing'))
        if spc is not None: bits.append('spc=%s' % dict(spc.attrib).__str__()[:60])
    sizes = [(r.font.size.pt if r.font.size else None, r.font.bold) for r in p.runs][:3]
    print('%2d [%-14s] %-38s runs=%s | %s' % (i, p.style.name, (p.text[:36] or '(empty)'), sizes, ' '.join(bits)))
print()
print('--- body element order (paragraphs vs tables) ---')
from docx.table import Table
from docx.text.paragraph import Paragraph
body = d.element.body
for i, child in enumerate(body):
    tag = child.tag.split('}')[1]
    if tag == 'p':
        print(i, 'P  ', Paragraph(child, d).text[:60])
    elif tag == 'tbl':
        print(i, 'TBL', '<table>')
    else:
        print(i, tag)
