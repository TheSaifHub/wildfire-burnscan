"""
Phase 3, segmentation model: builds a small U-Net and trains it on 64x64
patches of the Camp Fire (west 60% = train, east 40% = test, per
17_choose_split.py / 19_verify_patch_class_counts.py), using all 12 raw
bands (6 before + 6 after) as input and MTBS's severity map as labels.
"""

import numpy as np
import rasterio
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

torch.manual_seed(0)
np.random.seed(0)

PATCH_SIZE = 64
SPLIT_COLUMN = 2094
NUM_CLASSES = 4  # 1=Unburned/very low, 2=Low, 3=Moderate, 4=High -> reindexed 0-3
IGNORE_INDEX = -100

# --- Load full rasters ---
with rasterio.open("data/processed/before_stack.tif") as src:
    before = src.read()  # (6, H, W)
with rasterio.open("data/processed/after_stack.tif") as src:
    after = src.read()  # (6, H, W)
with rasterio.open("data/processed/mtbs_aligned.tif") as src:
    mtbs = src.read(1)
with rasterio.open("data/processed/baseline_severity.tif") as src:
    baseline = src.read(1)

stack = np.concatenate([before, after], axis=0).astype(np.float32) / 10000.0  # (12, H, W)
valid = np.isin(baseline, [1, 2, 3, 4]) & np.isin(mtbs, [1, 2, 3, 4])
labels = np.where(valid, mtbs.astype(np.int64) - 1, IGNORE_INDEX).astype(np.int64)  # reindex 1-4 -> 0-3

height, width = mtbs.shape
n_rows, n_cols = height // PATCH_SIZE, width // PATCH_SIZE

train_coords, test_coords = [], []
for r in range(n_rows):
    for c in range(n_cols):
        y0, x0 = r * PATCH_SIZE, c * PATCH_SIZE
        patch_valid = valid[y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE]
        if patch_valid.mean() < 0.5:
            continue
        target = train_coords if (x0 + PATCH_SIZE // 2) < SPLIT_COLUMN else test_coords
        target.append((y0, x0))

print(f"Patches: {len(train_coords)} train, {len(test_coords)} test")


class PatchDataset(Dataset):
    def __init__(self, coords):
        self.coords = coords

    def __len__(self):
        return len(self.coords)

    def __getitem__(self, idx):
        y0, x0 = self.coords[idx]
        x = stack[:, y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE]
        y = labels[y0:y0 + PATCH_SIZE, x0:x0 + PATCH_SIZE]
        return torch.from_numpy(x), torch.from_numpy(y)


train_loader = DataLoader(PatchDataset(train_coords), batch_size=16, shuffle=True)
test_loader = DataLoader(PatchDataset(test_coords), batch_size=16, shuffle=False)


class ConvBlock(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class SmallUNet(nn.Module):
    """3-level U-Net, kept deliberately small given the dataset is one fire."""

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


model = SmallUNet()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss(ignore_index=IGNORE_INDEX)

EPOCHS = 25
for epoch in range(1, EPOCHS + 1):
    model.train()
    total_loss = 0.0
    for x, y in train_loader:
        optimizer.zero_grad()
        pred = model(x)
        loss = criterion(pred, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * x.size(0)
    avg_loss = total_loss / len(train_coords)
    print(f"Epoch {epoch:2d}/{EPOCHS}  train loss: {avg_loss:.4f}")

torch.save(model.state_dict(), "data/processed/unet_model.pt")
print("Saved data/processed/unet_model.pt")

# --- Evaluate on test patches ---
model.eval()
confusion = np.zeros((NUM_CLASSES, NUM_CLASSES), dtype=np.int64)
with torch.no_grad():
    for x, y in test_loader:
        pred = model(x).argmax(dim=1)
        pred_np = pred.numpy()
        y_np = y.numpy()
        mask = y_np != IGNORE_INDEX
        for i in range(NUM_CLASSES):
            for j in range(NUM_CLASSES):
                confusion[i, j] += int(((pred_np == i) & (y_np == j) & mask).sum())

total_valid = confusion.sum()
agreement = np.trace(confusion) / total_valid
labels_map = {0: "Unburned/very low", 1: "Low", 2: "Moderate", 3: "High"}
print(f"\nU-Net test-set overall agreement: {100 * agreement:.1f}%  (baseline was 44.9%)")
print("\nPer-class breakdown:")
for i in range(NUM_CLASSES):
    row_total = confusion[i].sum()
    if row_total == 0:
        continue
    match_pct = 100 * confusion[i, i] / row_total
    print(f"  Predicted '{labels_map[i]}' ({row_total} px) -> actually correct: {match_pct:.1f}%")
