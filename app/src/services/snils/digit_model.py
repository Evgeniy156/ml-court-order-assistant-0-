"""
Torch CNN модель для распознавания цифр 0-9.
Singleton для загрузки модели один раз.
"""
import os
import torch
import torch.nn as nn
import numpy as np
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Singleton instance
_model_instance: Optional['DigitCNN'] = None


class DigitCNN(nn.Module):
    """CNN для классификации цифр 0-9."""
    
    def __init__(self, num_classes: int = 10):
        super(DigitCNN, self).__init__()
        
        # Conv layers
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.relu1 = nn.ReLU()
        self.pool1 = nn.MaxPool2d(2, 2)
        
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.relu2 = nn.ReLU()
        self.pool2 = nn.MaxPool2d(2, 2)
        
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.relu3 = nn.ReLU()
        self.pool3 = nn.MaxPool2d(2, 2)
        
        # FC layers
        # После 3 pool (32 -> 16 -> 8 -> 4), размер 4x4
        self.fc1 = nn.Linear(128 * 4 * 4, 256)
        self.relu4 = nn.ReLU()
        self.dropout = nn.Dropout(0.5)
        self.fc2 = nn.Linear(256, num_classes)
    
    def forward(self, x):
        x = self.pool1(self.relu1(self.conv1(x)))
        x = self.pool2(self.relu2(self.conv2(x)))
        x = self.pool3(self.relu3(self.conv3(x)))
        x = x.view(x.size(0), -1)
        x = self.dropout(self.relu4(self.fc1(x)))
        x = self.fc2(x)
        return x


def get_model() -> DigitCNN:
    """
    Получает singleton экземпляр модели.
    Загружает веса из weights/snils_digits.pt если доступны.
    
    Returns:
        Загруженная модель
        
    Raises:
        FileNotFoundError: если веса не найдены
    """
    global _model_instance
    
    if _model_instance is not None:
        return _model_instance
    
    # Определяем путь к весам
    # Пробуем несколько вариантов
    possible_paths = [
        "weights/snils_digits.pt",
        "app/weights/snils_digits.pt",
        os.path.join(os.path.dirname(__file__), "../../../weights/snils_digits.pt"),
    ]
    
    weights_path = None
    for path in possible_paths:
        if os.path.exists(path):
            weights_path = path
            break
    
    if weights_path is None:
        # Пробуем найти относительно корня проекта
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
        weights_path = os.path.join(project_root, "weights", "snils_digits.pt")
        
        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Digit model weights not found. "
                f"Expected at: {weights_path}. "
                f"Please train the model first using training/train_digits.py"
            )
    
    # Создаем модель
    model = DigitCNN(num_classes=10)
    
    # Загружаем веса
    device = torch.device("cpu")  # Используем CPU по умолчанию
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.eval()
    
    _model_instance = model
    logger.info(f"Loaded digit model from {weights_path}")
    
    return model


def predict_proba(cells: List[np.ndarray], topk: int = 3) -> List[List[dict]]:
    """
    Предсказывает вероятности для каждой клетки.
    
    Args:
        cells: список нормализованных изображений клеток (32x32 grayscale)
        topk: количество лучших кандидатов для каждой клетки
        
    Returns:
        Список списков словарей: для каждой клетки topk результатов
        [{"digit": 0-9, "p": probability}, ...]
    """
    model = get_model()
    device = torch.device("cpu")
    
    # Подготовка батча
    batch = []
    for cell in cells:
        # Нормализуем в [0, 1]
        cell_norm = cell.astype(np.float32) / 255.0
        # Добавляем channel dimension
        cell_tensor = torch.from_numpy(cell_norm).unsqueeze(0)  # (1, 32, 32)
        batch.append(cell_tensor)
    
    batch_tensor = torch.stack(batch).unsqueeze(1)  # (N, 1, 32, 32)
    batch_tensor = batch_tensor.to(device)
    
    # Предсказание
    with torch.no_grad():
        logits = model(batch_tensor)  # (N, 10)
        probs = torch.softmax(logits, dim=1)  # (N, 10)
    
    # Извлекаем topk для каждой клетки
    results = []
    for i in range(len(cells)):
        cell_probs = probs[i].cpu().numpy()
        topk_indices = np.argsort(cell_probs)[::-1][:topk]
        
        cell_results = []
        for idx in topk_indices:
            cell_results.append({
                "digit": int(idx),
                "p": float(cell_probs[idx])
            })
        results.append(cell_results)
    
    return results

