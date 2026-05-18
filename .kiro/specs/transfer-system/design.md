# Transfer System — Design

## Архитектура

```
frontend/index.html
  ├ screen-transfers
  │   ├ tab: «Мои предложения»  → GET /transfers/outgoing
  │   ├ tab: «Входящие»          → GET /transfers/incoming
  │   └ tab: «Списки»            → GET /squad (uses is_transfer_listed)
  │
  └ JS: transfersModule.js (offer modal, agent modal, bulk actions)

app/api/routes/transfers.py
  ├ POST   /careers/{cid}/transfers/offer          → подать оффер чужому игроку
  ├ POST   /careers/{cid}/transfers/respond        → ответить на оффер
  ├ POST   /careers/{cid}/transfers/loan           → подать аренду
  ├ GET    /careers/{cid}/transfers/outgoing       → список моих офферов
  ├ GET    /careers/{cid}/transfers/incoming       → список офферов мне
  ├ POST   /careers/{cid}/transfers/bulk           → bulk-accept/reject
  ├ POST   /careers/{cid}/transfers/agent-talk     → раунд переговоров с агентом
  ├ GET    /careers/{cid}/transfers/window         → текущий статус окна
  └ POST   /careers/{cid}/transfers/scan-tick      → ИИ-скан рынка (cron-like)

app/services/transfer_engine.py
  ├ class TransferEngine
  │   ├ submit_offer(career, player, fee, wage, years)
  │   ├ ai_respond(offer)             — детерм по seed = player_id*career_id
  │   ├ schedule_ai_scan(career_id)   — раз в 7 дней
  │   ├ generate_random_offer(player) — для is_transfer_listed=1
  │   └ close_deal(offer)             — финансы + лог + инбокс
  │
  ├ class AgentNegotiator
  │   ├ propose_round(offer, agent)   — возвращает контр-предложение
  │   └ converged?(offer)             — агент согласен на эту зарплату?
  │
  └ class WindowGuard
      ├ is_open(date) -> bool
      └ days_until_close(date) -> int

app/models (SQLAlchemy ORM)
  ├ TransferOffer    (transfers + offers слиты в одну таблицу)
  ├ Agent            (per-player attrs)
  └ TransferDealLog
```

## Схема БД

### `transfer_offers`

| Поле | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| career_id | INTEGER NOT NULL | карьера-покупатель ИЛИ карьера-продавец |
| direction | VARCHAR(10) | `outgoing` / `incoming` |
| player_id | INTEGER | целевой игрок |
| from_club_id | INTEGER | клуб-продавец |
| to_club_id | INTEGER | клуб-покупатель |
| fee | INTEGER | базовая сумма £ |
| wage | INTEGER | предлагаемая зарплата £/нед |
| contract_years | INTEGER | 1-5 |
| role | VARCHAR(20) | key/first/rotation/backup/youth |
| sell_on_pct | INTEGER | % перепродажи 0-25 |
| loan_type | VARCHAR(20) NULLABLE | `simple` / `mandatory_buyback` / `optional_buyback` |
| loan_buyback_fee | INTEGER NULLABLE | |
| loan_until | DATE NULLABLE | конец аренды |
| status | VARCHAR(20) | `pending` / `accepted` / `rejected` / `counter` / `expired` |
| counter_fee | INTEGER NULLABLE | контр-предложение |
| counter_wage | INTEGER NULLABLE | |
| counter_deadline | DATE NULLABLE | до какой даты ответить |
| created_date | VARCHAR(10) | |
| resolved_date | VARCHAR(10) NULLABLE | |
| created_at | DATETIME | server_default=now |

### `agents`

| Поле | Тип |
|---|---|
| player_id | INTEGER PK |
| name | VARCHAR(80) |
| greed | INTEGER 1-20 |
| patience | INTEGER 1-20 |
| commission_pct | INTEGER 5-10 |

### `transfers` (история закрытых сделок — уже есть)

Расширим столбцами `loan_type`, `loan_buyback_fee`,
`loan_buyback_mandatory`, `agent_fee`, `sell_on_pct`.

## Поток данных

### 1. Игрок подаёт оффер чужому игроку

