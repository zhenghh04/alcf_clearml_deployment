import argparse
import time

import mlflow
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--data-size", type=int, default=1024)
    parser.add_argument("--experiment", type=str, default="resnet50-mlflow")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def accuracy(logits, targets):
    preds = torch.argmax(logits, dim=1)
    return (preds == targets).float().mean().item()


def main():
    args = parse_args()

    mlflow.set_experiment(args.experiment)
    with mlflow.start_run():
        mlflow.log_params(vars(args))

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

                mlflow.log_metric("train_loss", loss.item(), step=global_step)
                mlflow.log_metric("train_acc", acc, step=global_step)
                global_step += 1

            steps = len(loader)
            mlflow.log_metric("epoch_loss", epoch_loss / steps, step=epoch)
            mlflow.log_metric("epoch_acc", epoch_acc / steps, step=epoch)
            mlflow.log_metric("epoch_time_sec", time.time() - start, step=epoch)


if __name__ == "__main__":
    main()
