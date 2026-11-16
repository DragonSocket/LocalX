#!/usr/bin/fish

# Файл с задачей
set CMD_FILE "command.txt"

if not test -f $CMD_FILE
    echo "❌ Ошибка: Файл $CMD_FILE не найден!"
    exit 1
end

set TASK (cat $CMD_FILE)

echo "🚀 Запуск агента через opencode..."
echo "📖 Контекст: SPEC.md, TASKS.md, INSTRUCTIONS.md"
echo "--------------------------------------------"

# Формируем объединенный промпт
set CONTEXT_PROMPT (cat SPEC.md TASKS.md INSTRUCTIONS.md)

# Добавляем инструкцию по соблюдению границ задачи (Scope Lockdown)
set SCOPE_INSTRUCTION "\n\n⚠️ СТРОГОЕ ПРАВИЛО (SCOPE LOCKDOWN):\nВыполняй ТОЛЬКО то, что прямо указано в 'NEW TASK'. \nЗапрещено реализовывать UI, контроллеры или другие слои, если они не являются частью текущей задачи. \nЕсли задача требует изменений вне её границ — остановись и сообщи об этом."

# Выполняем реальный вызов opencode
opencode run -m ollama/qwen3.5:9b "$CONTEXT_PROMPT$SCOPE_INSTRUCTION\n\n--- NEW TASK ---\n$TASK"

if test $status -ne 0
    echo "--------------------------------------------"
    echo "❌ Ошибка при выполнении команды."
end
