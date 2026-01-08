import os
import json
import tempfile
import subprocess
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]  # .../01_raster
SEND = ROOT / "send_to_rasterscan.py"
CONVERT = ROOT / "convert_raster_to_scene.py"
TEMPLATE = ROOT / "templates" / "react_planner_template.json"
OUTDIR = ROOT / "out"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # react-planner engine
        "http://localhost:5174",  # plano-ui (common)
        "http://localhost:5175",  # plano-ui (fallback)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload-plan")
async def upload_plan(file: UploadFile = File(...)):
    api_key = os.environ.get("RASTERSCAN_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RASTERSCAN_API_KEY is not set in environment")

    OUTDIR.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(await file.read())

    raw_json = OUTDIR / "rasterscan_raw.json"
    scene_json = OUTDIR / "scene.react.json"

    try:
        subprocess.run(
            [str(SEND), str(tmp_path), str(raw_json)],
            check=True,
            cwd=str(ROOT),
            env=os.environ.copy(),
        )

        subprocess.run(
            [str(CONVERT), str(TEMPLATE), str(raw_json), str(scene_json)],
            check=True,
            cwd=str(ROOT),
            env=os.environ.copy(),
        )

        scene = json.loads(scene_json.read_text(encoding="utf-8"))
        return JSONResponse(scene)

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
