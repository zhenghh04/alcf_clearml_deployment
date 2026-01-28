from __future__ import print_function

import argparse
import os
import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models


def _get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def train_one_epoch(model, loader, optimizer, criterion, device, epoch, log_interval):
    model.train()
    running_loss = 0.0
    for batch_idx, (data, target) in enumerate(loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad(set_to_none=True)
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        if batch_idx % log_interval == 0:
            avg_loss = running_loss / max(1, batch_idx + 1)
            print(f"Epoch {epoch} [{batch_idx}/{len(loader)}] loss={avg_loss:.4f}")


def validate(model, loader, criterion, device):
    model.eval()
    loss = 0.0
    correct = 0
    with torch.no_grad():
        for data, target in loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            loss += criterion(output, target).item()
            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()

    loss /= max(1, len(loader))
    acc = correct / max(1, len(loader.dataset))
    print(f"Validation: loss={loss:.4f} acc={acc:.4f}")
    return loss, acc


def main():
    parser = argparse.ArgumentParser(description="ResNet50 CIFAR-10 training")
    parser.add_argument("--data-dir", default=os.environ.get("CIFAR10_DIR", "./"))
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--log-interval", type=int, default=20)
    parser.add_argument("--download", action="store_true", default=False)
    parser.add_argument("--checkpoint", default=os.environ.get("RESNET50_CKPT", "/tmp/resnet50_cifar10.pt"))
    args = parser.parse_args()

    device = _get_device()
    print("Using device:", device)

    transform_train = transforms.Compose(
        [
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )
    transform_test = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ]
    )

    train_root = args.data_dir
    test_root = args.data_dir
    train_set = datasets.CIFAR10(root=train_root, train=True, download=True, transform=transform_train)
    test_set = datasets.CIFAR10(root=test_root, train=False, download=True, transform=transform_test)

    train_loader = DataLoader(
        train_set, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers, pin_memory=True
    )
    test_loader = DataLoader(
        test_set, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers, pin_memory=True
    )

    model = models.resnet50(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 10)
    model.to(device)

    optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=0.9, weight_decay=5e-4)
    criterion = nn.CrossEntropyLoss()

    start = time.time()
    for epoch in range(1, args.epochs + 1):
        train_one_epoch(model, train_loader, optimizer, criterion, device, epoch, args.log_interval)
        validate(model, test_loader, criterion, device)
    torch.save(model.state_dict(), args.checkpoint)
    print("Saved checkpoint:", args.checkpoint)
    print("Training finished in {:.2f}s".format(time.time() - start))


if __name__ == "__main__":
    main()
