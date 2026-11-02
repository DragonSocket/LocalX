#!/usr/bin/fish

# Файл с задачей
set CMD_FILE "command.txt"

if not test -f $CMD_FILE
    echo "❌ Ошибка: Файл $CMD_FILE не найден!"
    exit 1
end

set TASK (cat $CMD_FILE)

echo "🚀 Запуск агента qwen3.5..."
echo "📖 Контекст: SPEC.md, TASKS.md, INSTRUCTIONS.md"
echo "--------------------------------------------"

# Мы формируем объединенный промпт, чтобы агент получил всё сразу.
set CONTEXT_PROMPT (cat SPEC.md TASKS.md INSTRUCTIONS.md)

# Выполняем команду. 
# ВАЖНО: Замени 'qwen3.5' на актуальную команду для запуска твоего агента.
echo -e "$CONTEXT_PROMPT\n\n--- NEW TASK ---\n$TASK" | qwen3.5

if test $status -ne 0
    echo "--------------------------------------------"
    echo "❌ Ошибка при выполнении команды."
end
