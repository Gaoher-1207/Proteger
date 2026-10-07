import io
import sys
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2] / "backend"))
from app.services.extractors import extract_content

def test_generated_sample_formats():
    base=Path(__file__).resolve().parents[2]/"sample_data"
    expected={"sample_document.pdf":"PDF","sample_stress_findings.pdf":"PDF","sample_document.docx":"DOCX","sample_workbook.xlsx":"XLSX","sample_presentation.pptx":"PPTX","sample_archive.zip":"ZIP","sample_image.png":"IMAGE_PNG","sample_code.py":"SOURCE_CODE","sample_data.json":"JSON","sample_data.csv":"CSV","sample_data.txt":"TEXT"}
    for filename,kind in expected.items():
        result=extract_content((base/filename).read_bytes(),filename)
        assert result.file_type==kind
        assert result.method
        assert result.status

def test_zip_slip_member_is_never_read():
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w") as archive:
        archive.writestr("../outside.txt","secret@example.com")
        archive.writestr("safe.txt","demo@example.com")
    result=extract_content(stream.getvalue(),"fixture.zip")
    assert "demo@example.com" in result.text
    assert "secret@example.com" not in result.text

def test_signature_overrides_misleading_extension():
    image=(Path(__file__).resolve().parents[2]/"sample_data"/"sample_image.png").read_bytes()
    result=extract_content(image,"looks_like_text.txt","text/plain")
    assert result.file_type=="IMAGE_PNG"
    assert result.status=="Image detected. OCR is not currently available."

def test_common_text_markup_yaml_and_logs():
    cases={"document.xml":("<root>contact demo@example.test</root>","XML","demo@example.test"),
           "page.html":("<html><body>contact demo@example.test</body></html>","HTML","demo@example.test"),
           "config.yaml":("contact: demo@example.test","YAML","demo@example.test"),
           "service.log":("INFO contact demo@example.test","LOG","demo@example.test"),
           "notes.md":("contact demo@example.test","MARKDOWN","demo@example.test")}
    for filename,(content,kind,expected) in cases.items():
        result=extract_content(content.encode(),filename)
        assert result.file_type==kind and expected in result.text and result.status=="Complete"
