"""
Роутер для распознавания СНИЛС по фото/скану
"""
import os
import io
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

from ..services.snils.pipeline import run_snils_pipeline

router = APIRouter(prefix="/snils", tags=["SNILS"])

logger = logging.getLogger(__name__)

# Флаг для debug эндпоинтов
ENABLE_DEBUG_ENDPOINTS = os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true"


@router.get("/")
async def snils_root():
    """Проверка доступности роутера SNILS"""
    return {"status": "ok", "message": "SNILS router is working"}


@router.post("/recognize")
async def recognize_snils(file: UploadFile = File(...)):
    """
    Распознает СНИЛС на изображении.
    
    Принимает файл (multipart) и возвращает JSON с результатами.
    Не логирует bytes и распознанные цифры.
    """
    # Проверяем тип файла
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только JPG и PNG изображения"
        )
    
    # Читаем файл в память
    try:
        image_bytes = await file.read()
    except Exception as e:
        logger.error(f"Ошибка чтения файла: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка чтения файла: {str(e)}"
        )
    
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл пуст"
        )
    
    # Вызываем пайплайн распознавания
    try:
        result = run_snils_pipeline(image_bytes)
        return JSONResponse(content=result)
    except HTTPException:
        # Пробрасываем HTTPException дальше (например, 503 для отсутствия модели)
        raise
    except Exception as e:
        logger.error(f"Ошибка распознавания СНИЛС: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка распознавания: {str(e)}"
        )


@router.post("/recognize/debug")
async def recognize_snils_debug(file: UploadFile = File(...)):
    """
    Debug эндпоинт для распознавания СНИЛС.
    Возвращает bbox'ы и служебные данные.
    Доступен только если ENABLE_DEBUG_ENDPOINTS=true.
    НЕ возвращает исходное изображение и НЕ возвращает распознанные цифры.
    """
    if not ENABLE_DEBUG_ENDPOINTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug эндпоинт отключен"
        )
    
    # Проверяем тип файла
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только JPG и PNG изображения"
        )
    
    # Читаем файл
    try:
        image_bytes = await file.read()
    except Exception as e:
        logger.error(f"Ошибка чтения файла: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка чтения файла: {str(e)}"
        )
    
    # Вызываем пайплайн с debug=True
    try:
        result = run_snils_pipeline(image_bytes, debug=True)
        
        # Формируем debug ответ (без распознанных цифр)
        debug_data = {
            "angle": result.get("debug", {}).get("angle", 0.0),
            "method": result.get("debug", {}).get("method", "unknown"),
            "qr_count": result.get("debug", {}).get("qr_count", 0),
            "qr_boxes": result.get("debug", {}).get("qr_boxes", []),
            "rows_count": result.get("debug", {}).get("rows_count", 0),
            "image_size": result.get("debug", {}).get("preprocess", {}).get("original_size", [0, 0]),
            "warnings": result.get("warnings", []),
            "rows_boxes": []
        }
        
        # Добавляем bbox строк из debug информации
        rows_boxes = result.get("debug", {}).get("rows_boxes", [])
        debug_data["rows_boxes"] = rows_boxes
        
        return JSONResponse(content=debug_data)
    except HTTPException:
        # Пробрасываем HTTPException дальше (например, 503 для отсутствия модели)
        raise
    except Exception as e:
        logger.error(f"Ошибка debug распознавания: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка debug: {str(e)}"
        )

