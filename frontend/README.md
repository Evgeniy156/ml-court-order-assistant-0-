# ML Court Order Assistant - Frontend

Веб-интерфейс для ML-сервиса предсказания судебных приказов.

## Технологии

- React 18
- TypeScript
- Vite
- Ant Design
- React Router
- Axios

## Установка и запуск

### Разработка

```bash
# Установить зависимости
npm install

# Запустить dev-сервер
npm run dev
```

Приложение будет доступно по адресу `http://localhost:3000`

### Сборка для продакшена

```bash
# Собрать проект
npm run build

# Предпросмотр продакшен-сборки
npm run preview
```

Собранные файлы будут в папке `dist/`

## Переменные окружения

Создайте файл `.env` в корне проекта:

```env
VITE_API_URL=http://localhost:8000
```

## Структура проекта

```
frontend/
├── src/
│   ├── components/      # Переиспользуемые компоненты
│   ├── contexts/        # React контексты (Auth)
│   ├── pages/          # Страницы приложения
│   ├── services/       # API сервисы
│   ├── App.tsx         # Главный компонент
│   └── main.tsx        # Точка входа
├── public/             # Статические файлы
├── index.html          # HTML шаблон
└── vite.config.ts      # Конфигурация Vite
```

## Основные страницы

- `/login` - Авторизация/регистрация
- `/dashboard` - Дашборд с балансом и статистикой
- `/payment` - Пополнение баланса
- `/upload` - Загрузка CSV файлов для ML-предсказаний
- `/history` - История транзакций

## API интеграция

Все API запросы идут через сервис `src/services/api.ts`:
- `authService` - авторизация
- `billingService` - биллинг
- `webService` - веб-интерфейс
- `WebSocketClient` - WebSocket для отслеживания задач

