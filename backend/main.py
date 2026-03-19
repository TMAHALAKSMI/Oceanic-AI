"""
Ocean Waste Detection System - FastAPI Backend
"""
import os
import uuid
import json
import time
import base64
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from utils.detector import WasteDetector
from utils.database import DatabaseManager
from utils.image_utils import encode_image_base64, create_comparison_image

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── App Setup ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Ocean Waste Detection API",
    description="AI-powered ocean plastic and waste detection from drone/satellite imagery",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Directories ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# Serve static result images
app.mount("/results", StaticFiles(directory=str(RESULT_DIR)), name="results")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ─── Global Instances ────────────────────────────────────────────────────────
detector = WasteDetector()
db = DatabaseManager(BASE_DIR / "waste_detection.db")


# ─── Pydantic Models ────────────────────────────────────────────────────────
class DetectionResult(BaseModel):
    id: str
    filename: str
    timestamp: str
    waste_detected: bool
    total_detections: int
    waste_types: dict
    confidence_avg: float
    ocean_health_score: float
    image_url: str
    result_url: str
    detections: list


class StatsResponse(BaseModel):
    total_analyses: int
    total_waste_items: int
    avg_confidence: float
    most_common_waste: str
    clean_ocean_pct: float
    polluted_ocean_pct: float


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Ocean Waste Detection API", "status": "operational", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "detector_ready": detector.model_loaded, "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/detect", response_model=DetectionResult)
async def detect_waste(file: UploadFile = File(...)):
    """Upload an ocean image and run waste detection."""
    # Validate
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    detection_id = str(uuid.uuid4())[:12]
    timestamp = datetime.utcnow().isoformat()

    # Save upload
    upload_filename = f"{detection_id}_original{file_ext}"
    upload_path = UPLOAD_DIR / upload_filename
    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    logger.info(f"Processing image: {file.filename} → {upload_filename}")

    # Run detection
    try:
        t0 = time.time()
        result_image, detections, stats = detector.detect(str(upload_path))
        elapsed = time.time() - t0
        logger.info(f"Detection completed in {elapsed:.2f}s — found {len(detections)} objects")
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

    # Save result image
    result_filename = f"{detection_id}_result.jpg"
    result_path = RESULT_DIR / result_filename
    cv2.imwrite(str(result_path), result_image)

    # Build response
    waste_types = {}
    total_conf = 0.0
    for d in detections:
        label = d["label"]
        waste_types[label] = waste_types.get(label, 0) + 1
        total_conf += d["confidence"]

    conf_avg = round(total_conf / len(detections), 4) if detections else 0.0
    waste_detected = len(detections) > 0
    health_score = round(max(0.0, 1.0 - (len(detections) * 0.08)), 2)

    record = {
        "id": detection_id,
        "filename": file.filename,
        "timestamp": timestamp,
        "waste_detected": waste_detected,
        "total_detections": len(detections),
        "waste_types": json.dumps(waste_types),
        "confidence_avg": conf_avg,
        "ocean_health_score": health_score,
        "upload_path": upload_filename,
        "result_path": result_filename,
        "detections_json": json.dumps(detections),
        "processing_time": round(elapsed, 3),
    }
    db.save_detection(record)

    return DetectionResult(
        id=detection_id,
        filename=file.filename,
        timestamp=timestamp,
        waste_detected=waste_detected,
        total_detections=len(detections),
        waste_types=waste_types,
        confidence_avg=conf_avg,
        ocean_health_score=health_score,
        image_url=f"/uploads/{upload_filename}",
        result_url=f"/results/{result_filename}",
        detections=detections,
    )


@app.get("/api/history")
async def get_history(limit: int = 20, offset: int = 0):
    """Get detection history."""
    records = db.get_history(limit=limit, offset=offset)
    total = db.get_total_count()
    return {"total": total, "offset": offset, "limit": limit, "records": records}


@app.get("/api/detection/{detection_id}")
async def get_detection(detection_id: str):
    """Get a single detection record."""
    record = db.get_detection(detection_id)
    if not record:
        raise HTTPException(status_code=404, detail="Detection not found")
    return record


@app.delete("/api/detection/{detection_id}")
async def delete_detection(detection_id: str):
    """Delete a detection record and its files."""
    record = db.get_detection(detection_id)
    if not record:
        raise HTTPException(status_code=404, detail="Detection not found")

    # Remove files
    for path in [UPLOAD_DIR / record["upload_path"], RESULT_DIR / record["result_path"]]:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass

    db.delete_detection(detection_id)
    return {"message": "Deleted successfully"}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Aggregate statistics across all detections."""
    return db.get_stats()


@app.post("/api/compare")
async def compare_images(
    clean_image: UploadFile = File(...),
    polluted_image: UploadFile = File(...)
):
    """Side-by-side comparison between a clean ocean image and a polluted one."""
    for f, label in [(clean_image, "clean"), (polluted_image, "polluted")]:
        if not f.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"{label} file must be an image")

    cid = str(uuid.uuid4())[:8]

    # Save both
    clean_path = UPLOAD_DIR / f"{cid}_clean{Path(clean_image.filename).suffix}"
    poll_path = UPLOAD_DIR / f"{cid}_polluted{Path(polluted_image.filename).suffix}"
    clean_path.write_bytes(await clean_image.read())
    poll_path.write_bytes(await polluted_image.read())

    # Detect on polluted
    result_img, detections, _ = detector.detect(str(poll_path))

    # Build comparison image
    comp_img = create_comparison_image(str(clean_path), result_img)
    comp_filename = f"{cid}_comparison.jpg"
    comp_path = RESULT_DIR / comp_filename
    cv2.imwrite(str(comp_path), comp_img)

    return {
        "comparison_url": f"/results/{comp_filename}",
        "detections": len(detections),
        "waste_types": {d["label"]: 1 for d in detections},
    }


@app.post("/api/thermal")
async def thermal_analysis(file: UploadFile = File(...)):
    """Generate a simulated thermal/heatmap overlay for the image."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    tid = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix
    tmp_path = UPLOAD_DIR / f"{tid}_thermal_in{ext}"
    tmp_path.write_bytes(await file.read())

    img = cv2.imread(str(tmp_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Simulate thermal by equalizing + applying colormap
    eq = cv2.equalizeHist(gray)
    thermal = cv2.applyColorMap(eq, cv2.COLORMAP_JET)
    blended = cv2.addWeighted(img, 0.45, thermal, 0.55, 0)

    out_filename = f"{tid}_thermal_out.jpg"
    out_path = RESULT_DIR / out_filename
    cv2.imwrite(str(out_path), blended)

    return {"thermal_url": f"/results/{out_filename}"}