```
[Frontend] modal -> POST /transfers/offer
   { player_id, fee, wage, contract_years, role, sell_on_pct }

[Backend]
   1. WindowGuard.is_open() ? иначе 400
   2. Проверка бюджета: budget >= fee + commission ? иначе 400
   3. INSERT transfer_offers (direction=outgoing, status=pending)
   4. push_inbox_message(category='transfer_out', ...)
   5. Schedule AI response after random(1-7) days
```

### 2. ИИ-клуб отвечает (cron / advance_day hook)

```
[advance_day]
   for offer in pending offers where response_due <= today:
      decision = AgentNegotiator.evaluate(offer)
      if accept:
         offer.status = 'accepted'
         close_deal(offer)
      elif counter:
         offer.status = 'counter'
         offer.counter_fee, offer.counter_wage, offer.counter_deadline
      else:
         offer.status = 'rejected'
      push_inbox_message(category='transfer_response', ...)
```

### 3. ИИ-клуб шлёт оффер на моего листированного игрока

```
[scan_tick] (раз в 7 дней внутри advance_day)
   listed = SELECT * FROM squad_players WHERE is_transfer_listed=1
   for sp in listed:
      probability = compute_market_appeal(sp, all_ai_clubs)
      if random() < probability:
         offer = generate_random_offer(sp)
         INSERT transfer_offers (direction=incoming, status=pending)
         push_inbox_message(category='transfer_in', ...)
```

### 4. Закрытие сделки

```
close_deal(offer):
   commission = offer.fee * (agent.commission_pct/100)
   buyer_budget -= (offer.fee + commission)
   seller_budget += offer.fee
   INSERT transfers (...)
   if direction=outgoing:
      DELETE squad_players WHERE career_id=seller AND player_id=...
      INSERT squad_players (career_id=buyer, player_id=..., contract_*)
   push_inbox_message(category='transfer_done', ...)
```

## Алгоритмы

### `compute_market_appeal(player, club)`
```
appeal = 0.5
appeal += (club.reputation - player_club.reputation) * 0.02
appeal += positional_need(club, player.position) * 0.3
appeal -= (player.wage / club.wage_budget) * 0.4
appeal *= window_open_factor    # 1.0 в окне, 0.0 вне
return clamp(appeal, 0, 1)
```

### `AgentNegotiator.propose_round(offer, agent)`
```
demanded_wage = player.wage * (1 + agent.greed / 50)   # 1.02-1.40×
if offer.wage >= demanded_wage:
   return ACCEPT
elif offer.wage >= demanded_wage * 0.85:
   return COUNTER(wage=demanded_wage)
else:
   patience_left = agent.patience - rounds_held
   if patience_left <= 0: return REJECT
   else: return COUNTER(wage = (offer.wage + demanded_wage) / 2)
```

## UI

### Сайдбар иконка
```
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M3 7h18M3 12h18M3 17h18"/>
  <path d="M16 4l4 4-4 4"/>
  <path d="M8 13l-4 4 4 4"/>
</svg>
```

### Таблица "Исходящие"
```
| Игрок | Клуб | Сумма | Статус | Дедлайн | Действие |
| Mbappé | PSG | £50M | counter (£60M) | 26.07.2025 | [Принять] [Отказ] |
```

### Bulk-bar
```
[ ] выбрать всё   [ Принять выбранные ]   [ Отклонить ]   [ Запросить улучшение ]
```

## Пуши в инбокс

| Триггер | Категория | Subject |
|---|---|---|
| подал оффер | `transfer_out` | "Предложение по {player} отправлено" |
| ИИ принял | `transfer_done` | "{player} переходит в {club}!" |
| ИИ отклонил | `transfer_rejected` | "{player}: предложение отклонено" |
| ИИ контр-оффер | `transfer_counter` | "Контр-предложение по {player}" |
| ИИ прислал оффер | `transfer_in` | "Предложение по {player} (£{fee})" |
| Сделка закрыта | `transfer_done` | "{player} → {to_club} за £{fee}" |
| Окно закрылось | `transfer_window` | "Трансферное окно закрыто" |

## Ограничения первой итерации

— Без 3D визуала и интерактивной анимации.  
— Без переговоров с самим игроком (только через агента).  
— Boards/sponsors не реагируют на сделки в этой итерации.
