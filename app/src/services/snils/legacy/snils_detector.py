"""
Улучшенный детектор строк СНИЛС на изображении.
Использует QR-коды как якорь, с fallback на контурный детектор.
LEGACY: сохранен для совместимости.
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

# ... existing code ...

