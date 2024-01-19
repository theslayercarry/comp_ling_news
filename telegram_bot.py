# ТЕЛЕГРАМ - БОТ
import telebot
import asyncio
import requests
import mysql.connector
from fuzzywuzzy import fuzz
from datetime import datetime
from bs4 import BeautifulSoup
from telebot import types
from mysql.connector import Error
from config import telegram_token, db_config

# Функции для переписывания и аннотации новости
from rewriter import rewrite
from summarizer import summarize

bot = telebot.TeleBot(telegram_token)

# Загрузка имен и достопримечательностей из файлов
sights_file_path = 'файлы с данными/sights_volgograd.txt'
vip_persons_file_path = 'файлы с данными/VIP_persons_volgograd.txt'

with open(sights_file_path, 'r', encoding='utf-8') as sights_file:
    sights = [line.strip() for line in sights_file]

with open(vip_persons_file_path, 'r', encoding='utf-8') as vip_persons_file:
    vip_persons = [line.strip() for line in vip_persons_file]


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
            btn_vip = types.InlineKeyboardButton("VIP-персоны", callback_data=f"vip_{news[0]}")

            btn_attractions = types.InlineKeyboardButton("Достопримечательности", callback_data=f"attractions_{news[0]}")

            btn_rewriter = types.InlineKeyboardButton("Переписанная новость", callback_data=f"rewriter_{news[0]}")

            btn_summarizer = types.InlineKeyboardButton("Аннотация", callback_data=f"summarizer_{news[0]}")

            inline_keyboard.add(btn_vip, btn_attractions, btn_summarizer, btn_rewriter)

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
    chat_id = call.message.chat.id
    news_id = int(call.data.split("_")[1])
    news_text = get_news_text_from_website(news_id)  # Функция для получения текста новости с сайта
    if call.message:
        if call.data.startswith("vip_"):
            # Обработка нажатия на кнопку "Vip-персоны"
            vip_persons_mentions = find_mentions_in_text(news_text, vip_persons)
            formatted_mentions = format_mentions_with_context(vip_persons_mentions, news_text)
            message_text = f"<b>Упоминания VIP-персон в новости:</b>\n\n{formatted_mentions}"
            bot.send_message(chat_id, message_text, reply_to_message_id=call.message.message_id, parse_mode='HTML')

        elif call.data.startswith("attractions_"):
            # Обработка нажатия на кнопку "Достопримечательности"
            sights_mentions = find_mentions_in_text(news_text, sights)
            formatted_mentions = format_mentions_with_context(sights_mentions, news_text)
            message_text = f"<b>Упоминания достопримечательностей в новости:</b>\n\n{formatted_mentions}"
            bot.send_message(chat_id, message_text, reply_to_message_id=call.message.message_id, parse_mode='HTML')

        elif call.data.startswith("rewriter_"):
            # Обработка нажатия на кнопку "Переписанная новость"
            asyncio.run(handle_rewriter(call, news_text, chat_id))

        elif call.data.startswith("summarizer_"):
            # Обработка нажатия на кнопку "Аннотация"
            asyncio.run(handle_summarizer(call, news_text, chat_id))


# Асинхронные функции, которые ожидают выполнения функций rewrite и summarize
# Функция для обработки аннотации новости
async def handle_summarizer(call, news_text, chat_id):
    try:
        formatted_mentions = await summarize(news_text)
        message_text = f"<b>Аннотация новости:</b>\n\n{formatted_mentions}"
        bot.send_message(chat_id, message_text, reply_to_message_id=call.message.message_id, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка при обработке аннотации новости: {e}")


# Функция для обработки переписанной новости
async def handle_rewriter(call, news_text, chat_id):
    try:
        formatted_mentions = await rewrite(news_text)
        message_text = f"<b>Переписанная новость:</b>\n\n{formatted_mentions}"
        bot.send_message(chat_id, message_text, reply_to_message_id=call.message.message_id, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка при обработке переписанной новости: {e}")

# Функция для получения текста новости с сайта
def get_news_text_from_website(news_id):
    try:
        # Получение ссылки на новость
        news_link = get_news_link_by_id(news_id)

        if not news_link:
            print(f"Ссылка на новость с ID {news_id} не найдена.")
            return ""

        # Отправка запроса на сайт
        response = requests.get(news_link)

        # Проверка успешности запроса
        if response.status_code == 200:
            # Получение HTML-кода страницы
            html_content = response.text

            # Парсинг HTML-кода страницы
            soup = BeautifulSoup(html_content, 'html.parser')

            # Извлечение текста новости
            news_text_element = soup.find('div', class_='news-text')
            news_text = news_text_element.get_text() if news_text_element else ""

            # Получаем текущее время
            current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

            # Возврат текста новости
            characters = 250
            print('-' * characters, '\n', current_datetime, '\n', '-' * characters)
            print(news_text)

            return news_text
        else:
            print(f"Не удалось получить страницу новости. Код состояния: {response.status_code}")
            return ""
    except Exception as e:
        print(f"Ошибка при получении текста новости: {e}")
        return ""


# Функция для поиска упоминаний в тексте с контекстом
def find_mentions_in_text(text, entities):
    characters_after_word = 0  # Количество символов после предложения
    mentions = set()  # Используем множество для уникальных упоминаний

    for entity in entities:
        entity_parts = entity.split()
        entity_length = len(entity_parts)

        sentences = text.split('.')  # Разделяем текст на предложения

        for sentence in sentences:
            words = sentence.split()
            i = 0
            while i < len(words) - entity_length + 1:
                window = words[i:i + entity_length]
                window_text = ' '.join(window)

                # Проверяем схожесть для обоих вариантов имени и фамилии
                similarity_ratio_forward = fuzz.ratio(' '.join(entity_parts).lower(), window_text.lower())
                similarity_ratio_reverse = fuzz.ratio(' '.join(reversed(entity_parts)).lower(), window_text.lower())

                if similarity_ratio_forward >= 90 or similarity_ratio_reverse >= 90:
                    start_index = text.find(sentence)
                    mentions.add((sentence.strip(), start_index, start_index + characters_after_word))
                    break
                else:
                    i += 1  # Перейдем к следующему слову в предложении

    return list(mentions)  # Преобразуем множество обратно в список для вывода


# Функция для форматирования упоминаний с контекстом
def format_mentions_with_context(mentions, text):
    formatted_mentions = []
    for mention, start, end in mentions:
        context = text[start:end].strip()
        formatted_mentions.append(f"● {mention} {context}")
    return "\n\n".join(formatted_mentions)


# Функция для ссылки новости по её id в базе данных
def get_news_link_by_id(news_id):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        query = f"SELECT link FROM news WHERE id = {news_id}"
        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            return result[0]  # Возвращаем первый столбец результата (ссылка на новость)
        else:
            print(f"Ссылка на новость с ID {news_id} не найдена.")
            return ""

    except Error as e:
        print(f"Ошибка при выполнении запроса к базе данных: {e}")
        return ""

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    bot.polling(none_stop=True)
