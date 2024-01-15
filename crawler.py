import requests
import time
from bs4 import BeautifulSoup
import mysql.connector
from datetime import datetime, timedelta
from config import db_config

# Функция для взятия новости с каждого контейнера
def parse_news(container):
    # Извлекаем заголовок новости (ссылка на полную новость включена в заголовок)
    title_container = container.find('a', class_='sys')
    title = title_container.text.strip()
    link = 'https://bloknot-volgograd.ru' + title_container['href']

    # Извлекаем дату новости
    date_container = container.find('span', class_='botinfo')
    date_str = date_container.text.strip().split()  # Разбиваем текст на слова (по умолчанию по пробелам)
    time_str = date_str[-1].replace(' ', '')  # Убираем неразрывные пробелы для формата времени mysql
    date_str = date_str[0]

    if 'сегодня' in date_str.lower():
        # Получаем текущую дату и время
        current_datetime = datetime.now()
        # Форматируем дату в нужный формат
        date_str = current_datetime.strftime('%Y-%m-%d')
    elif 'вчера' in date_str.lower():
        # Получаем текущую дату и вычитаем один день
        current_datetime = datetime.now() - timedelta(days=1)
        # Форматируем дату в нужный формат
        date_str = current_datetime.strftime('%Y-%m-%d')
    else:
        date_str = datetime.strptime(date_str, '%d.%m.%Y').strftime('%Y-%m-%d')

    # Объединяем дату и время
    datetime_str = f"{date_str} {time_str}" if ':' in time_str else date_str

    # Извлекаем текст новости
    text_container = container.find('p')
    text = text_container.text.strip() if text_container else ''

    # Извлекаем ссылку на изображение
    image_container = container.find('img', class_='preview_picture')
    image_link = 'https:' + image_container['src'] if image_container else None

    return {'title': title, 'date': datetime_str, 'link': link, 'text': text, 'image_link': image_link}

# Функция для внесения новости в базу данных
def insert_into_db(news_data):
    query = "INSERT INTO news (title, date, link, text, image_link) VALUES (%s, %s, %s, %s, %s)"
    values = (news_data['title'], news_data['date'], news_data['link'], news_data['text'], news_data['image_link'])

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(query, values)
        connection.commit()
    except Exception as e:
        print(f"Error inserting data into the database: {e}")
    finally:
        cursor.close()
        connection.close()


# Функция для проверки наличия ссылки в базе данных
def link_exists_in_db(connection, link):
    query = "SELECT id FROM news WHERE link = %s"
    value = (link,)

    try:
        connection_ = mysql.connector.connect(**connection)
        cursor = connection_.cursor()
        cursor.execute(query, value)
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        print(f"Error checking link existence in the database: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection_' in locals():
            connection_.close()

def main():
    # URL сайта или RSS-ленты
    site_url = 'https://bloknot-volgograd.ru'

    # Периодичность повторения парсинга (в секундах)
    parse_interval = 2

    # Максимальное количество новостей, которое мы хотим получить
    max_news = 10000

    # Количество новостей, которое мы получили за 1 сессию парсинга
    received_news = 0

    while received_news <= max_news:
        # Получение всех контейнеров новостей
        response = requests.get(site_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        news_containers = soup.find_all('li', id=lambda x: x and x.startswith('bx_'))

        for container in reversed(news_containers):
            # Получить новость
            news_data = parse_news(container)

            # Проверить, была ли новость уже обработана (по ссылке)
            if not link_exists_in_db(db_config, news_data['link']) and (news_data['text'] != ''):
                # Записать новость в базу данных
                insert_into_db(news_data)

                # Уменьшить счетчик новостей
                received_news += 1

                # Ожидание перед следующей итерацией
                time.sleep(parse_interval)

                print(received_news, ')', news_data['title'], news_data['link'], news_data['date'])

        # После обработки новостей проверяем, не достигнуто ли максимальное количество новостей
        if received_news >= max_news:
            print("Достигнуто максимальное количество новостей. Программа завершает работу.")
            break


if __name__ == "__main__":
    main()
