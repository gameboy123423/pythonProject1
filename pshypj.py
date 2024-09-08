import telebot
from telebot import types
import sqlite3
from datetime import datetime
import pandas as pd

'''Кто бы не читал этот код, простите '''
# Токен
bot = telebot.TeleBot('7314394046:AAHWOpsisgxtW2zpWw-9lRsonU--4Y9Phxk')

chat_id = ''

# Создание базы данных и функция подключения
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS goods (
        id INTEGER PRIMARY KEY,
        goods_name TEXT,
        amount INTEGER,
        price INTEGER
    )
''')

conn.commit()

def create_connection():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    return conn, cursor

# Крч, это клава которая составляется сама, она берет названия товаров из базы данных
def goods_keyboard(callback_prefix):
    conn, cursor = create_connection()
    goods_keyboard = telebot.types.InlineKeyboardMarkup()
    cursor.execute("SELECT goods_name FROM goods")
    goods_list = cursor.fetchall()
    for good in goods_list:
        temp = telebot.types.InlineKeyboardButton(f'{good[0]}', callback_data=f'{callback_prefix}_{good[0]}')
        goods_keyboard.add(temp)
    conn.close()
    return goods_keyboard

# Функция для главного меню
def main_menu_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Создать чек', 'Изменения')
    markup.row('Показать всё')
    markup.add('Продажи за день', 'Продажи за неделю', 'Продажи за месяц')
    return markup

# Стадия 1
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Добро пожаловать', reply_markup=main_menu_keyboard())
    global chat_id
    chat_id = message.chat.id

# Define a function to handle button clicks
@bot.message_handler(func=lambda message: True)
def button_click(message):
    print(f"Button clicked: {message.text}")  # Log button clicks
    if message.text == 'Создать чек':
        tips(message)
    elif message.text == 'Изменения':
        bot.send_message(message.chat.id, 'меняем', reply_markup=changes_keyboard())
        bot.register_next_step_handler(message, changes)
    elif message.text == 'Показать всё':
        show_all(message)
    elif message.text == 'Продажи за день':
        send_sales_summary(message, 'day')
    elif message.text == 'Продажи за неделю':
        send_sales_summary(message, 'week')
    elif message.text == 'Продажи за месяц':
        send_sales_summary(message, 'month')
    elif message.text == 'Назад':
        bot.send_message(message.chat.id, 'Возвращаемся назад', reply_markup=main_menu_keyboard())

# Define the tips function
def tips(message):
    print("Executing tips function")  # Log execution
    if message.text == 'Назад':
        bot.register_next_step_handler(message, button_click)
    elif message.text == 'Создать чек':
        bot.send_message(message.chat.id, 'Выберите товар:', reply_markup=goods_keyboard('choose_good'))

@bot.callback_query_handler(func=lambda call: True)
def callback_query_handler(call):
    print(f"Callback received: {call.data}")  # Log callback data
    if call.data.startswith('choose_good_'):
        goods_name = call.data.split('_')[2]
        bot.send_message(call.message.chat.id, f'Введите количество для {goods_name}:')
        bot.register_next_step_handler(call.message, lambda msg: process_good_amount(msg, goods_name))
    elif call.data.startswith('update_amount_'):
        goods_name = call.data.split('_')[2]
        bot.send_message(call.message.chat.id, f'Введите новое количество для {goods_name}:')
        bot.register_next_step_handler(call.message, lambda msg: update_amount_with_name(msg, goods_name))
    elif call.data.startswith('update_price_'):
        goods_name = call.data.split('_')[2]
        bot.send_message(call.message.chat.id, f'Введите новую цену для {goods_name}:')
        bot.register_next_step_handler(call.message, lambda msg: update_price_with_name(msg, goods_name))
    elif call.data == 'add_good':
        bot.send_message(call.message.chat.id, 'Введите имя товара:')
        bot.register_next_step_handler(call.message, add_good)
    elif call.data == 'delete_good':
        bot.send_message(call.message.chat.id, 'Введите имя товара для удаления:')
        bot.register_next_step_handler(call.message, delete_good)
    elif call.data == 'update_amount':
        bot.send_message(call.message.chat.id, 'Выберите товар для изменения количества:', reply_markup=goods_keyboard('update_amount'))
    elif call.data == 'update_price':
        bot.send_message(call.message.chat.id, 'Выберите товар для изменения цены:', reply_markup=goods_keyboard('update_price'))
    elif call.data == 'show_all':
        show_all(call.message)

def process_good_amount(message, goods_name):
    print(f"Processing amount for {goods_name}")  # Log processing
    try:
        amount = int(message.text)
        conn, cursor = create_connection()
        cursor.execute("SELECT amount, price FROM goods WHERE goods_name=?", (goods_name,))
        row = cursor.fetchone()
        if row:
            current_amount = row[0]
            price = row[1]
            if current_amount >= amount:
                cursor.execute("UPDATE goods SET amount=? WHERE goods_name=?", (current_amount - amount, goods_name))
                conn.commit()
                bot.send_message(message.chat.id, f'Количество товара {goods_name} уменьшено на {amount}!')

                # Сохранение чеков в текстовый файл
                with open('tips.txt', 'a') as file:
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    file.write(f"___________________________________________________________________________________\n"
                               f"  Время: {now}\n  Товар: {goods_name}\n  Количество: {amount}\n  Сумма: {amount * price}\n"
                               f"___________________________________________________________________________________\n")

                # Сохранение данных чеков в отдельный файл
                with open('sales.txt', 'a') as sales_file:
                    sales_file.write(f"{now},{goods_name},{amount},{price}\n")

                # Переход к следующему этапу или сообщению об успешном завершении
                bot.send_message(message.chat.id, 'Чек успешно создан!', reply_markup=main_menu_keyboard())
            else:
                bot.send_message(message.chat.id, f'Недостаточно товара {goods_name} в наличии!',
                                 reply_markup=main_menu_keyboard())
        else:
            bot.send_message(message.chat.id, f'Товар {goods_name} не найден в базе данных.',
                             reply_markup=main_menu_keyboard())
        conn.close()
    except ValueError:
        bot.send_message(message.chat.id, 'Пожалуйста, введите корректное число.')
        bot.register_next_step_handler(message, lambda msg: process_good_amount(msg, goods_name))

# переход к изменению данных
def changes(message):
    print("Executing changes function")  # Log execution
    bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=changes_keyboard())

# Изменение данных
def changes_keyboard():
    changes_keyboard = telebot.types.InlineKeyboardMarkup()
    changes_keyboard.add(telebot.types.InlineKeyboardButton('Добавить товар', callback_data='add_good'))
    changes_keyboard.add(telebot.types.InlineKeyboardButton('Удалить товар', callback_data='delete_good'))
    changes_keyboard.add(telebot.types.InlineKeyboardButton('Изменить количество', callback_data='update_amount'))
    changes_keyboard.add(telebot.types.InlineKeyboardButton('Изменить цену', callback_data='update_price'))
    return changes_keyboard

def add_good(message):
    print(f"Adding good: {message.text}")  # Log addition
    conn, cursor = create_connection()
    goods_name = message.text
    cursor.execute("INSERT INTO goods (goods_name, amount, price) VALUES (?, 0, 0)", (goods_name,))
    conn.commit()
    bot.send_message(message.chat.id, f'Товар {goods_name} добавлен!')
    conn.close()

def delete_good(message):
    print(f"Deleting good: {message.text}")  # Log deletion
    conn, cursor = create_connection()
    goods_name = message.text
    cursor.execute("DELETE FROM goods WHERE goods_name=?", (goods_name,))
    conn.commit()
    bot.send_message(message.chat.id, f'Товар {goods_name} удален!')
    conn.close()

def update_amount(message):
    print("Requesting new amount")  # Log update request
    bot.send_message(message.chat.id, 'Выберите товар для изменения количества:', reply_markup=goods_keyboard('update_amount'))

def get_goods_name_for_update_amount(message):
    goods_name = message.text
    print(f"Updating amount for {goods_name}")  # Log update
    bot.send_message(message.chat.id, 'Введите новое количество:')
    bot.register_next_step_handler(message, update_amount_with_name, goods_name)

def update_amount_with_name(message, goods_name):
    try:
        amount = int(message.text)
        conn, cursor = create_connection()
        cursor.execute("UPDATE goods SET amount=? WHERE goods_name=?", (amount, goods_name))
        conn.commit()
        bot.send_message(message.chat.id, f'Количество товара {goods_name} изменено на {amount}!')
        conn.close()
    except ValueError:
        bot.send_message(message.chat.id, 'Пожалуйста, введите корректное число.')
        bot.register_next_step_handler(message, update_amount_with_name, goods_name)

def update_price(message):
    print("Requesting new price")  # Log update request
    bot.send_message(message.chat.id, 'Выберите товар для изменения цены:', reply_markup=goods_keyboard('update_price'))

def get_goods_name_for_update_price(message):
    goods_name = message.text
    print(f"Updating price for {goods_name}")  # Log update
    bot.send_message(message.chat.id, 'Введите новую цену:')
    bot.register_next_step_handler(message, update_price_with_name, goods_name)

def update_price_with_name(message, goods_name):
    try:
        price = int(message.text)
        conn, cursor = create_connection()
        cursor.execute("UPDATE goods SET price=? WHERE goods_name=?", (price, goods_name))
        conn.commit()
        bot.send_message(message.chat.id, f'Цена товара {goods_name} изменена на {price}!')
        conn.close()
    except ValueError:
        bot.send_message(message.chat.id, 'Пожалуйста, введите корректное число.')
        bot.register_next_step_handler(message, update_price_with_name, goods_name)

def show_all(message):
    print("Showing all goods")  # Log showing all goods
    conn, cursor = create_connection()
    cursor.execute('SELECT * FROM goods')
    goods_list = cursor.fetchall()
    output = ''
    for el in goods_list:
        output += f'{el[1]} — Количество: {el[2]}, Цена: {el[3]}\n'
    bot.send_message(message.chat.id, output)
    conn.close()

# Функция для чтения данных о продажах с указанием кодировки
def read_sales_data():
    print("Reading sales data")  # Log reading
    try:
        sales_data = pd.read_csv('sales.txt', names=['datetime', 'goods_name', 'amount', 'price'], encoding='ansi')
        sales_data['datetime'] = pd.to_datetime(sales_data['datetime'])
        return sales_data
    except Exception as e:
        print(f"Error reading sales data: {e}")
        return pd.DataFrame()


def sales_per_day():
    sales_data = read_sales_data()
    if sales_data.empty:
        return pd.DataFrame()

    # Получаем текущую дату
    today = datetime.now().date()

    # Фильтруем данные за сегодняшний день
    sales_data['date'] = sales_data['datetime'].dt.date
    filtered_data = sales_data[sales_data['date'] == today]

    # Группируем по товару
    grouped = filtered_data.groupby('goods_name').agg({
        'amount': 'sum',  # Суммируем количество проданного товара
        'price': 'sum'    # Суммируем итоговую сумму
    }).reset_index()

    return grouped



def sales_per_week():
    sales_data = read_sales_data()
    if sales_data.empty:
        return pd.DataFrame()

    # Группировка по неделям
    sales_data['week'] = sales_data['datetime'].dt.isocalendar().week
    sales_data['year'] = sales_data['datetime'].dt.year

    # Группировка по году, неделе и товару
    grouped = sales_data.groupby(['year', 'week', 'goods_name']).agg({'amount': 'sum', 'price': 'mean'}).reset_index()

    return grouped



def sales_per_month():
    sales_data = read_sales_data()
    if sales_data.empty:
        return pd.DataFrame()

    # Группировка по месяцам
    sales_data['month'] = sales_data['datetime'].dt.to_period('M')

    # Группировка по месяцу и товару
    grouped = sales_data.groupby(['month', 'goods_name']).agg({'amount': 'sum', 'price': 'mean'}).reset_index()

    return grouped



# Функция отправки сводки продаж
def send_sales_summary(message, period):
    if period == 'day':
        sales_data = sales_per_day()
    elif period == 'week':
        sales_data = sales_per_week()
    elif period == 'month':
        sales_data = sales_per_month()
    else:
        bot.send_message(message.chat.id, 'Некорректный период!')
        return

    if sales_data.empty:
        bot.send_message(message.chat.id, 'Нет данных для отображения.')
        return

    output = f'Продажи за {period}:\n'
    total_sum = 0

    # Выводим результат
    for _, row in sales_data.iterrows():
        amount = row['amount']
        price = row['price']  # Общая сумма
        total_sum += price

        output += f"{row['goods_name']}: {amount} шт, {price} тг\n"

    output += f"\nОбщая сумма за {period}: {total_sum} тг\n"
    bot.send_message(message.chat.id, output)


# Запуск бота
bot.infinity_polling()
