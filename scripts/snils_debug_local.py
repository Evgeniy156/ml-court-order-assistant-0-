"""
Скрипт для локальной отладки детекции СНИЛС.
Читает все *.jpg/*.png из tests/assets_local/ и выводит статистику.
"""
import os
import sys
import glob
from pathlib import Path

# Добавляем путь к проекту
# Определяем корень проекта: ищем скрипт и поднимаемся на 2 уровня вверх
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent

# Если скрипт запущен не из корня, пытаемся найти корень по структуре
if not (_project_root / "app" / "src").exists():
    # Пробуем найти корень по наличию app/src
    possible_roots = [
        Path.cwd(),
        _current_file.parent.parent,
        Path.cwd().parent,
    ]
    for root in possible_roots:
        if (root / "app" / "src").exists():
            _project_root = root
            break

sys.path.insert(0, str(_project_root))

# Переходим в корень проекта для работы с относительными путями
try:
    os.chdir(_project_root)
except Exception:
    pass  # Если не удалось сменить директорию, продолжаем

from app.src.services.snils_pipeline import run_snils_pipeline


def main():
    """Основная функция"""
    assets_dir = _project_root / "tests" / "assets_local"
    
    if not assets_dir.exists():
        print(f"❌ Директория {assets_dir} не найдена")
        print("Создайте директорию и поместите туда тестовые изображения (JPG/PNG)")
        return
    
    # Ищем все изображения
    image_files = list(assets_dir.glob("*.jpg")) + list(assets_dir.glob("*.png"))
    image_files += list(assets_dir.glob("*.JPG")) + list(assets_dir.glob("*.PNG"))
    
    if not image_files:
        print(f"❌ Не найдено изображений в {assets_dir}")
        return
    
    print(f"Найдено {len(image_files)} изображений\n")
    print("=" * 80)
    
    for img_path in sorted(image_files):
        print(f"\n📄 Файл: {img_path.name}")
        print("-" * 80)
        
        try:
            # Читаем файл
            with open(img_path, "rb") as f:
                image_bytes = f.read()
            
            # Запускаем pipeline с debug
            result = run_snils_pipeline(image_bytes, debug=True)
            
            # Выводим статистику
            debug_info = result.get("debug", {})
            
            print(f"  Метод детекции: {debug_info.get('method', 'unknown')}")
            print(f"  Угол поворота: {debug_info.get('angle', 0.0):.2f}°")
            print(f"  QR-кодов найдено: {debug_info.get('qr_count', 0)}")
            print(f"  Строк найдено: {debug_info.get('rows_count', 0)}")
            print(f"  Распознано строк: {result.get('count', 0)}")
            
            # Предупреждения
            warnings = result.get("warnings", [])
            if warnings:
                print(f"  ⚠️  Предупреждения: {', '.join(warnings)}")
            
            # QR bbox
            qr_boxes = debug_info.get("qr_boxes", [])
            if qr_boxes:
                print(f"  QR bbox: {qr_boxes}")
            
            # Результаты распознавания (только количество, без цифр)
            if result.get("count", 0) > 0:
                for idx, row_result in enumerate(result.get("results", []), 1):
                    print(f"  Строка {idx}: checksum={row_result.get('is_valid_checksum')}, "
                          f"confidence={row_result.get('confidence', 0):.2%}")
            
        except Exception as e:
            print(f"  ❌ Ошибка: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Готово!")


if __name__ == "__main__":
    main()

