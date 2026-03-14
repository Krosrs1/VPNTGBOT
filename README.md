# VPNTGBOT — production-ready Telegram VPN bot (aiogram 3 + Marzban)

Бот продает VPN-подписки через Telegram, принимает оплату через CryptoBot и автоматически выдает доступ через API панели Marzban.

## Возможности

Тарифы (в рублях):
- 1 месяц — 200 ₽
- 3 месяца — 500 ₽
- 1 год — 1200 ₽


### Пользователь
- `/start` + главное меню:
  - Купить VPN
  - Пробный период
  - Моя подписка
  - Мой VPN
  - Поддержка
- Тарифы: 1 / 3 / 12 месяцев
- Оплата через CryptoBot invoice
- Автоматическая проверка оплаты кнопкой «Проверить оплату»
- После оплаты:
  - создание/продление пользователя в Marzban
  - запись подписки в SQLite
  - отправка VPN-ссылки
- Пробный период:
  - один раз на пользователя
  - 24 часа
  - 5 GB
- «Моя подписка»:
  - тариф
  - дата окончания
  - оставшиеся дни
- «Мой VPN»:
  - username
  - VPN-ссылка
  - краткая инструкция подключения

### Админ
- `/admin` (только `ADMIN_ID`)
- Разделы:
  - Пользователи
  - Активные подписки
  - Доход
  - Рассылка сообщений
  - Выдать VPN вручную
  - Заблокировать пользователя

## Структура проекта

```text
project/
  bot.py
  config.py
  database.py
  marzban_api.py
  cryptobot_api.py
  schema.sql
  requirements.txt
  .env.example
  handlers/
    start.py
    buy.py
    trial.py
    profile.py
    vpn.py
    admin.py
  keyboards/
    menu.py
    admin.py
  systemd/
    vpnbot.service
```

## Быстрый старт локально

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполните .env
python bot.py
```

## Пример .env

```env
BOT_TOKEN=123456789:AA...
ADMIN_ID=123456789
MARZBAN_URL=https://marzban.example.com
MARZBAN_TOKEN=your_marzban_token
MARZBAN_INBOUND_TAG=VLESS TCP REALITY
CRYPTOBOT_TOKEN=your_cryptobot_token
DATABASE_PATH=vpn_bot.db
```

## Установка на VPS (Ubuntu 22.04+)

1. Установить зависимости:

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git
```

2. Развернуть проект:

```bash
sudo mkdir -p /opt/vpnbot
sudo chown -R $USER:$USER /opt/vpnbot
git clone <your_repo_url> /opt/vpnbot
cd /opt/vpnbot
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env
```

3. Запустить вручную для проверки:

```bash
source /opt/vpnbot/.venv/bin/activate
python /opt/vpnbot/bot.py
```

4. Настроить автозапуск через systemd:

```bash
sudo cp systemd/vpnbot.service /etc/systemd/system/vpnbot.service
sudo systemctl daemon-reload
sudo systemctl enable vpnbot
sudo systemctl start vpnbot
sudo systemctl status vpnbot
```

5. Логи:

```bash
journalctl -u vpnbot -f
```

## Примечания по продакшену

- Обработка платежей идемпотентна: один оплаченный счет активирует/продлевает подписку только один раз.
- Для совместимости со старой БД выполняется мягкая миграция таблицы `payments` (добавляются `plan` и `is_processed`).
- Перед запуском убедитесь, что в Marzban inbound `VLESS TCP REALITY` существует.
- Для повышенной надежности можно добавить webhook вместо polling и отдельный воркер проверки оплат.
- Регулярно делайте бэкап файла SQLite (`vpn_bot.db`).
