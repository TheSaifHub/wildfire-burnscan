"""
Phase 6 backend. Serves precomputed Camp Fire results -- no live Earth
Engine or model calls happen here, everything comes from fires.db and
static/, both produced once by seed.py.
"""

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

BACKEND_DIR = Path(__file__).parent
DB_PATH = BACKEND_DIR / "fires.db"

app = FastAPI(title="Wildfire BurnScan API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BACKEND_DIR / "static"), name="static")


def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/fires")
def list_fires():
    rows = query("SELECT id, name, location, ignition_date FROM fires")
    return rows


@app.get("/fires/{fire_id}")
def get_fire(fire_id: str):
    rows = query("SELECT * FROM fires WHERE id = ?", (fire_id,))
    if not rows:
        raise HTTPException(status_code=404, detail=f"Fire '{fire_id}' not found")
    row = rows[0]
    return {
        "id": row["id"],
        "name": row["name"],
        "location": row["location"],
        "ignition_date": row["ignition_date"],
        "before_date": row["before_date"],
        "after_date": row["after_date"],
        "bounds": {
            "west": row["bounds_west"],
            "south": row["bounds_south"],
            "east": row["bounds_east"],
            "north": row["bounds_north"],
        },
        "stats": {
            "total_area_km2": row["total_area_km2"],
            "severity_breakdown_pct": {
                "unburned": row["pct_unburned"],
                "low": row["pct_low"],
                "moderate": row["pct_moderate"],
                "high": row["pct_high"],
            },
            "validation": {
                "unet_agreement_pct": row["unet_agreement_pct"],
                "baseline_agreement_pct": row["baseline_agreement_pct"],
                "note": "Agreement figures validated on a held-out test region, not the full map.",
            },
        },
        "images": {
            "before": row["before_image"],
            "after": row["after_image"],
            "severity": row["severity_image"],
        },
    }
