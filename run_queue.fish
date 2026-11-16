#!/usr/bin/fish

if test (count $argv) -lt 2
    echo "❌ Ошибка: Недостаточно аргументов!"
    echo "Использование: ./run_queue.fish <queue_dir> <model_id>"
    echo "Пример: ./run_queue.fish queue_build ollama/qwen3.5:9b-32k"
    exit 1
end

set QUEUE_DIR $argv[1]
set MODEL_ID $argv[2]

if not test -d $QUEUE_DIR
    echo "❌ Ошибка: Директория $QUEUE_DIR не найдена!"
    exit 1
end

echo "🚀 Запуск очереди задач из $QUEUE_DIR с использованием модели $MODEL_ID..."
echo "--------------------------------------------"

for task_file in $QUEUE_DIR/*.txt
    if not test -e $task_file
        break
    end

    echo "🛠 Обработка: $task_file"
    
    # Читаем задачу напрямую из файла
    set task_content (cat $task_file)
    
    # Формируем полный промпт (CONTEXT + TASK)
    set CONTEXT_PROMPT (cat SPEC.md TASKS.md INSTRUCTIONS.md)
    set FULL_PROMPT "$CONTEXT_PROMPT\n\n--- NEW TASK ---\n$task_content"
    
    # Выполняем вызов opencode с переданной моделью
    opencode run -m $MODEL_ID "$FULL_PROMPT"
    
    if test $status -ne 0
        echo "--------------------------------------------"
        echo "❌ Ошибка на задаче $task_file. Останавливаем очередь."
        exit 1
    end
    
    # Перемещаем выполненный файл в подпапку completed внутри целевой директории
    mkdir -p $QUEUE_DIR/completed
    mv $task_file $QUEUE_DIR/completed/
    
    echo "✅ Задача $task_file выполнена успешно."
    echo "--------------------------------------------"
end

echo "🎉 ВСЕ ЗАДАЧИ ИЗ $QUEUE_DIR ВЫПОЛНЕНЫ!"
