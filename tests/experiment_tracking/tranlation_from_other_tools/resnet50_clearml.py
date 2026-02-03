import argparse
import time

import torch
import torch.nn as nn
import torch.optim as optim
from clearml import Task
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--data-size", type=int, default=1024)
    parser.add_argument("--project", type=str, default="resnet50-clearml")
    parser.add_argument("--task-name", type=str, default="resnet50")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def accuracy(logits, targets):
    preds = torch.argmax(logits, dim=1)
    return (preds == targets).float().mean().item()


def main():
    args = parse_args()

    task = Task.init(project_name=args.project, task_name=args.task_name)
    task.connect(vars(args))
    logger = task.get_logger()

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
        for inputs, targets in loader:
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

            logger.report_scalar("train", "loss", value=loss.item(), iteration=global_step)
            logger.report_scalar("train", "acc", value=acc, iteration=global_step)
            global_step += 1

        steps = len(loader)
        logger.report_scalar("epoch", "loss", value=epoch_loss / steps, iteration=epoch)
        logger.report_scalar("epoch", "acc", value=epoch_acc / steps, iteration=epoch)
        logger.report_scalar("epoch", "time_sec", value=time.time() - start, iteration=epoch)


if __name__ == "__main__":
    main()
