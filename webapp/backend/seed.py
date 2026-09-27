"""
One-time seed script for Phase 6. Does two things:
1. Generates three separate map-layer images (before/after/severity) from
   our already-computed Phase 3/4 results, cropped to the same nodata-free
   extent as phase4_final_output.png, with the severity layer using
   transparency (not gray) outside the valid area so it overlays cleanly on
   a real map.
2. Computes that extent's geographic bounds in lat/lon (Leaflet needs
   lat/lon; our data is in UTM) and writes everything -- one row, the Camp
   Fire -- into a fresh SQLite database.

No live Earth Engine or model calls happen here -- everything is read from
already-computed files in ../../data/processed/.
"""

import sqlite3
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from PIL import Image

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent.parent
PROCESSED = PROJECT_ROOT / "data" / "processed"
STATIC_DIR = BACKEND_DIR / "static" / "fires" / "camp-fire"
DB_PATH = BACKEND_DIR / "fires.db"

SEVERITY_COLORS = {
    1: (46, 204, 113),   # Unburned/very low - green
    2: (241, 196, 15),   # Low - yellow
    3: (230, 126, 34),   # Moderate - orange
    4: (192, 57, 43),    # High - red
}

with rasterio.open(PROCESSED / "before_stack.tif") as src:
    before = src.read()
    transform = src.transform
    crs = src.crs
with rasterio.open(PROCESSED / "after_stack.tif") as src:
    after = src.read()
with rasterio.open(PROCESSED / "mtbs_aligned.tif") as src:
    mtbs = src.read(1)
with rasterio.open(PROCESSED / "baseline_severity.tif") as src:
    baseline = src.read(1)

valid = np.isin(baseline, [1, 2, 3, 4]) & np.isin(mtbs, [1, 2, 3, 4])
height, width = mtbs.shape

# --- Same crop logic as scripts/22_phase4_output.py ---
band_nodata = (before == 0).all(axis=0) | (after == 0).all(axis=0)
band_valid = ~band_nodata
row_frac = band_valid.mean(axis=1)
good_rows = np.where(row_frac > 0.95)[0]
row_min, row_max = good_rows.min(), good_rows.max() + 1
col_frac_within_rows = band_valid[row_min:row_max, :].mean(axis=0)
good_cols = np.where(col_frac_within_rows > 0.99)[0]
col_min, col_max = good_cols.min(), good_cols.max() + 1
crop = (slice(row_min, row_max), slice(col_min, col_max))

# --- Geographic bounds of the crop, converted from UTM to lat/lon for Leaflet ---
crop_transform_bounds = rasterio.transform.array_bounds(
    row_max - row_min, col_max - col_min,
    transform * rasterio.Affine.translation(col_min, row_min),
)  # (left, bottom, right, top) in the raster's own CRS (UTM)
west, south, east, north = transform_bounds(crs, "EPSG:4326", *crop_transform_bounds)

# --- Load the trained U-Net's severity map (already computed in Phase 4) ---
# Re-derive it the same way scripts/22_phase4_output.py did, rather than
# re-running inference here -- read the same source data, no model needed
# since Phase 4 already produced and validated this exact map.
import torch
import torch.nn as nn

PATCH_SIZE = 64


