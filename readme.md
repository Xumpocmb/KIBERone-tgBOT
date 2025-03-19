# KIBERone TELEGRAM BOT

## Telegram bot on Aiogram3

Run app:


# Install:

pip install -r requirements.txt


source /path/to/your/venv/bin/activate
python bot.py


nohup python3 bot.py > bot.log 2>&1 &
nohup позволяет запустить процесс, который не завершится, когда вы закроете сеанс SSH.

'>' перенаправляет вывод программы в файл bot.log.
'2>&1' перенаправляет stderr (стандартный поток ошибок) в stdout (стандартный поток вывода), что позволяет записывать как вывод, так и ошибки в тот же файл.
'&' позволяет процессу работать в фоновом режиме.

ps aux | grep bot.py
Это покажет вам процесс bot.py, который должен быть запущен.

# KIBERone

ngrok http http://127.0.0.1:8080