"""
dataset.py

Loads (satellite image tile, rooftop mask) pairs for training.

Expects a folder structure like:
    data/train/images/*.png   (RGB satellite tiles)
    data/train/masks/*.png    (matching binary masks - white=rooftop, black=background)

Compatible with the Inria Aerial Image Labeling Dataset or SpaceNet
Buildings Dataset formats once tiled into matching image/mask pairs
(both are free to download - see README for links).
"""
import os
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset


class RooftopDataset(Dataset):
    def __init__(self, images_dir, masks_dir, tile_size=256):
        self.images_dir = images_dir
        self.masks_dir = masks_dir
        self.tile_size = tile_size
        self.filenames = sorted(os.listdir(images_dir))

    def __len__(self):
        return len(self.filenames)

    def __getitem__(self, idx):
        fname = self.filenames[idx]
        img = Image.open(os.path.join(self.images_dir, fname)).convert("RGB")
        mask = Image.open(os.path.join(self.masks_dir, fname)).convert("L")

        img = img.resize((self.tile_size, self.tile_size))
        mask = mask.resize((self.tile_size, self.tile_size))

        img_arr = np.array(img, dtype=np.float32) / 255.0
        mask_arr = np.array(mask, dtype=np.float32) / 255.0
        mask_arr = (mask_arr > 0.5).astype(np.float32)  # binarize

        img_tensor = torch.from_numpy(img_arr).permute(2, 0, 1)  # HWC -> CHW
        mask_tensor = torch.from_numpy(mask_arr).unsqueeze(0)     # add channel dim

        return img_tensor, mask_tensor
