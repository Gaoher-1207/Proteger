"""In-memory, non-executing content extractors with conservative resource limits."""
from html.parser import HTMLParser
from pathlib import PurePosixPath
import io
import re
import zipfile
from xml.etree import ElementTree
from app.config import MAX_ARCHIVE_BYTES, MAX_ARCHIVE_MEMBER_BYTES, MAX_ARCHIVE_ENTRIES, MAX_ARCHIVE_DEPTH
from app.services.file_type_detector import detect_file_type, safe_filename

class _HTMLText(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self, data): self.parts.append(data)

def _clean_markup(text, kind):
    if kind == "HTML":
        parser=_HTMLText()
        try: parser.feed(text); return "\n".join(parser.parts)
        except Exception: pass
    if kind == "XML":
        try: return "\n".join(ElementTree.fromstring(text).itertext())
        except (ElementTree.ParseError, ValueError): pass
    return text

def _decode_text(data):
    if b"\x00" in data: return None
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text=data.decode(encoding)
            if sum(ch.isprintable() or ch in "\r\n\t" for ch in text) / max(1,len(text)) >= .88: return text
        except (UnicodeDecodeError, UnicodeError): continue
    return None

def _strings(data):
    # Preserve printable ASCII/Latin-1 runs only; binary bytes are never interpreted as code.
    return "\n".join(x.decode("latin-1") for x in re.findall(rb"[\x20-\x7e]{4,}", data))

