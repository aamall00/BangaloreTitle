import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel

logging.basicConfig(stream = sys.stdout, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", force=True)
log = logging.getLogger(__name__)

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
sys.path.insert(0, str(BASE_DIR))

from ocr.azure_ocr import AzureOCR
from rag.knowledge_base import KnowledgeBase
from analysis.document_parser import DocumentParser
from analysis.title_analyzer import TitleAnalyzer
from analysis.risk_checker import RiskChecker
from db.database import Database
from reports.pdf_generator import PDFGenerator

app = FastAPI(title="Bengaluru Title Scout API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_config: dict = {}
_ocr: Optional[AzureOCR] = None
_kb:  Optional[KnowledgeBase] = None
_db:  Optional[Database] = None


def get_ocr() -> AzureOCR:
    global _ocr
    if _ocr is None:
        _ocr = AzureOCR(
            endpoint=_config.get("azure_endpoint", os.getenv("AZURE_DOC_ENDPOINT", "")),
            key=_config.get("azure_key",      os.getenv("AZURE_DOC_KEY",      "")),
        )
    return _ocr


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase(persist_dir=str(BASE_DIR / "chroma_db"))
        _kb.initialize()
    return _kb


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(db_path=str(BASE_DIR / "title_scout.db"))
        _db.initialize()
    return _db


@app.on_event("startup")
async def startup():
    log.info("Starting Bengaluru Title Scout backend...")
    try:
        get_kb()
        get_db()
        log.info("Knowledge base and database initialized.")
    except Exception as e:
        log.error(f"Startup error: {e}")


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    kb_ok = _kb is not None
    return {
        "status": "ok",
        "message": "Bengaluru Title Scout backend is running",
        "knowledge_base": "loaded" if kb_ok else "not loaded",
    }


class ConfigPayload(BaseModel):
    azure_endpoint:    Optional[str] = None
    azure_key:         Optional[str] = None
    openai_api_key:    Optional[str] = None
    anthropic_api_key: Optional[str] = None
    preferred_llm:     Optional[str] = "claude"


@app.post("/config")
async def set_config(payload: ConfigPayload):
    global _config, _ocr
    _config.update({k: v for k, v in payload.dict().items() if v})
    _ocr = None
    if payload.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = payload.anthropic_api_key
    if payload.openai_api_key:
        os.environ["OPENAI_API_KEY"] = payload.openai_api_key
    return {"status": "ok"}


@app.post("/rebuild-knowledge-base")
async def rebuild_kb():
    global _kb
    _kb = None
    kb = get_kb()
    kb.rebuild()
    return {"status": "ok", "message": "Knowledge base rebuilt."}


@app.post("/analyze")
async def analyze_documents(
    files: List[UploadFile] = File(...),
    doc_type: str = Form("auto"),
    additional_context: str = Form(""),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    upload_dir = BASE_DIR / "uploads"
    upload_dir.mkdir(exist_ok=True)

    saved_paths = []
    try:
        for f in files:
            dest = upload_dir / f.filename
            content = await f.read()
            dest.write_bytes(content)
            saved_paths.append(str(dest))

        ocr_engine = get_ocr()
        kb         = get_kb()
        db         = get_db()

        log.info(f"Running OCR on {len(saved_paths)} file(s)...")
        ocr_results = []
        for path in saved_paths:
            result = ocr_engine.extract(path)
            ocr_results.append(result)

        combined_text = "\n\n--- DOCUMENT BREAK ---\n\n".join(
            r.get("full_text", "") for r in ocr_results
        )

        log.info("Parsing document structure...")
        parser  = DocumentParser()
        parsed  = parser.parse(combined_text, doc_type, ocr_results)

        log.info("Querying Karnataka law knowledge base...")
        law_context = kb.query_relevant_laws(combined_text, parsed)

        log.info("Running AI title analysis...")
        analyzer = TitleAnalyzer(
            preferred_llm=_config.get("preferred_llm", os.getenv("PREFERRED_LLM", "claude"))
        )
        analysis = analyzer.analyze(parsed, law_context, additional_context)

        log.info("Running risk checker...")
        checker = RiskChecker(kb)
        analysis = checker.check(analysis, parsed, law_context)

        db.save_analysis(analysis)
        log.info(f"Analysis complete — Risk: {analysis.get('risk_level')}")
        return JSONResponse(content=analysis)

    except Exception as e:
        log.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for path in saved_paths:
            try:
                os.remove(path)
            except Exception:
                pass


class ReportRequest(BaseModel):
    analysis: dict


@app.post("/generate-report")
async def generate_report(req: ReportRequest):
    try:
        generator = PDFGenerator()
        pdf_bytes = generator.generate(req.analysis)
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="title-report.pdf"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        log.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cases")
async def list_cases():
    db = get_db()
    return db.list_analyses()


@app.get("/cases/{case_id}")
async def get_case(case_id: str):
    db = get_db()
    case = db.get_analysis(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")