# Скрипт для коммита и пуша фикса тестов
# Выполните этот скрипт в директории проекта

Write-Host "=== Коммит фикса тестов ===" -ForegroundColor Cyan

# Шаг 0 - Проверка ветки
Write-Host "`nШаг 0: Проверка текущей ветки..." -ForegroundColor Yellow
$currentBranch = git branch --show-current
Write-Host "Текущая ветка: $currentBranch" -ForegroundColor White

if ($currentBranch -ne "safe-public-release") {
    Write-Host "Переключение на ветку safe-public-release..." -ForegroundColor Yellow
    git switch safe-public-release 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Создание новой ветки safe-public-release..." -ForegroundColor Yellow
        git checkout -b safe-public-release 2>&1
    }
}

# Шаг 1 - Проверка изменений
Write-Host "`nШаг 1: Проверка изменений в tests/conftest.py..." -ForegroundColor Yellow
if (-not (Test-Path "tests\conftest.py")) {
    Write-Host "ОШИБКА: tests/conftest.py не найден!" -ForegroundColor Red
    Write-Host "Убедитесь, что вы находитесь в директории проекта" -ForegroundColor Red
    exit 1
}

git status tests/conftest.py
git diff tests/conftest.py | Select-Object -First 20

# Шаг 2 - Опциональный запуск тестов
Write-Host "`nШаг 2: Запуск тестов (опционально)..." -ForegroundColor Yellow
$runTests = Read-Host "Запустить тесты локально? (y/n)"
if ($runTests -eq "y" -or $runTests -eq "Y") {
    Write-Host "Запуск pytest..." -ForegroundColor Cyan
    pytest -q tests/test_api.py 2>&1
}

# Шаг 3 - Добавление и коммит
Write-Host "`nШаг 3: Добавление файла и коммит..." -ForegroundColor Yellow
git add tests/conftest.py
git status --short tests/conftest.py

$commitMessage = "Fix CI tests: writable sqlite path + recreate engine in fixtures"
Write-Host "Коммит с сообщением: $commitMessage" -ForegroundColor Cyan
git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    Write-Host "ОШИБКА: Не удалось создать коммит!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Коммит создан успешно" -ForegroundColor Green

# Шаг 4 - Push
Write-Host "`nШаг 4: Push в ветку safe-public-release..." -ForegroundColor Yellow
git push origin safe-public-release

if ($LASTEXITCODE -ne 0) {
    Write-Host "ОШИБКА: Не удалось запушить изменения!" -ForegroundColor Red
    Write-Host "Проверьте, что remote 'origin' настроен правильно" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✓ Изменения успешно запушены!" -ForegroundColor Green
Write-Host "Проверьте PR #14 на GitHub для подтверждения" -ForegroundColor Cyan

