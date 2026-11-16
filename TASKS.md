# TASKS.md — статус проекта localX

## Выполнено
- [x] `src/core/config.py` — схема `[node]/[local]/[remote]/[storage]`, миграция legacy `[connection]`, env-override `LOCALX_*`.
- [x] `src/core/network.py` — P2P dual-mode движок: listener `ncat -l -k` + connector с авто-реconnect, envelope-протокол, self-echo suppression, handshake `kind="hello"`, корректный teardown (setpgrp/killpg).
- [x] `src/core/history.py` — JSONL-персистентность, locks, батчи.
- [x] `src/ui/tui.py` — `ChatTUI` на prompt_toolkit: bounded transcript (1000 строк), статус-строка, Enter/Ctrl+C/Ctrl+D.
- [x] `src/main.py` — оркестратор: `/exit`, `/help`, `/status`, `/peers`, `/history [n]`, consumer входящих, error-reporter, guarded shutdown.
- [x] `config.toml` — новая схема (alice/9001 ↔ 9002).
- [x] `pyproject.toml` — deps: prompt-toolkit, portalocker, pydantic; `uv sync` воспроизводим.
- [x] `README.md` — описание реального P2P-поведения, таблица env-переменных, инструкция запуска двух пиров.
- [x] `scripts/smoke_p2p.py` — тест движка: **SMOKE TEST OK**.
- [x] `scripts/e2e_two_peers.py` — pty-тест двух UI-пиров: **E2E OK** (alice↔bob обмениваются сообщениями, exit-путь чистый, exit code 0).
- [x] Скроллинг транскрипта: PageUp/PageDown, Ctrl+Home/End, маркер `... N line(s) above (PageUp)` — подтверждено pyte-пробой (30 сообщений, 41 над экраном).
- [x] Offline-queue: сообщения в `_outbox` (max 200), флеш при reconnect — **`scripts/reconnect_test.py`: RECONNECT/OUTBOX TEST OK**.
- [x] Hang на `/exit` устранён: 30+ сообщений → exit code 0 за 1 с, history полностью flush'ится.
- [x] `tests/` — pytest: config (migration/env/валидация), envelope, history (deadlock-fix, батчи, shutdown). **15 passed**.
- [x] Колесо мыши: SGR-нотчи (`\x1b[<4/5;..M`) транслируются в `Ctrl+Up/Down` через патч `KeyProcessor.feed_multiple` — скроллит в любой точке экрана. `scripts/scroll_probe.py`: **SCROLL PROBE OK** (24x80 и 12x40).
- [x] Статус-строка: в узких терминалах имя peer'а уходит первым, индикатор `[↑ N]` / счётчик unread не обрезается.
- [x] Полный аудит логики приложения: `AUDIT.md` — 4 проблемы высокой критичности (`_max_scroll` off-by-one, смерть incoming-consumer при ошибке истории, stale `_known_peers`/`peer_online`, обрезка буфера без корректировки `_scroll`), 7 средних, 8 мелких.
- [x] Все 19 пунктов аудита исправлены: честный `_peers_by_source` (peer забывается вместе со stream'ом), exponential backoff reconnect, line-by-line `_flush_outbox` с сохранением хвоста, повторный flush перед каждым send, outbox drop-oldest, drain- grace для `_read_stream` при остановке, `LOG_FILE`/`config.toml` резолвятся от проекта, уникальный дефолт `peer_id = USER-pid`, warning на self-echo, удаление мёртвого кода (`NetworkProcessError`, `_error_event`). Тесты: `tests/test_network_peers.py` — **25 passed**.

## Следующие шаги
- [ ] Улучшение UI-ready детекции в e2e (ANSI-шум в потоке).
