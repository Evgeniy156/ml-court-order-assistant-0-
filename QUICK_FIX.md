# Исправление импортов

## Проблема
Ошибка: `ModuleNotFoundError: No module named 'app.src.services.utils'`

## Решение
Исправлены импорты в:
- `app/src/services/snils/decode.py`: `from ...utils.snils_checksum import snils_checksum_ok`
- `app/src/services/snils/pipeline.py`: `from ...utils.snils_checksum import format_snils`

## Проверка

Запустите из корня проекта:

```powershell
pytest tests/test_snils_api.py -v
```

Или запустите API:

```powershell
uvicorn app.src.main:app --host 0.0.0.0 --port 8000
```

## Для PowerShell curl

В PowerShell используйте `Invoke-WebRequest` вместо `curl`:

```powershell
# Health check
Invoke-WebRequest -Uri http://localhost:8000/health

# Распознавание
$filePath = "tests/assets_local/snils2.jpg"
$form = @{
    file = Get-Item -Path $filePath
}
Invoke-WebRequest -Uri http://localhost:8000/snils/recognize -Method Post -Form $form
```

Или используйте `curl.exe` (полный путь):

```powershell
curl.exe -X POST http://localhost:8000/snils/recognize -F "file=@tests/assets_local/snils2.jpg"
```

