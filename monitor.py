import requests
import time
import os
from datetime import datetime
import logging
import threading

# === НАСТРОЙКИ ===
URL = "https://edservicetx.com/"
CHECK_INTERVAL = 3600  # Проверка каждый час (3600 секунд)
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "207417689"
TIMEOUT = 20  # Таймаут 20 секунд
# =================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Счетчик ошибок и время последнего алерта
error_count = 0
last_status = None
last_alert_time = None
ALERT_INTERVAL = 3600  # Минимальный интервал между алертами (1 час)

def send_telegram_message(chat_id, text):
    """Отправляет сообщение в Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        return True
    except:
        return False

def check_website():
    """
    Простая проверка статуса сайта.
    Возвращает True если статус 200, False если нет.
    """
    try:
        response = requests.get(URL, timeout=TIMEOUT)
        
        if response.status_code == 200:
            return True, response.status_code
        else:
            return False, response.status_code
            
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection Error"
    except:
        return False, "Unknown Error"

def telegram_bot_polling():
    """Polling метод для Telegram бота."""
    logger.info("Запуск Telegram бота...")
    
    offset = None
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {'timeout': 30, 'offset': offset}
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                updates = response.json()
                
                if updates.get('ok') and updates.get('result'):
                    for update in updates['result']:
                        offset = update['update_id'] + 1
                        
                        if 'message' in update and 'text' in update['message']:
                            message = update['message']
                            chat_id = message['chat']['id']
                            text = message['text'].strip().lower()
                            
                            # Команда /ping
                            if text == '/ping':
                                status, code = check_website()
                                
                                if status:
                                    response_text = f"✅ Сайт работает\nURL: {URL}\nСтатус: 200 OK\nВремя: {datetime.now().strftime('%H:%M:%S')}"
                                else:
                                    response_text = f"❌ Сайт не доступен\nURL: {URL}\nОшибка: {code}\nВремя: {datetime.now().strftime('%H:%M:%S')}"
                                
                                send_telegram_message(chat_id, response_text)
                            
                            # Команда /help
                            elif text in ['/help', '/start']:
                                help_text = f"Мониторинг сайта\nURL: {URL}\n\nКоманды:\n/ping - проверить сейчас"
                                send_telegram_message(chat_id, help_text)
            
        except:
            time.sleep(5)

def website_monitor():
    """Мониторинг сайта в фоновом режиме."""
    global error_count, last_status, last_alert_time
    
    logger.info(f"Запуск мониторинга: {URL}")
    
    while True:
        try:
            status, code = check_website()
            current_time = time.time()
            
            if status:
                logger.info(f"✅ Сайт доступен, статус: {code}")
                
                # Если сайт был недоступен, а теперь восстановился
                if last_status == False and error_count > 0:
                    message = f"✅ Сайт восстановлен!\n\nURL: {URL}\nСтатус: 200 OK\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nСайт снова доступен после {error_count} неудачных проверок."
                    send_telegram_message(CHAT_ID, message)
                    error_count = 0
                    last_alert_time = None
                
                last_status = True
                
            else:
                error_count += 1
                logger.error(f"❌ Сайт не доступен, ошибка: {code}, счетчик ошибок: {error_count}")
                last_status = False
                
                # Проверяем, нужно ли отправлять алерт
                should_send_alert = False
                
                # Если это первая ошибка после восстановления
                if error_count == 1:
                    should_send_alert = True
                
                # Или если прошло достаточно времени с последнего алерта
                elif last_alert_time and (current_time - last_alert_time >= ALERT_INTERVAL):
                    should_send_alert = True
                
                # Или если это вторая ошибка подряд (первый алерт)
                elif error_count == 2:
                    should_send_alert = True
                
                if should_send_alert:
                    if error_count == 1:
                        message = f"⚠️ Первая ошибка обнаружена\n\nURL: {URL}\nОшибка: {code}\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nСледующая проверка через {CHECK_INTERVAL//60} минут."
                    else:
                        message = f"🚨 Сайт не доступен!\n\nURL: {URL}\nОшибка: {code}\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nОшибок подряд: {error_count}\nСледующая проверка через {CHECK_INTERVAL//60} минут."
                    
                    if send_telegram_message(CHAT_ID, message):
                        last_alert_time = current_time
                        logger.info(f"Алерт отправлен, счетчик ошибок: {error_count}")
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Ошибка мониторинга: {e}")
            time.sleep(CHECK_INTERVAL)

def main():
    """Основная функция."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден!")
        return
    
    logger.info("Запуск системы мониторинга...")
    logger.info(f"Интервал проверки: {CHECK_INTERVAL} секунд ({CHECK_INTERVAL//60} минут)")
    logger.info(f"Минимальный интервал между алертами: {ALERT_INTERVAL} секунд")
    
    # Запуск мониторинга в фоне
    monitor_thread = threading.Thread(target=website_monitor, daemon=True)
    monitor_thread.start()
    
    # Запуск Telegram бота
    telegram_bot_polling()

if __name__ == "__main__":
    main()