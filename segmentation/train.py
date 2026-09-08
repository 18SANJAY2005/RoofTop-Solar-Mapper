"""
train.py

Trains the U-Net rooftop segmentation model.

Usage:
    python train.py --images data/train/images --masks data/train/masks --epochs 30

Download a labeled dataset first:
- Inria Aerial Image Labeling: https://project.inria.fr/aerialimagelabeling/
- SpaceNet Buildings (AWS Open Data): https://spacenet.ai/spacenet-buildings-dataset-v2/
Both need tiling into fixed-size image/mask pairs before use here - see
the dataset's own docs for tiling scripts.
"""
import argparse
import torch
from torch.utils.data import DataLoader
from model import UNet
from dataset import RooftopDataset


def dice_loss(pred, target, eps=1e-6):
    """Dice loss - handles class imbalance well (rooftops are a minority
    of pixels in most tiles), which plain BCE tends to struggle with."""
    pred_flat = pred.view(-1)
    target_flat = target.view(-1)
    intersection = (pred_flat * target_flat).sum()
    return 1 - (2 * intersection + eps) / (pred_flat.sum() + target_flat.sum() + eps)


def train(images_dir, masks_dir, epochs=30, batch_size=8, lr=1e-3, device=None):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on {device}")

    dataset = RooftopDataset(images_dir, masks_dir)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = UNet().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    bce = torch.nn.BCELoss()

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for images, masks in loader:
            images, masks = images.to(device), masks.to(device)

            optimizer.zero_grad()
            preds = model(images)
            loss = bce(preds, masks) + dice_loss(preds, masks)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / len(loader)
        print(f"Epoch {epoch+1}/{epochs} - loss: {avg_loss:.4f}")

    torch.save(model.state_dict(), "rooftop_unet.pt")
    print("Saved model to rooftop_unet.pt")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", required=True, help="path to training images folder")
    parser.add_argument("--masks", required=True, help="path to training masks folder")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    train(args.images, args.masks, args.epochs, args.batch_size, args.lr)
