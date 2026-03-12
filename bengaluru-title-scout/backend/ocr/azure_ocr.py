import os
import base64
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
    from azure.core.credentials import AzureKeyCredential
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    log.warning("azure-ai-documentintelligence not installed. Using fallback OCR.")

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class AzureOCR:
    def __init__(self, endpoint: str = "", key: str = ""):
        self.endpoint = endpoint or os.getenv("AZURE_DOC_ENDPOINT", "")
        self.key      = key      or os.getenv("AZURE_DOC_KEY",      "")
        self._client: Optional[object] = None

    def _get_client(self):
        if not AZURE_AVAILABLE:
            return None
        if not self.endpoint or not self.key:
            log.warning("Azure OCR: endpoint/key not configured. Using fallback.")
            return None
        if self._client is None:
            self._client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key),
            )
        return self._client

    def extract(self, file_path: str) -> dict:
        path = Path(file_path)
        suffix = path.suffix.lower()
        log.info(f"OCR: extracting {path.name} ({suffix})")

        client = self._get_client()
        if client and AZURE_AVAILABLE:
            return self._azure_extract(client, file_path)
        else:
            return self._fallback_extract(file_path, suffix)

    def _azure_extract(self, client, file_path: str) -> dict:
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            poller = client.begin_analyze_document(
                "prebuilt-layout",
                analyze_request=file_bytes,
                content_type="application/octet-stream",
                output_content_format=DocumentContentFormat.MARKDOWN,
            )
            result = poller.result()

            pages_text = []
            tables = []

            for page in (result.pages or []):
                page_lines = [line.content for line in (page.lines or [])]
                pages_text.append("\n".join(page_lines))

            for table in (result.tables or []):
                tbl = []
                for cell in table.cells:
                    while len(tbl) <= cell.row_index:
                        tbl.append([])
                    while len(tbl[cell.row_index]) <= cell.column_index:
                        tbl[cell.row_index].append("")
                    tbl[cell.row_index][cell.column_index] = cell.content
                tables.append(tbl)

            full_text = result.content or "\n\n".join(pages_text)

            return {
                "full_text": full_text,
                "pages":     pages_text,
                "tables":    tables,
                "page_count": len(pages_text),
                "engine":    "azure_document_intelligence",
                "language":  self._detect_language(full_text),
            }

        except Exception as e:
            log.error(f"Azure OCR failed: {e}. Falling back.")
            return self._fallback_extract(file_path, Path(file_path).suffix.lower())

    def _fallback_extract(self, file_path: str, suffix: str) -> dict:
        if suffix == ".pdf":
            if PYMUPDF_AVAILABLE:
                return self._pymupdf_extract(file_path)
            elif PDFPLUMBER_AVAILABLE:
                return self._pdfplumber_extract(file_path)

        if suffix in (".jpg", ".jpeg", ".png", ".tiff", ".tif"):
            return self._image_fallback(file_path)

        return {"full_text": "", "pages": [], "tables": [], "page_count": 0, "engine": "none", "language": "en"}

    def _pymupdf_extract(self, file_path: str) -> dict:
        doc = fitz.open(file_path)
        pages_text = []
        tables = []
        for page in doc:
            text = page.get_text("text")
            pages_text.append(text)
        doc.close()
        full_text = "\n\n".join(pages_text)
        return {
            "full_text": full_text,
            "pages": pages_text,
            "tables": tables,
            "page_count": len(pages_text),
            "engine": "pymupdf",
            "language": self._detect_language(full_text),
        }

    def _pdfplumber_extract(self, file_path: str) -> dict:
        pages_text = []
        tables = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
        full_text = "\n\n".join(pages_text)
        return {
            "full_text": full_text,
            "pages": pages_text,
            "tables": tables,
            "page_count": len(pages_text),
            "engine": "pdfplumber",
            "language": self._detect_language(full_text),
        }

    def _image_fallback(self, file_path: str) -> dict:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang="kan+eng")
            return {
                "full_text": text,
                "pages": [text],
                "tables": [],
                "page_count": 1,
                "engine": "tesseract",
                "language": self._detect_language(text),
            }
        except Exception as e:
            log.warning(f"Tesseract fallback failed: {e}")
            return {"full_text": "", "pages": [], "tables": [], "page_count": 0, "engine": "none", "language": "en"}

    def _detect_language(self, text: str) -> str:
        kannada_chars = sum(1 for c in text if '\u0C80' <= c <= '\u0CFF')
        if kannada_chars > 10:
            return "kn+en" if len(text) > kannada_chars * 3 else "kn"
        return "en"
