"""WebSocket роутер для отслеживания статуса задач"""
import os
import sys
import json
import logging
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Добавляем корень проекта в sys.path
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

import storage.db as db_module
from storage.models import UserDB, MLTaskDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])


def get_db():
    """Dependency для получения сессии БД"""
    # Используем SessionLocal из модуля динамически, чтобы он обновлялся в тестах
    db = db_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def verify_websocket_token(websocket: WebSocket, db: Session) -> UserDB:
    """Проверка токена через WebSocket"""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")
    
    from ..services.auth import verify_token
    try:
        token_data = verify_token(token)
        user = db.query(UserDB).filter(UserDB.email == token_data.email).first()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.websocket("/predictions/{task_id}")
async def websocket_task_status(websocket: WebSocket, task_id: int):
    """WebSocket для отслеживания статуса задачи"""
    await websocket.accept()
    
    db = SessionLocal()
    try:
        # Проверяем токен
        user = await verify_websocket_token(websocket, db)
        
        # Проверяем существование задачи и права доступа
        task = db.query(MLTaskDB).filter(MLTaskDB.id == task_id).first()
        if not task:
            await websocket.send_json({
                "error": "Task not found",
                "task_id": task_id,
            })
            await websocket.close()
            return
        
        if task.user_id != user.id:
            await websocket.send_json({
                "error": "Access denied",
                "task_id": task_id,
            })
            await websocket.close()
            return
        
        # Отправляем начальный статус
        await websocket.send_json({
            "task_id": task.id,
            "status": task.status,
            "prediction": float(task.prediction) if task.prediction is not None else None,
            "error_message": task.error_message,
            "credits_charged": task.credits_charged,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        })
        
        # Отслеживаем изменения статуса
        last_status = task.status
        while True:
            try:
                # Обновляем задачу из БД
                db.refresh(task)
                
                # Если статус изменился, отправляем обновление
                if task.status != last_status:
                    last_status = task.status
                    await websocket.send_json({
                        "task_id": task.id,
                        "status": task.status,
                        "prediction": float(task.prediction) if task.prediction is not None else None,
                        "error_message": task.error_message,
                        "credits_charged": task.credits_charged,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                    })
                    
                    # Если задача завершена (done или failed), закрываем соединение
                    if task.status in ("done", "failed"):
                        await websocket.close()
                        break
                
                # Проверяем, не закрыл ли клиент соединение
                try:
                    data = await websocket.receive_text()
                    # Клиент может отправить ping
                    if data == "ping":
                        await websocket.send_text("pong")
                except:
                    # Соединение закрыто клиентом
                    break
                
                # Небольшая задержка перед следующей проверкой
                import asyncio
                await asyncio.sleep(1)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for task {task_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket for task {task_id}: {e}")
                await websocket.send_json({
                    "error": str(e),
                    "task_id": task_id,
                })
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
    finally:
        db.close()

