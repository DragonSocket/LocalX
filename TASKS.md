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

## Следующие шаги
- [ ] pytest-покрытие (config migration, envelope parse, history flush, reconnect logic).
- [ ] `peers`-команда: реальный список подключённых peer'ов из handshake.
- [ ] Улучшение UI-ready детекции в e2e (ANSI-шум в потоке).
