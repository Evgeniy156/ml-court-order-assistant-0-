# Скрипт для коммита и пуша фикса тестов
# Выполните в директории проекта, где вы уже находитесь

Write-Host "=== Коммит и push фикса тестов ===" -ForegroundColor Cyan

# Проверка ветки
Write-Host "`nТекущая ветка:" -ForegroundColor Yellow
git branch

# Проверка изменений
Write-Host "`nСтатус tests/conftest.py:" -ForegroundColor Yellow
git status tests/conftest.py

# Добавление файла
Write-Host "`nДобавление файла..." -ForegroundColor Yellow
git add tests/conftest.py

# Коммит
Write-Host "`nСоздание коммита..." -ForegroundColor Yellow
git commit -m "Fix CI tests: writable sqlite path + recreate engine in fixtures"

# Push
Write-Host "`nPush в origin/safe-public-release..." -ForegroundColor Yellow
git push origin safe-public-release

Write-Host "`n✓ Готово! Проверьте PR #14 на GitHub" -ForegroundColor Green

