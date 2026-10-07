"""Create fake document fixtures using only Python's standard library."""
from pathlib import Path
import base64
import zipfile

OUT=Path(__file__).parent
def put_zip(filename, files):
    with zipfile.ZipFile(OUT/filename,"w",zipfile.ZIP_DEFLATED) as zf:
        for name,content in files.items(): zf.writestr(name,content)

put_zip("sample_document.docx", {
 "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
 "word/document.xml": '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>FAKE / DEMONSTRATION DATA ONLY test@example.com API_KEY=fake_demo_key_123456789</w:t></w:r></w:p></w:body></w:document>'})
put_zip("sample_workbook.xlsx", {
 "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>',
 "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Demo" sheetId="1"/></sheets></workbook>',
 "xl/worksheets/sheet1.xml": '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>FAKE / DEMONSTRATION DATA ONLY test@example.com</t></is></c></row></sheetData></worksheet>'})
put_zip("sample_presentation.pptx", {
 "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>',
 "ppt/slides/slide1.xml": '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>FAKE / DEMONSTRATION DATA ONLY test@example.com</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'})
put_zip("sample_archive.zip", {"readme.txt":"FAKE / DEMONSTRATION DATA ONLY\nContact archive.demo@example.test\n", "nested/payload.csv":"id,email\n1,zip.demo@example.test\n"})
(OUT/"sample_image.png").write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="))
def make_pdf(filename, text):
    objects=[b"<< /Type /Catalog /Pages 2 0 R >>",b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    escaped=text.replace("\\","\\\\").replace("(","\\(").replace(")","\\)").encode()
    stream=b"BT /F1 8 Tf 10 80 Td ("+escaped+b") Tj ET"
    objects.append(b"<< /Length "+str(len(stream)).encode()+b" >>\nstream\n"+stream+b"\nendstream")
    pdf=bytearray(b"%PDF-1.4\n"); offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(pdf)); pdf.extend(f"{i} 0 obj\n".encode()+obj+b"\nendobj\n")
    xref=len(pdf); pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    (OUT/filename).write_bytes(pdf)

make_pdf("sample_document.pdf","FAKE DEMO test@example.com")
make_pdf("sample_stress_findings.pdf"," ".join(f"person{i}@example.test" for i in range(2500)))
print("Created fake PDF, DOCX, XLSX, PPTX, ZIP and PNG fixtures (plus PDF pagination stress fixture).")