def _safe_zip(zf):
    infos=zf.infolist()
    if len(infos)>MAX_ARCHIVE_ENTRIES: raise ValueError("Archive entry count exceeds the safety limit")
    total=0
    for info in infos:
        path=PurePosixPath(info.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or info.filename.startswith(("/", "\\")) or re.match(r"^[a-zA-Z]:",info.filename.replace("\\","/")):
            continue
        # Ignore Unix symbolic links. No entries are written to disk in this extractor.
        mode=(info.external_attr >> 16) & 0o170000
        if mode == 0o120000: continue
        total += info.file_size
        if info.file_size > MAX_ARCHIVE_MEMBER_BYTES or total > MAX_ARCHIVE_BYTES:
            raise ValueError("Archive uncompressed size exceeds the safety limit")
    return [i for i in infos if not i.is_dir() and not PurePosixPath(i.filename.replace("\\","/")).is_absolute() and ".." not in PurePosixPath(i.filename.replace("\\","/")).parts and not re.match(r"^[a-zA-Z]:",i.filename.replace("\\","/")) and ((i.external_attr >> 16) & 0o170000) != 0o120000]

def _read_member(zf, info):
    with zf.open(info) as member:
        data=member.read(MAX_ARCHIVE_MEMBER_BYTES+1)
    if len(data)>MAX_ARCHIVE_MEMBER_BYTES: raise ValueError("Archive member exceeds the safety limit")
    return data

def _office_text(data, kind):
    xlsx_bounds={}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            _safe_zip(zf)  # validate archive before passing it to a document library
            if kind=="XLSX":
                for info in zf.infolist():
                    if not info.filename.startswith("xl/worksheets/") or not info.filename.endswith(".xml"): continue
                    bounds=[0,0,0]
                    for _,cell in ElementTree.iterparse(io.BytesIO(_read_member(zf,info)),events=("end",)):
                        if cell.tag.endswith("}c"):
                            ref=cell.attrib.get("r",""); match=re.fullmatch(r"([A-Z]+)([0-9]+)",ref.upper())
                            if match:
                                col=0
                                for char in match.group(1): col=col*26+ord(char)-64
                                row=int(match.group(2)); bounds[0]=max(bounds[0],row); bounds[1]=max(bounds[1],col); bounds[2]+=1
                                if row>100_000 or col>512 or bounds[2]>200_000 or bounds[0]*bounds[1]>200_000: raise ValueError("Spreadsheet dimensions or cell count exceed the safety limit")
                        cell.clear()
                    xlsx_bounds[info.filename]=tuple(bounds[:2])
        try:
            if kind == "DOCX":
                from docx import Document
                doc=Document(io.BytesIO(data))
                texts=[p.text for p in doc.paragraphs]
                texts.extend(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
                return "\n".join(texts), "Complete" if any(texts) else "Document opened, but no readable text was found."
            if kind == "XLSX":
                from openpyxl import load_workbook
                workbook=load_workbook(io.BytesIO(data), read_only=True, data_only=True)
                texts=[]; cells=0
                for sheet in workbook.worksheets:
                    bound=xlsx_bounds.get(sheet.path.lstrip("/"), (1,1))
                    sheet.reset_dimensions()
                    for row in sheet.iter_rows(max_row=max(1,bound[0]),max_col=max(1,bound[1]),values_only=True):
                        cells += len(row)
                        if cells > 200_000: raise ValueError("Spreadsheet cell limit exceeded")
                        texts.extend(str(value) for value in row if value is not None)
                workbook.close()
                return "\n".join(texts), "Complete" if texts else "Document opened, but no readable text was found."
            if kind == "PPTX":
                from pptx import Presentation
                deck=Presentation(io.BytesIO(data))
                if len(deck.slides)>500: return "", "Presentation slide limit exceeded (500 slides)."
                texts=[shape.text for slide in deck.slides for shape in slide.shapes if getattr(shape,"has_text_frame",False)]
                return "\n".join(texts), "Complete" if any(texts) else "Document opened, but no readable text was found."
        except ValueError as exc:
            if "limit exceeded" in str(exc): return "", str(exc)
            pass
        except Exception:
            # Damaged/incomplete OOXML can still contain readable XML parts; try the bounded fallback.
            pass
        texts=[]
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            members=_safe_zip(zf)
            for info in members:
                n=info.filename
                wanted_docx = kind=="DOCX" and (n=="word/document.xml" or (n.startswith(("word/header", "word/footer", "word/comments")) and n.endswith(".xml")))
                wanted_xlsx = kind=="XLSX" and (n=="xl/sharedStrings.xml" or (n.startswith("xl/worksheets/") and n.endswith(".xml")))
                wanted_pptx = kind=="PPTX" and n.startswith(("ppt/slides/slide", "ppt/notesSlides/notesSlide")) and n.endswith(".xml")
                wanted = wanted_docx or wanted_xlsx or wanted_pptx
                if wanted:
                    payload=_read_member(zf,info)
                    if len(payload)>MAX_ARCHIVE_MEMBER_BYTES: raise ValueError("Office document part exceeds the safety limit")
                    try: texts.extend(ElementTree.fromstring(payload).itertext())
                    except ElementTree.ParseError: continue
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError, KeyError, ElementTree.ParseError) as exc:
        return "", f"Malformed {kind} document: {exc}"
    return "\n".join(texts), "Complete" if texts else "Document opened, but no readable text was found."

def _scan_archive(data, depth):
    if depth >= MAX_ARCHIVE_DEPTH: return "", "Archive depth limit reached; nested content was not inspected."
    extracted=[]; notices=[]; used=0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in _safe_zip(zf):
                path=PurePosixPath(info.filename.replace("\\", "/"))
                if path.is_absolute() or ".." in path.parts: continue
                payload=_read_member(zf,info); used += len(payload)
                if used>MAX_ARCHIVE_BYTES: raise ValueError("Archive extracted-byte limit exceeded")
                result=extract_content(payload,path.name,"",depth+1)
                if result.text: extracted.append(f"\n--- archive member: {safe_filename(info.filename)} ---\n{result.text}")
                elif result.status not in {"No readable strings were found in this binary file.", "File type detected, but no readable content could be safely extracted."}: notices.append(f"{path.name}: {result.status}")
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        return "", f"Malformed or unreadable ZIP archive: {exc}"
    except ValueError as exc:
        return "", str(exc)
    status=("Partial extraction. " + "; ".join(notices[:3])) if extracted and notices else ("Complete" if extracted else ("; ".join(notices[:3]) or "Archive inspected; no supported readable content was found."))
    return "\n".join(extracted), status

class Extraction:
    def __init__(self, file_type, mime_type, method, status, text):
        self.file_type=file_type; self.mime_type=mime_type; self.method=method; self.status=status; self.text=text

def extract_content(data: bytes, filename: str, supplied_mime: str="", depth: int=0):
    kind,mime=detect_file_type(data,filename,supplied_mime)
    if kind in {"IMAGE_PNG","IMAGE_JPEG","IMAGE_UNSUPPORTED"}:
        label="PNG" if kind=="IMAGE_PNG" else "JPEG" if kind=="IMAGE_JPEG" else "Image"
        return Extraction(kind,mime,"OCR extraction","Image detected. OCR is not currently available.","")
    if kind=="PDF":
        try:
            from pypdf import PdfReader, apply_configuration
            with apply_configuration(maximum_declared_stream_length=MAX_ARCHIVE_MEMBER_BYTES, zlib_maximum_output_length=MAX_ARCHIVE_MEMBER_BYTES, array_based_stream_maximum_output_length=MAX_ARCHIVE_MEMBER_BYTES, jbig2_maximum_output_length=MAX_ARCHIVE_MEMBER_BYTES, lzw_maximum_output_length=MAX_ARCHIVE_MEMBER_BYTES, run_length_maximum_output_length=MAX_ARCHIVE_MEMBER_BYTES, image_maximum_buffer_size=MAX_ARCHIVE_MEMBER_BYTES, page_tree_maximum_entries=2000):
                reader=PdfReader(io.BytesIO(data), strict=False, root_object_recovery_limit=2000)
                if reader.is_encrypted: return Extraction(kind,mime,"PDF text extraction","Encrypted PDF; text extraction unavailable.","")
                if len(reader.pages)>500: return Extraction(kind,mime,"PDF text extraction","PDF page limit exceeded (500 pages).","")
                pages=[]; total_chars=0
                for page in reader.pages:
                    page_text=page.extract_text() or ""
                    total_chars+=len(page_text)
                    if total_chars>MAX_ARCHIVE_BYTES: return Extraction(kind,mime,"PDF text extraction","PDF extracted-text limit exceeded.","")
                    pages.append(page_text)
                text="\n".join(pages)
                return Extraction(kind,mime,"PDF text extraction","Complete" if text.strip() else "PDF opened, but no readable text was found.",text)
        except ImportError: return Extraction(kind,mime,"PDF text extraction","PDF detected. Install pypdf to extract text.","")
        except Exception: return Extraction(kind,mime,"PDF text extraction","Malformed, unreadable, or over-limit PDF; no text was extracted.","")
    if kind in {"DOCX","XLSX","PPTX"}:
        method={"DOCX":"DOCX text extraction","XLSX":"XLSX cell extraction","PPTX":"PPTX slide extraction"}[kind]
        text,status=_office_text(data,kind)
        return Extraction(kind,mime,method,status,text)
    if kind=="ZIP":
        text,status=_scan_archive(data,depth)
        return Extraction(kind,mime,"Safe recursive ZIP content extraction",status,text)
    decoded=_decode_text(data)
    if decoded is not None:
        text=_clean_markup(decoded,kind)
        return Extraction(kind,mime,"Text/source content extraction","Complete" if text.strip() else "File contains no readable text.",text)
    if kind=="BINARY":
        text=_strings(data)
        return Extraction(kind,mime,"Binary/String Analysis","Complete" if text else "No readable strings were found in this binary file.",text)
    text=_strings(data)
    return Extraction(kind,mime,"Safe text/strings fallback","Complete" if text else "File type detected, but no readable content could be safely extracted.",text)
