import win32com.client, os
d = os.path.dirname(os.path.abspath(__file__))
docx = os.path.join(d, 'wet lab das calculations.docx')
pdf  = os.path.join(d, 'wet lab das calculations.pdf')
w = win32com.client.DispatchEx('Word.Application')
w.Visible = False
doc = w.Documents.Open(docx, ReadOnly=True)
doc.SaveAs(pdf, FileFormat=17)
print('pages =', doc.ComputeStatistics(2), ' words =', doc.ComputeStatistics(0))
doc.Close(False); w.Quit()
print('pdf bytes =', os.path.getsize(pdf))
