# 🚀 КАК ЗАПУСТИТЬ БОТА ЗАВТРА

## ☕ Утром когда проснулся:

### Шаг 1: Открой VS Code
- Запусти **Visual Studio Code**
- Нажми **File → Open Folder**
- Выбери папку: `C:\Users\user\Documents\bot_project`

### Шаг 2: Открой терминал
- В VS Code нажми **Terminal → New Terminal** (или `Ctrl + ~`)
- Терминал откроется внизу экрана

### Шаг 3: Запусти бота
В терминале напечатай:
```bash
.\venv\Scripts\python main.py
```
Нажми **Enter**

### Шаг 4: Проверь что работает
Увидишь примерно так:
```
INFO:aiogram.dispatcher:Start polling
INFO:aiogram.dispatcher:Run polling for bot @ArenaSlot_bot
```

✅ **Бот работает!** Можешь тестить в Telegram.

---

## 🛑 Остановить бота

Когда нужно остановить:
- Нажми `Ctrl + C` в терминале
- Или просто закрой терминал

---

## 💡 Если что-то не работает

### Ошибка "python не найден"
```bash
.\venv\Scripts\python main.py
```
(используй виртуальное окружение)

### Ошибка "ModuleNotFoundError"
Установи зависимости:
```bash
.\venv\Scripts\pip install -r requirements.txt
```

### Конфликт "already running"
Останови старые процессы:
```bash
taskkill /F /IM python.exe
```
Потом запусти снова: `.\venv\Scripts\python main.py`

---

## 📋 Продолжить работу

1. **Открой план на сегодня:**
   - Файл: `plan_tomorrow.md` в папке проекта
   - Или спроси меня "что делать дальше?"

2. **Смотри задачи:**
   - Файл: `task.md` - там список что сделали и что осталось

3. **Начни кодить!** 🔥

---

## 🆘 Быстрая помощь

**Команда для запуска бота:**
```bash
cd C:\Users\user\Documents\bot_project
.\venv\Scripts\python main.py
```


Вот и всё! Спокойной ночи! 😴
