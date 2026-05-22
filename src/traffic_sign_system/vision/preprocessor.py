"""Dataset loading, augmentation, and frame preprocessing."""

import os
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.datasets import GTSRB as TorchGTSRB
import albumentations as A
from albumentations.pytorch import ToTensorV2
from pathlib import Path
import yaml
from typing import Optional

from traffic_sign_system.paths import DEFAULT_CONFIG_PATH, project_path


def load_config(path: str = None) -> dict:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def _gauss_noise(std_range=(0.01, 0.06), p=0.2):
    """Albumentations 1.x and 2.x use different Gaussian-noise argument names."""
    try:
        return A.GaussNoise(std_range=std_range, p=p)
    except TypeError:
        var_limit = tuple((v * 255) ** 2 for v in std_range)
        return A.GaussNoise(var_limit=var_limit, p=p)


def _coarse_dropout(num_holes=(1, 3), hole_size=(8, 16), p=0.15):
    """Albumentations 1.x and 2.x use different CoarseDropout argument names."""
    try:
        return A.CoarseDropout(
            num_holes_range=num_holes,
            hole_height_range=hole_size,
            hole_width_range=hole_size,
            p=p,
        )
    except TypeError:
        return A.CoarseDropout(
            max_holes=num_holes[1],
            min_holes=num_holes[0],
            max_height=hole_size[1],
            min_height=hole_size[0],
            max_width=hole_size[1],
            min_width=hole_size[0],
            p=p,
        )


#  Albumentations pipeline (albumentations 2.x compatible) 
def get_train_transforms(img_size: int = 224, aug_cfg: dict = None) -> A.Compose:
    aug_cfg = aug_cfg or {}
    brightness = aug_cfg.get("random_brightness", 0.2)
    contrast = aug_cfg.get("random_contrast", 0.2)
    rotation = aug_cfg.get("random_rotation", 10)
    gaussian_noise = aug_cfg.get("gaussian_noise", True)
    motion_blur = aug_cfg.get("motion_blur", True)
    perspective = aug_cfg.get("perspective", True)

    transforms = [
        A.Resize(img_size, img_size),
        A.RandomBrightnessContrast(
            brightness_limit=brightness,
            contrast_limit=contrast,
            p=0.5,
        ),
        A.HueSaturationValue(p=0.25),
    ]

    if gaussian_noise:
        transforms.append(_gauss_noise(std_range=(0.01, 0.06), p=0.2))
    if motion_blur:
        transforms.append(A.MotionBlur(blur_limit=3, p=0.15))
    if perspective:
        transforms.append(A.Perspective(scale=(0.02, 0.06), p=0.2))

    transforms.extend([
        A.Rotate(limit=rotation, p=0.4),
        _coarse_dropout(num_holes=(1, 3), hole_size=(8, 16), p=0.15),
        A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ToTensorV2(),
    ])

    return A.Compose(transforms)


def get_train_transforms_legacy(img_size: int = 224) -> A.Compose:
    return A.Compose([
        A.Resize(img_size, img_size),
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.6),
        A.HueSaturationValue(p=0.4),
        _gauss_noise(std_range=(0.02, 0.1), p=0.3),
        A.MotionBlur(blur_limit=5, p=0.2),
        A.Perspective(scale=(0.05, 0.1), p=0.3),
        A.Rotate(limit=15, p=0.5),
        _coarse_dropout(num_holes=(1, 4), hole_size=(10, 20), p=0.2),
        A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ToTensorV2(),
    ])


def get_val_transforms(img_size: int = 224) -> A.Compose:
    return A.Compose([
        A.Resize(img_size, img_size),
        A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ToTensorV2(),
    ])


#  Albumentations wrapper around torchvision GTSRB 
class GTSRBDataset(Dataset):
    """
    Wraps torchvision.datasets.GTSRB and applies Albumentations transforms.
    Auto-downloads the dataset on first run (~260 MB).
    """

    def __init__(self, root: str, split: str = "train", transform: A.Compose = None):
        self.transform = transform
        print(f"[Dataset] Loading GTSRB {split} split (auto-download if needed)...")
        self._ds = TorchGTSRB(
            root=root,
            split=split,
            download=True,   # downloads automatically if missing
        )

    def __len__(self):
        return len(self._ds)

    def __getitem__(self, idx):
        img_pil, label = self._ds[idx]
        image = np.array(img_pil.convert("RGB"))
        if self.transform:
            augmented = self.transform(image=image)
            image = augmented["image"]
        else:
            image = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
        return image, label


#  DataLoader factory 
def build_dataloaders(cfg: dict):
    img_size   = cfg["cnn"]["img_size"]
    data_root  = project_path(cfg["paths"]["raw"])
    batch_size = cfg["cnn"]["batch_size"]

    # torchvision GTSRB only has "train" and "test" splits
    train_ds = GTSRBDataset(
        data_root,
        split="train",
        transform=get_train_transforms(img_size, cfg.get("augmentation", {})),
    )
    val_ds   = GTSRBDataset(data_root, split="test",  transform=get_val_transforms(img_size))

    # Use 4 workers on Linux/Mac; 0 on Windows to avoid multiprocessing issues
    num_workers = 0 if os.name == "nt" else 4

    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=torch.cuda.is_available(),
    )

    print(f"[Dataset] Train: {len(train_ds):,} | Val: {len(val_ds):,}")
    return train_loader, val_loader


#  Real-time frame preprocessor 
class FramePreprocessor:
    """Prepare a raw OpenCV BGR frame crop for CNN inference."""

    def __init__(self, img_size: int = 224):
        self.img_size = img_size
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    def preprocess_crop(self, frame: np.ndarray, bbox: tuple) -> Optional[torch.Tensor]:
        """Crop a bounding box region and return a model-ready (1,3,H,W) tensor."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        # Clamp to frame bounds
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        return self.transform(crop_rgb).unsqueeze(0)   # (1, 3, H, W)


if __name__ == "__main__":
    cfg = load_config()
    train_loader, val_loader = build_dataloaders(cfg)
    imgs, labels = next(iter(train_loader))
    print(f"Batch shape: {imgs.shape} | Labels sample: {labels[:5].tolist()}")

