import telebot
import requests
from telebot import types
import mysql.connector
from mysql.connector import Error
from config import telegram_token, db_config

bot = telebot.TeleBot(telegram_token)

# Функция для обработки команды /start
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_all = types.KeyboardButton("Показать все новости")
    button_latest = types.KeyboardButton("Показать последние новости")
    keyboard.add(button_all, button_latest)
    bot.send_message(message.chat.id, 'Привет! Я бот новостей. Выбери опцию, чтобы получить новости.', reply_markup=keyboard)

# Функция для обработки команды /get_news
@bot.message_handler(commands=['get_news'])
def get_news_command(message):
    get_news(message)

# Функция для обработки кнопок
@bot.message_handler(func=lambda message: message.text in ["Показать все новости", "Показать последние новости"])
def show_news_options(message):
    if message.text == "Показать все новости":
        get_news(message, order_by="date")
    elif message.text == "Показать последние новости":
        get_news(message, order_by="date DESC", limit=5)

# Функция для отображения новостей
def get_news(message, order_by=None, limit=None):
    try:
        # Подключение к базе данных
        connection = mysql.connector.connect(**db_config)

        # Построение SQL-запроса
        sql_query = "SELECT * FROM news"
        if order_by:
            sql_query += f" ORDER BY {order_by}"
        if limit:
            sql_query += f" LIMIT {limit}"

        # Выполнение SQL-запроса
        cursor = connection.cursor()
        cursor.execute(sql_query)
        news_records = cursor.fetchall()

        # Отправка новостей в чат
        for news in news_records:
            title = news[1]
            news_text = f"<b>{title}</b>\n\n{news[2]}\n\n\n{news[4]}\n\n{news[3]}"
            image_link = news[5]

            # Создание инлайн-клавиатуры с мини-кнопками
            inline_keyboard = types.InlineKeyboardMarkup(row_width=2)
            btn_vip = types.InlineKeyboardButton("Vip-персоны", callback_data=f"vip_{news[0]}")
            btn_attractions = types.InlineKeyboardButton("Достопримечательности",
                                                         callback_data=f"attractions_{news[0]}")
            inline_keyboard.add(btn_vip, btn_attractions)

            # Отправка изображения и текста с инлайн-клавиатурой
            if image_link:
                response = requests.get(image_link)
                if response.status_code == 200:
                    image_data = response.content
                    # Отправка изображения и текста
                    bot.send_photo(message.chat.id, photo=image_data, caption=news_text, parse_mode='HTML',
                                   reply_markup=inline_keyboard)
                else:
                    print(f"Не удалось загрузить изображение: {image_link}")
            else:
                bot.send_message(message.chat.id, news_text, parse_mode='HTML', reply_markup=inline_keyboard)

    except Error as e:
        print(f"Ошибка при запросе к базе данных: {e}")

    finally:
        # Закрытие соединения с базой данных
        if connection.is_connected():
            cursor.close()
            connection.close()


# Обработка нажатий на мини-кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        if call.data.startswith("vip_"):
            # Обработка нажатия на кнопку "Vip-персоны"
            news_id = int(call.data.split("_")[1])
            bot.send_message(call.message.chat.id, f"Вы выбрали Vip-персоны для новости с ID {news_id}")
        elif call.data.startswith("attractions_"):
            # Обработка нажатия на кнопку "Достопримечательности"
            news_id = int(call.data.split("_")[1])
            bot.send_message(call.message.chat.id, f"Вы выбрали Достопримечательности для новости с ID {news_id}")

if __name__ == "__main__":
    bot.polling(none_stop=True)

