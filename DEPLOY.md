# Деплой FM26 на бесплатный хостинг

Цель: 20 пользователей одновременно, каждый со своими данными.
Стек: backend на **Render.com**, frontend на **GitHub Pages**.
Стоимость: **0 рублей**.

## 1. Backend → Render

### Шаг 1.1. Создай GitHub репозиторий

```bash
cd C:\Users\sin3\Documents\fm26\fm26
git init
git add -A
git commit -m "FM26 initial deploy"
```

Зайди на https://github.com → New repository → `fm26` → создай.

```bash
git remote add origin https://github.com/ТВОЁ_ИМЯ/fm26.git
git push -u origin main
```

### Шаг 1.2. Подключи Render

1. Иди на https://render.com → Sign up через GitHub
2. **New → Web Service** → выбери репозиторий `fm26`
3. Настройки:
   - **Name**: `fm26-backend`
   - **Region**: `Frankfurt` (или ближайший)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run_local.py`
   - **Plan**: `Free`
4. **Create Web Service**

Render автоматически подхватит `render.yaml` и начнёт билд (~5 минут).

### Шаг 1.3. Сидинг базы

После первого деплоя БД пустая — нужно загрузить игроков и клубы.
В Render: **Shell** → запусти:

```
python seed_local.py
```

Готово. Получишь URL вида `https://fm26-backend.onrender.com`.

> ⚠️ Бесплатный план Render засыпает через 15 мин простоя.
> Первый запрос после сна занимает ~30 секунд. Это нормально.

## 2. Frontend → GitHub Pages

### Шаг 2.1. Подготовь HTML

Открой `frontend/index.html` и найди в самом верху JS строку:

```js
const API = 'http://localhost:8000/api';
```

Замени на свой Render URL:

```js
const API = 'https://fm26-backend.onrender.com/api';
```

Закоммить:

```bash
git add frontend/index.html
git commit -m "Point frontend at Render"
git push
```

### Шаг 2.2. Включи GitHub Pages

1. На странице репозитория: **Settings → Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `main` / `/frontend`
4. **Save**

Через ~1 минуту твой `index.html` будет доступен по адресу
`https://ТВОЁ_ИМЯ.github.io/fm26/`.

## 3. Что получают пользователи

- Заходят по ссылке `https://ТВОЁ_ИМЯ.github.io/fm26/`
- На auth-экране: «Регистрация» → email + пароль
- Каждый получает отдельный `user_id` и СВОЮ карьеру
- Карьеры других пользователей не видны

## 4. Тест multi-user

Проверь так:
1. Зарегистрируйся в Chrome: `alice@test.com` / `password123`, создай карьеру за Real Madrid
2. Открой Firefox, зарегистрируйся: `bob@test.com` / `password123`, создай карьеру за Barcelona
3. У alice не должно быть видно карьеры bob и наоборот

## 5. Что дальше

- Отслеживай нагрузку: Render Dashboard → Metrics
- Если 20+ юзеров одновременно тормозят → переходи на платный план Starter ($7/мес)
- Бэкап БД: Render Dashboard → Disks (на платном плане)
- Кастомный домен: Settings → Custom Domain (бесплатно)

## 6. Известные ограничения бесплатного плана

| Что | Лимит | Решение |
|---|---|---|
| Засыпание после 15 мин | Первый запрос ~30 с | Купи Starter $7/мес |
| 750 ч/мес запуска | ~24 дня x 24 часа | Хватит на 1 сервис |
| 512 MB RAM | До 30-50 одновременных пользователей | Достаточно для 20 |
| Эпhemeral disk | БД стирается при рестарте | Используй Postgres add-on |

> 🛑 ВАЖНО: на бесплатном Render файлы могут пропасть при рестарте.
> Для production используй **Render Postgres free tier** (1GB) и
> поменяй `DATABASE_URL` в env vars.
