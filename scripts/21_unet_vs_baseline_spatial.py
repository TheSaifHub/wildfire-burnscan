"""
Spatially compares the U-Net's disagreement pattern against MTBS to the
baseline's, restricted to the SAME held-out test region for both (a fair,
like-for-like comparison -- showing baseline errors across the whole image
would be misleading since only the test region is a fair U-Net evaluation).
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import numpy as np
import rasterio
import torch
import torch.nn as nn

PATCH_SIZE = 64
SPLIT_COLUMN = 2094
IGNORE_INDEX = -100


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
n_rows, n_cols = height // PATCH_SIZE, width // PATCH_SIZE

test_coords = []
for r in range(n_rows):
    for c in range(n_cols):
        y0, x0 = r * PATCH_SIZE, c * PATCH_SIZE
        patch_valid = valid[y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE]
        if patch_valid.mean() < 0.5:
            continue
        if (x0 + PATCH_SIZE // 2) >= SPLIT_COLUMN:
            test_coords.append((y0, x0))

model = SmallUNet()
model.load_state_dict(torch.load("data/processed/unet_model.pt"))
model.eval()

# in_test_region marks every pixel covered by a kept test patch
in_test_region = np.zeros((height, width), dtype=bool)
unet_pred_full = np.full((height, width), -1, dtype=np.int64)  # 0-3, or -1 if not predicted

with torch.no_grad():
    for y0, x0 in test_coords:
        x = torch.from_numpy(stack[:, y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE]).unsqueeze(0)
        pred = model(x).argmax(dim=1).squeeze(0).numpy()
        unet_pred_full[y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE] = pred
        in_test_region[y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE] = True

test_valid = in_test_region & valid
mtbs_reindexed = mtbs.astype(np.int64) - 1  # 1-4 -> 0-3, matches U-Net's label space
baseline_reindexed = baseline.astype(np.int64) - 1  # baseline is 1-4 (or 255->254, excluded via test_valid anyway)


def categorize(pred, truth, mask):
    category = np.zeros(pred.shape, dtype=np.uint8)
    category[mask & (pred == truth)] = 1
    category[mask & (pred > truth)] = 2
    category[mask & (pred < truth)] = 3
    return category


baseline_category = categorize(baseline_reindexed, mtbs_reindexed, test_valid)
unet_category = categorize(unet_pred_full, mtbs_reindexed, test_valid)

colors = ["#e0e0e0", "#2ca02c", "#d62728", "#1f77b4"]
labels = ["Excluded (train region/nodata)", "Agree", "Overestimated severity", "Underestimated severity"]
cmap = ListedColormap(colors)

# Crop to just the test region for a tighter, clearer view
test_cols = np.where(in_test_region.any(axis=0))[0]
x_min, x_max = test_cols.min(), test_cols.max() + 1
test_rows = np.where(in_test_region.any(axis=1))[0]
y_min, y_max = test_rows.min(), test_rows.max() + 1

fig, axes = plt.subplots(1, 2, figsize=(16, 9))
axes[0].imshow(baseline_category[y_min:y_max, x_min:x_max], cmap=cmap, vmin=0, vmax=3)
axes[0].set_title("Baseline vs MTBS (test region only)")
axes[0].axis("off")

axes[1].imshow(unet_category[y_min:y_max, x_min:x_max], cmap=cmap, vmin=0, vmax=3)
axes[1].set_title("U-Net vs MTBS (test region only)")
axes[1].axis("off")

patches = [mpatches.Patch(color=colors[i], label=labels[i]) for i in range(4)]
fig.legend(handles=patches, loc="lower center", ncol=4, fontsize=9, bbox_to_anchor=(0.5, -0.02))

plt.tight_layout()
plt.savefig("data/processed/unet_vs_baseline_spatial.png", dpi=150, bbox_inches="tight")
print("Saved data/processed/unet_vs_baseline_spatial.png")

for name, category in [("Baseline", baseline_category), ("U-Net", unet_category)]:
    total = test_valid.sum()
    print(f"\n{name} (test region only):")
    for i, label in enumerate(labels):
        if i == 0:
            continue
        count = (category == i).sum()
        print(f"  {label:<28} {count:>10} pixels ({100 * count / total:.1f}% of valid test pixels)")
