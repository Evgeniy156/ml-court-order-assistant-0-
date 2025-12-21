"""
Скрипт для нарезки клеток из изображений для ручной сортировки.
"""
import cv2
import numpy as np
import os
from pathlib import Path
from typing import List, Tuple

from app.src.services.snils.grid_detect import detect_snils_rows
from app.src.services.snils.cut_cells import cut_row_cells, normalize_cell


def extract_cells_from_image(image_path: str, output_dir: str) -> int:
    """
    Извлекает клетки из изображения и сохраняет для ручной сортировки.
    
    Args:
        image_path: путь к изображению
        output_dir: директория для сохранения клеток
        
    Returns:
        Количество извлеченных клеток
    """
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        print(f"Не удалось загрузить изображение: {image_path}")
        return 0
    
    # Детектируем строки
    rows, _ = detect_snils_rows(image_bgr, debug=False)
    
    if not rows:
        print(f"Не найдено строк на изображении: {image_path}")
        return 0
    
    # Создаем директории для каждой цифры
    for digit in range(10):
        os.makedirs(os.path.join(output_dir, str(digit)), exist_ok=True)
    
    count = 0
    for row_idx, row_cells in enumerate(rows):
        try:
            # Нарезаем клетки
            normalized_cells = cut_row_cells(row_cells, image_bgr)
            
            # Сохраняем каждую клетку
            for cell_idx, cell_img in enumerate(normalized_cells):
                # Сохраняем в папку для ручной сортировки
                output_path = os.path.join(output_dir, f"row{row_idx}_cell{cell_idx}.png")
                cv2.imwrite(output_path, cell_img)
                count += 1
        except Exception as e:
            print(f"Ошибка при обработке строки {row_idx}: {e}")
    
    print(f"Извлечено {count} клеток из {image_path}")
    return count


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Использование: python dataset_build.py <image_path> <output_dir>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    os.makedirs(output_dir, exist_ok=True)
    extract_cells_from_image(image_path, output_dir)

