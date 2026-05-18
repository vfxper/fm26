# Transfer System — Tasks

- [ ] 1. Database schema
  - [ ] 1.1 Add `transfer_offers` table to `run_local.py create_tables()`
  - [ ] 1.2 Add `agents` table to `run_local.py create_tables()`
  - [ ] 1.3 Extend existing `transfers` table with `loan_type`, `loan_buyback_fee`, `loan_buyback_mandatory`, `agent_fee`, `sell_on_pct` columns (lazy ALTER on first use)
  - [ ] 1.4 Seed `agents` rows for all CSV players (random greed/patience/commission)

- [ ] 2. Core engine
  - [ ] 2.1 Create `app/services/transfer_engine.py` with `TransferEngine` class
  - [ ] 2.2 Implement `submit_offer(career_id, player_id, fee, wage, years, role, sell_on_pct)`
  - [ ] 2.3 Implement `WindowGuard.is_open(date)` and `days_until_close(date)`
  - [ ] 2.4 Implement `AgentNegotiator.propose_round(offer, agent)`
  - [ ] 2.5 Implement `compute_market_appeal(player, club)`
  - [ ] 2.6 Implement `close_deal(offer)` — finance updates, squad swap, log row
  - [ ] 2.7 Property test: window guard correctness
  - [ ] 2.8 Property test: closed deals never break finance invariants

- [ ] 3. AI scan & response
  - [ ] 3.1 Implement `schedule_ai_scan(career_id)` triggered weekly from `advance_day`
  - [ ] 3.2 Implement `generate_random_offer(player, ai_club)` — used during scan
  - [ ] 3.3 Implement deferred response queue: process pending offers whose `response_due <= today`
  - [ ] 3.4 Hook scan + response into `app/api/routes/careers.py advance_day`
  - [ ] 3.5 Property test: scan probability bounded in [0,1] for any player/club pair

- [ ] 4. API routes
  - [ ] 4.1 Create `app/api/routes/transfers.py` with router
  - [ ] 4.2 `POST /careers/{cid}/transfers/offer` — submit offer
  - [ ] 4.3 `POST /careers/{cid}/transfers/respond` — accept/reject/counter on incoming
  - [ ] 4.4 `POST /careers/{cid}/transfers/loan` — submit loan (with buyback fields)
  - [ ] 4.5 `GET /careers/{cid}/transfers/outgoing`
  - [ ] 4.6 `GET /careers/{cid}/transfers/incoming`
  - [ ] 4.7 `POST /careers/{cid}/transfers/bulk` — `{action: accept|reject|improve, ids: [...]}`
  - [ ] 4.8 `POST /careers/{cid}/transfers/agent-talk` — single negotiation round
  - [ ] 4.9 `GET /careers/{cid}/transfers/window`
  - [ ] 4.10 Register router in `app/api/routes/__init__.py`

- [ ] 5. Inbox integration
  - [ ] 5.1 Push `transfer_out` on submit_offer
  - [ ] 5.2 Push `transfer_in` on incoming offer creation
  - [ ] 5.3 Push `transfer_done` / `transfer_rejected` / `transfer_counter` on response
  - [ ] 5.4 Push `transfer_window` 7 days before window close

- [ ] 6. Frontend
  - [ ] 6.1 Add `screen-transfers` markup to `frontend/index.html` with three tabs
  - [ ] 6.2 Add SVG icon and sidebar nav entry `nav-transfers`
  - [ ] 6.3 Implement offer modal (form: fee, wage, years, role, sell-on, loan toggle)
  - [ ] 6.4 Implement agent talk modal (round counter + slider)
  - [ ] 6.5 Implement bulk actions bar with checkboxes
  - [ ] 6.6 Wire `loadTransfersOutgoing()`, `loadTransfersIncoming()`, `loadTransfersListed()`
  - [ ] 6.7 Add badge "Новых офферов: N" on home screen
  - [ ] 6.8 Add `data-transfer-id` row click → opens offer detail panel

- [ ] 7. Loans
  - [ ] 7.1 Implement loan submission path with `mandatory_buyback` / `optional_buyback` types
  - [ ] 7.2 Add `loan_until` automatic expiry watchdog in advance_day (returns player to parent on expiry)
  - [ ] 7.3 Trigger mandatory buyback when conditions met (matches/goals)
  - [ ] 7.4 Optional buyback button shown to parent club for 1 year window

- [ ] 8. Validation rules
  - [ ] 8.1 Reject offer when window closed
  - [ ] 8.2 Reject offer when buyer budget insufficient
  - [ ] 8.3 Reject when player <16 (academy-only)
  - [ ] 8.4 Cap simultaneous transfer-listed players at 5 (board confidence gate)
  - [ ] 8.5 Property test: validation always raises 400 (never 500) on bad input

- [ ] 9. Documentation & smoke test
  - [ ] 9.1 Add a `python -m pytest -k transfer` smoke run
  - [ ] 9.2 Update `frontend/index.html` README block / inline comment with the new flow
  - [ ] 9.3 Add a few seeded examples to `seed_local.py` (so a fresh DB has 3-5 sample agents)