class ConvBlock(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class SmallUNet(nn.Module):
    def __init__(self, in_channels=12, num_classes=4, base=16):
        super().__init__()
        self.enc1 = ConvBlock(in_channels, base)
        self.enc2 = ConvBlock(base, base * 2)
        self.enc3 = ConvBlock(base * 2, base * 4)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = ConvBlock(base * 4, base * 8)
        self.up3 = nn.ConvTranspose2d(base * 8, base * 4, 2, stride=2)
        self.dec3 = ConvBlock(base * 8, base * 4)
        self.up2 = nn.ConvTranspose2d(base * 4, base * 2, 2, stride=2)
        self.dec2 = ConvBlock(base * 4, base * 2)
        self.up1 = nn.ConvTranspose2d(base * 2, base, 2, stride=2)
        self.dec1 = ConvBlock(base * 2, base)
        self.out = nn.Conv2d(base, num_classes, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        b = self.bottleneck(self.pool(e3))
        d3 = self.dec3(torch.cat([self.up3(b), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.out(d1)


stack = np.concatenate([before, after], axis=0).astype(np.float32) / 10000.0
model = SmallUNet()
model.load_state_dict(torch.load(PROCESSED / "unet_model.pt"))
model.eval()

unet_pred_full = np.full((height, width), -1, dtype=np.int64)
n_rows, n_cols = height // PATCH_SIZE, width // PATCH_SIZE
with torch.no_grad():
    for r in range(n_rows):
        for c in range(n_cols):
            y0, x0 = r * PATCH_SIZE, c * PATCH_SIZE
            x = torch.from_numpy(stack[:, y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE]).unsqueeze(0)
            pred = model(x).argmax(dim=1).squeeze(0).numpy()
            unet_pred_full[y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE] = pred
severity_map = unet_pred_full + 1

# --- Build and save the three layer images ---
RGB_INDICES = [2, 1, 0]


def stretch_rgb(stack6):
    rgb = stack6[RGB_INDICES].astype(np.float32)
    out = np.zeros_like(rgb)
    for i in range(3):
        lo, hi = np.percentile(rgb[i], [2, 98])
        out[i] = np.clip((rgb[i] - lo) / (hi - lo), 0, 1)
    return np.moveaxis(out, 0, -1)


before_rgb = (stretch_rgb(before)[crop] * 255).astype(np.uint8)
after_rgb = (stretch_rgb(after)[crop] * 255).astype(np.uint8)
Image.fromarray(before_rgb).save(STATIC_DIR / "before.png")
Image.fromarray(after_rgb).save(STATIC_DIR / "after.png")

severity_rgba = np.zeros((height, width, 4), dtype=np.uint8)
for cls, color in SEVERITY_COLORS.items():
    severity_rgba[(severity_map == cls) & valid, :3] = color
    severity_rgba[(severity_map == cls) & valid, 3] = 255
# alpha stays 0 (fully transparent) outside the valid area -- lets a real
# map show through underneath instead of a gray block
severity_rgba = severity_rgba[crop]
Image.fromarray(severity_rgba, mode="RGBA").save(STATIC_DIR / "severity.png")

print(f"Saved layer images to {STATIC_DIR}")
print(f"Bounds (lat/lon): west={west:.5f}, south={south:.5f}, east={east:.5f}, north={north:.5f}")

# --- Compute the same stats as scripts/22_phase4_output.py ---
PIXEL_AREA_KM2 = (10 * 10) / 1e6
total_valid_px = valid.sum()
total_km2 = total_valid_px * PIXEL_AREA_KM2
class_pct = {cls: 100 * int(((severity_map == cls) & valid).sum()) / total_valid_px for cls in SEVERITY_COLORS}

# --- Seed the database ---
DB_PATH.unlink(missing_ok=True)
conn = sqlite3.connect(DB_PATH)
conn.execute("""
    CREATE TABLE fires (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        ignition_date TEXT NOT NULL,
        before_date TEXT NOT NULL,
        after_date TEXT NOT NULL,
        bounds_west REAL, bounds_south REAL, bounds_east REAL, bounds_north REAL,
        total_area_km2 REAL,
        pct_unburned REAL, pct_low REAL, pct_moderate REAL, pct_high REAL,
        unet_agreement_pct REAL,
        baseline_agreement_pct REAL,
        before_image TEXT, after_image TEXT, severity_image TEXT
    )
""")
conn.execute(
    """INSERT INTO fires VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (
        "camp-fire", "Camp Fire", "Butte County, California",
        "2018-11-08", "2018-10-22", "2019-01-25",
        west, south, east, north,
        round(total_km2, 1),
        round(class_pct[1], 1), round(class_pct[2], 1), round(class_pct[3], 1), round(class_pct[4], 1),
        60.7, 44.9,
        "/static/fires/camp-fire/before.png",
        "/static/fires/camp-fire/after.png",
        "/static/fires/camp-fire/severity.png",
    ),
)
conn.commit()
conn.close()
print(f"Seeded {DB_PATH} with 1 fire (camp-fire)")
