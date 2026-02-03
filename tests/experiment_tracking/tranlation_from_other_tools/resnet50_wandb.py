import argparse
import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
import wandb


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--data-size", type=int, default=1024)
    parser.add_argument("--project", type=str, default="resnet50-wandb")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def accuracy(logits, targets):
    preds = torch.argmax(logits, dim=1)
    return (preds == targets).float().mean().item()


def main():
    args = parse_args()

    run = wandb.init(project=args.project, config=vars(args))

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

    dataset = datasets.FakeData(
        size=args.data_size,
        image_size=(3, 224, 224),
        num_classes=1000,
        transform=transform,
    )

    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
    )

    model = models.resnet50(weights=None)
    model.to(args.device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    global_step = 0
    for epoch in range(args.epochs):
        model.train()
        epoch_loss = 0.0
        epoch_acc = 0.0
        start = time.time()
        for batch_idx, (inputs, targets) in enumerate(loader):
            inputs = inputs.to(args.device)
            targets = targets.to(args.device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            acc = accuracy(outputs.detach(), targets)
            epoch_loss += loss.item()
            epoch_acc += acc

            wandb.log({
                "train/loss": loss.item(),
                "train/acc": acc,
                "step": global_step,
            })
            global_step += 1

        steps = len(loader)
        wandb.log({
            "epoch": epoch,
            "epoch/loss": epoch_loss / steps,
            "epoch/acc": epoch_acc / steps,
            "epoch/time_sec": time.time() - start,
        })

    run.finish()


if __name__ == "__main__":
    main()
