"""
Phase 4: produces the final before/after/severity map with a summary stat
block, using the U-Net as the primary model (baseline shown only as a brief
comparison callout).

Severity coloring is restricted to the same "valid" area used throughout
Phase 3 (our nodata-excluded AND within MTBS's own mapped extent for this
fire) -- predicting severity outside MTBS's assessed area would be an
unvalidated extrapolation, not a real result.

Honesty note baked into the stat block wording: the 60.7% agreement figure
was validated specifically on the held-out eastern test region. The western
region's predictions come from the same trained model but were not
independently validated (the model was trained on that exact data).
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio
import torch
import torch.nn as nn

PATCH_SIZE = 64
SPLIT_COLUMN = 2094
PIXEL_AREA_KM2 = (10 * 10) / 1e6  # 10m x 10m pixels -> km^2

SEVERITY_COLORS = {
    1: "#2ecc71",  # Unburned/very low - green
    2: "#f1c40f",  # Low - yellow
    3: "#e67e22",  # Moderate - orange
    4: "#c0392b",  # High - red
}
SEVERITY_LABELS = {1: "Unburned/very low", 2: "Low", 3: "Moderate", 4: "High"}


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


with rasterio.open("data/processed/before_stack.tif") as src:
    before = src.read()
with rasterio.open("data/processed/after_stack.tif") as src:
    after = src.read()
with rasterio.open("data/processed/mtbs_aligned.tif") as src:
    mtbs = src.read(1)
with rasterio.open("data/processed/baseline_severity.tif") as src:
    baseline = src.read(1)

stack = np.concatenate([before, after], axis=0).astype(np.float32) / 10000.0
valid = np.isin(baseline, [1, 2, 3, 4]) & np.isin(mtbs, [1, 2, 3, 4])
height, width = mtbs.shape

model = SmallUNet()
model.load_state_dict(torch.load("data/processed/unet_model.pt"))
model.eval()

# --- Run inference over the FULL map (train region included, for complete coverage) ---
unet_pred_full = np.full((height, width), -1, dtype=np.int64)
n_rows, n_cols = height // PATCH_SIZE, width // PATCH_SIZE
with torch.no_grad():
    for r in range(n_rows):
        for c in range(n_cols):
            y0, x0 = r * PATCH_SIZE, c * PATCH_SIZE
            x = torch.from_numpy(stack[:, y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE]).unsqueeze(0)
            pred = model(x).argmax(dim=1).squeeze(0).numpy()
            unet_pred_full[y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE] = pred

severity_map = unet_pred_full + 1  # back to 1-4 class numbering

# --- Build the color image for the severity panel ---
severity_rgb = np.ones((height, width, 3))  # white background
for cls, color in SEVERITY_COLORS.items():
    rgb = np.array([int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    severity_rgb[(severity_map == cls) & valid] = rgb
severity_rgb[~valid] = [0.88, 0.88, 0.88]  # light gray for excluded areas

# --- Crop out the black nodata edge (present in both before/after due to
# clipping a lat/long AOI box against UTM-oriented imagery). The nodata
# region turns out to be a contiguous horizontal band at the bottom, not
# spread evenly across columns -- so crop rows first, then find the tightest
# valid column range within that row window. ---
band_nodata = (before == 0).all(axis=0) | (after == 0).all(axis=0)
band_valid = ~band_nodata

row_frac = band_valid.mean(axis=1)
good_rows = np.where(row_frac > 0.95)[0]
row_min, row_max = good_rows.min(), good_rows.max() + 1

col_frac_within_rows = band_valid[row_min:row_max, :].mean(axis=0)
good_cols = np.where(col_frac_within_rows > 0.99)[0]
col_min, col_max = good_cols.min(), good_cols.max() + 1

crop = (slice(row_min, row_max), slice(col_min, col_max))
print(f"Cropping nodata edge: {height}x{width} -> {row_max - row_min}x{col_max - col_min}")

# --- RGB before/after panels ---
RGB_INDICES = [2, 1, 0]


def stretch_rgb(stack6):
    rgb = stack6[RGB_INDICES].astype(np.float32)
    out = np.zeros_like(rgb)
    for i in range(3):
        lo, hi = np.percentile(rgb[i], [2, 98])
        out[i] = np.clip((rgb[i] - lo) / (hi - lo), 0, 1)
    return np.moveaxis(out, 0, -1)


before_rgb = stretch_rgb(before)[crop]
after_rgb = stretch_rgb(after)[crop]
severity_rgb = severity_rgb[crop]

# --- Summary stats (U-Net, over the valid/mapped fire extent) ---
total_valid_px = valid.sum()
total_km2 = total_valid_px * PIXEL_AREA_KM2
class_counts = {cls: int(((severity_map == cls) & valid).sum()) for cls in SEVERITY_LABELS}
class_pct = {cls: 100 * count / total_valid_px for cls, count in class_counts.items()}

stat_lines = [
    "CAMP FIRE — Butte County, California",
    "Ignited Nov 8, 2018 | Before: Oct 22, 2018  |  After: Jan 25, 2019",
    "",
    f"Total area analyzed: {total_km2:.1f} km²",
    "",
    "Severity breakdown (U-Net model):",
]
for cls in [4, 3, 2, 1]:
    stat_lines.append(f"  {SEVERITY_LABELS[cls]:<20} {class_pct[cls]:5.1f}%")
stat_lines += [
    "",
    "Model validation (held-out eastern test region only):",
    "  U-Net: 60.7% agreement with official MTBS ground truth",
    "  vs. simple dNBR-threshold baseline: 44.9%",
    "",
    "Note: severity shown for the full mapped area uses this same",
    "trained model; the 60.7% figure applies specifically to the",
    "held-out eastern test region, not the full map shown here.",
]

# --- Assemble the figure ---
# Size the figure to match the cropped images' real aspect ratio, so each
# image panel fills its cell exactly with no leftover padding.
crop_h, crop_w = before_rgb.shape[0], before_rgb.shape[1]
img_aspect = crop_w / crop_h  # width:height per image panel
text_width_ratio = 0.9
fig_height = 6.0
fig_width = fig_height * (3 * img_aspect + text_width_ratio)

fig = plt.figure(figsize=(fig_width, fig_height))
gs = fig.add_gridspec(1, 4, width_ratios=[img_aspect, img_aspect, img_aspect, text_width_ratio])

ax0 = fig.add_subplot(gs[0])
ax0.imshow(before_rgb)
ax0.set_title("Before: Oct 22, 2018")
ax0.axis("off")

ax1 = fig.add_subplot(gs[1])
ax1.imshow(after_rgb)
ax1.set_title("After: Jan 25, 2019")
ax1.axis("off")

ax2 = fig.add_subplot(gs[2])
ax2.imshow(severity_rgb)
ax2.set_title("Burn Severity (U-Net)")
ax2.axis("off")
import matplotlib.patches as mpatches
legend_patches = [mpatches.Patch(color=SEVERITY_COLORS[c], label=SEVERITY_LABELS[c]) for c in [1, 2, 3, 4]]
ax2.legend(handles=legend_patches, loc="lower left", fontsize=8, framealpha=0.9)

ax3 = fig.add_subplot(gs[3])
ax3.axis("off")
ax3.text(0.02, 0.98, "\n".join(stat_lines), transform=ax3.transAxes,
          fontsize=10.5, va="top", family="monospace")

plt.tight_layout()
plt.savefig("data/processed/phase4_final_output.png", dpi=150, bbox_inches="tight")
print("Saved data/processed/phase4_final_output.png")
print("\nStat block contents:")
print("\n".join(stat_lines))
