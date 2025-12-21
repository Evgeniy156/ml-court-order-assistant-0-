"""
Обучение CNN модели для распознавания цифр 0-9.
"""
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple
import random


class DigitDataset(Dataset):
    """Датасет для обучения модели распознавания цифр."""
    
    def __init__(self, data_dir: str, augment: bool = True):
        """
        Args:
            data_dir: директория с подпапками 0-9
            augment: применять аугментации
        """
        self.data_dir = data_dir
        self.augment = augment
        self.samples = []
        
        # Загружаем все изображения
        for digit in range(10):
            digit_dir = os.path.join(data_dir, str(digit))
            if not os.path.exists(digit_dir):
                continue
            
            for img_file in os.listdir(digit_dir):
                if img_file.endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(digit_dir, img_file)
                    self.samples.append((img_path, digit))
        
        print(f"Загружено {len(self.samples)} образцов")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        
        # Загружаем изображение
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            # Fallback: создаем пустое изображение
            img = np.zeros((32, 32), dtype=np.uint8)
        
        # Resize до 32x32 если нужно
        if img.shape != (32, 32):
            img = cv2.resize(img, (32, 32), interpolation=cv2.INTER_AREA)
        
        # Нормализуем в [0, 1]
        img = img.astype(np.float32) / 255.0
        
        # Аугментации
        if self.augment:
            img = self._augment(img)
        
        # Преобразуем в тензор
        img_tensor = torch.from_numpy(img).unsqueeze(0)  # (1, 32, 32)
        
        return img_tensor, label
    
    def _augment(self, img: np.ndarray) -> np.ndarray:
        """Применяет аугментации к изображению."""
        # Поворот
        if random.random() < 0.5:
            angle = random.uniform(-10, 10)
            center = (16, 16)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            img = cv2.warpAffine(img, M, (32, 32), borderMode=cv2.BORDER_REPLICATE)
        
        # Сдвиг
        if random.random() < 0.5:
            tx = random.uniform(-2, 2)
            ty = random.uniform(-2, 2)
            M = np.float32([[1, 0, tx], [0, 1, ty]])
            img = cv2.warpAffine(img, M, (32, 32), borderMode=cv2.BORDER_REPLICATE)
        
        # Размытие
        if random.random() < 0.3:
            img = cv2.GaussianBlur(img, (3, 3), 0)
        
        # Шум
        if random.random() < 0.3:
            noise = np.random.normal(0, 0.05, img.shape)
            img = np.clip(img + noise, 0, 1)
        
        # Контраст
        if random.random() < 0.5:
            alpha = random.uniform(0.8, 1.2)
            img = np.clip(img * alpha, 0, 1)
        
        return img


def train_model(
    data_dir: str,
    output_path: str,
    epochs: int = 50,
    batch_size: int = 32,
    learning_rate: float = 0.001
):
    """
    Обучает модель распознавания цифр.
    
    Args:
        data_dir: директория с данными (подпапки 0-9)
        output_path: путь для сохранения весов
        epochs: количество эпох
        batch_size: размер батча
        learning_rate: скорость обучения
    """
    # Создаем датасет
    train_dataset = DigitDataset(data_dir, augment=True)
    
    if len(train_dataset) == 0:
        raise ValueError(f"Не найдено данных в {data_dir}")
    
    # Разделяем на train/val
    train_size = int(0.8 * len(train_dataset))
    val_size = len(train_dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        train_dataset, [train_size, val_size]
    )
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # Создаем модель
    from app.src.services.snils.digit_model import DigitCNN
    model = DigitCNN(num_classes=10)
    
    # Loss и optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    print(f"Обучение на устройстве: {device}")
    print(f"Размер обучающей выборки: {train_size}, валидационной: {val_size}")
    
    best_val_acc = 0.0
    
    for epoch in range(epochs):
        # Обучение
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()
        
        # Валидация
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        train_acc = 100 * train_correct / train_total
        val_acc = 100 * val_correct / val_total
        
        print(f"Epoch {epoch+1}/{epochs}:")
        print(f"  Train Loss: {train_loss/len(train_loader):.4f}, Acc: {train_acc:.2f}%")
        print(f"  Val Loss: {val_loss/len(val_loader):.4f}, Acc: {val_acc:.2f}%")
        
        # Сохраняем лучшую модель
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            torch.save(model.state_dict(), output_path)
            print(f"  Сохранена лучшая модель (val_acc: {val_acc:.2f}%)")
        
        scheduler.step()
    
    print(f"\nОбучение завершено. Лучшая точность: {best_val_acc:.2f}%")
    print(f"Модель сохранена в: {output_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Использование: python train_digits.py <data_dir> <output_path> [epochs] [batch_size]")
        print("Пример: python train_digits.py training/data/raw weights/snils_digits.pt 50 32")
        sys.exit(1)
    
    data_dir = sys.argv[1]
    output_path = sys.argv[2]
    epochs = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    batch_size = int(sys.argv[4]) if len(sys.argv) > 4 else 32
    
    train_model(data_dir, output_path, epochs=epochs, batch_size=batch_size)

