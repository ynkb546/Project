import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.simpledialog as sd

# Словарь состояния симуляции. Хранит текущие параметры и результаты лучшей стратегии.
state = {
    'df': None,  # Итоговый DataFrame с историей лучшего прогноза
    'batches': [],  # Текущий список партий на виртуальном складе
    'last_date': None,  # Дата последней смоделированной недели
    'q_value': 0,  # Целевой уровень запаса для оптимального квантиля
    'shelf_life': 0,  # Срок годности товара, введенный пользователем
    'storage_cost': 0,  # Стоимость хранения одной единицы товара в неделю
    'price': 0,  # Цена за единицу товара
    'product_name': ""  # Наименование выбранного для анализа товара
}

# Словарь метрик для построения аналитических графиков
metrics = {
    'total_packs': 0,  # Общее количество проданных штучных товаров
    'total_weight': 0,  # Общее количество проданных весовых товаров
    'top_packs': None,  # DataFrame с Топ-5 штучных товаров по объемам продаж
    'top_weight': None,  # DataFrame с Топ-5 весовых товаров по объемам продаж
    'plotly_weekly': None,  # Сгруппированные по неделям данные весовых товаров для графиков Plotly
    'plotly_cumulative': None,  # Кумулятивная сумма продаж для графиков Plotly
    'table_name': ""  # Имя загруженного файла
}

# Настройка единого визуального стиля для графиков Matplotlib и Seaborn
plt.rcParams['figure.facecolor'] = '#1a1c1e'
plt.rcParams['axes.facecolor'] = '#212529'
plt.rcParams['text.color'] = '#ffffff'
plt.rcParams['xtick.color'] = '#b2bdc6'
plt.rcParams['ytick.color'] = '#b2bdc6'
plt.rcParams['axes.labelcolor'] = '#ffffff'
plt.rcParams['axes.edgecolor'] = '#4f545c'


def center_window(window, width, height):
    """
    Метод для создания графических окон Tkinter на экране.
    Принимает объект окна, а также его желаемые ширину и высоту.
    """
    window.update_idletasks()
    # Вычисляем координаты X и Y на основе разрешения монитора пользователя
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def show_treeview_window(root, df, title):
    """
    Метод для создания окна с интерактивной таблицей.
    Используется для вывода еженедельных объемов, матрицы сравнения и итоговых прогнозов.
    """
    top = tk.Toplevel(root)
    top.title(title)
    top.geometry("1150x550")
    top.configure(bg="#1a1c1e")

    # Верхняя панель с названием таблицы
    header_frame = tk.Frame(top, bg="#212529", height=50)
    header_frame.pack(fill="x", side="top")
    tk.Label(header_frame, text=title.upper(), font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#212529").pack(pady=12,
                                                                                                               padx=15,
                                                                                                               side="left")

    table_frame = tk.Frame(top, bg="#1a1c1e")
    table_frame.pack(fill="both", expand=True, padx=15, pady=15)

    # Предобработка данных перед выводом: форматирование дат и округление дробных чисел
    display_df = df.copy()
    for col in display_df.columns:
        if pd.api.types.is_datetime64_any_dtype(display_df[col]):
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')
        elif pd.api.types.is_float_dtype(display_df[col]):
            display_df[col] = display_df[col].round(2)

    # Настройка стилей для таблицы
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#212529", foreground="#ffffff", fieldbackground="#212529", rowheight=28,
                    font=("Segoe UI", 9))
    style.configure("Treeview.Heading", background="#2f343a", foreground="#ffffff", bordercolor="#1a1c1e",
                    font=("Segoe UI", 9, "bold"))
    style.map("Treeview", background=[("selected", "#3a3f44")])

    # Полосы прокрутки
    scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
    scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")

    tree = ttk.Treeview(table_frame, columns=list(display_df.columns), show="headings", yscrollcommand=scroll_y.set,
                        xscrollcommand=scroll_x.set)

    # Настройка заголовков колонок
    for col in display_df.columns:
        tree.heading(col, text=col)
        anchor_pos = "center" if pd.api.types.is_numeric_dtype(df[col]) else "w"
        max_len = max(display_df[col].astype(str).map(len).max(), len(col)) if not display_df.empty else len(col)
        tree.column(col, width=min(max(max_len * 9, 110), 320), anchor=anchor_pos)

    scroll_y.config(command=tree.yview)
    scroll_x.config(command=tree.xview)
    scroll_y.pack(side="right", fill="y")
    scroll_x.pack(side="bottom", fill="x")
    tree.pack(fill="both", expand=True)

    # Заполнение таблицы данными из DataFrame
    for _, row in display_df.iterrows():
        tree.insert("", "end", values=list(row))


def add_interactive_week(root):
    """
    Метод для симуляции новой недели.
    Рассчитывает оптимальный объем заказа, запрашивает у пользователя продажи,
    проводит данные через модель и добавляет новую строку в таблицу.
    """
    # Дата следующей недели
    new_date = state['last_date'] + pd.DateOffset(days=7)
    current_stock = sum(b['qty'] for b in state['batches'])
    # Расчет рекомендуемой поставки
    suggested_delivery = int(max(0, np.ceil(state['q_value']) - current_stock))

    # Вызов диалогового окна для ввода продаж пользователем
    user_sales = sd.askfloat(
        "Симуляция новой недели",
        f"Дата: {new_date.strftime('%Y-%m-%d')}\n"
        f"Рекомендуемая поставка: {suggested_delivery} шт.\n"
        f"Ожидаемый запас: {current_stock + suggested_delivery} шт.\n\n"
        f"Введите фактический объем продаж за эту неделю:"
    )
    if user_sales is None:  # Если пользователь нажал "Отмена"
        return

    # Если поставка необходима, оформляем её как новую партию с полным сроком годности
    if suggested_delivery > 0:
        state['batches'].append({'qty': suggested_delivery, 'weeks_left': state['shelf_life']})

    start_stock = sum(b['qty'] for b in state['batches'])

    # Алгоритм продаж
    to_sell = user_sales
    sold = 0
    for b in state['batches']:
        if to_sell <= 0:
            break
        take = min(b['qty'], to_sell)  # Берем максимум возможного из текущей партии
        b['qty'] -= take
        to_sell -= take
        sold += take

    # Учет срока годности
    expired = 0
    active_batches = []
    for b in state['batches']:
        b['weeks_left'] -= 1  # Уменьшаем срок годности на 1 неделю
        if b['weeks_left'] <= 0:
            expired += b['qty']  # Товар испортился
        elif b['qty'] > 0:
            active_batches.append(b)  # Товар годен и не пуст — оставляем на складе
    state['batches'] = active_batches

    # Формирование новой строки с результатами
    new_row = {
        'Дата': new_date, 'Поставка, шт': suggested_delivery, 'Остаток начало, шт/кг': start_stock,
        'Спрос за неделю, шт/кг': user_sales, 'Продано, шт/кг': sold, 'Списано по сроку, шт/кг': expired,
        'Остаток конец, шт/кг': sum(b['qty'] for b in state['batches']),
        'Стоимость хранения, руб': start_stock * state['storage_cost'],
        'Прибыль от продаж, руб': sold * state['price'],
        'Чистая прибыль, руб': (sold * state['price']) - (start_stock * state['storage_cost']),
        'Упущенная выгода (дефицит), руб': to_sell * state['price'],
        'Убыток от списаний, руб': expired * state['price'],
        'Общая потерянная прибыль, руб': (to_sell + expired) * state['price']
    }

    # Обновление состояния системы
    state['df'] = pd.concat([state['df'], pd.DataFrame([new_row])], ignore_index=True)
    state['last_date'] = new_date

    # Отображение обновленной таблицы пользователю
    show_treeview_window(root, state['df'], "Обновленный интерактивный прогноз")


def run_quantile_simulation(prod_data, target_q, shelf_life, storage_cost, unit_price):
    """
    Функция моделирования запасов за весь период.
    Принимает срез данных по товару, квантиль, параметры логистики.
    Имитирует закупки, продажи, списания просрочки.
    """
    current_date = prod_data['Дата'].min()
    max_date = prod_data['Дата'].max()
    stock_batches = []  # склад для текущей симуляции
    deliveries = []  # Массив для накопления еженедельной истории результатов

    # Симуляция
    while current_date <= max_date:
        next_date = current_date + pd.DateOffset(days=7)
        current_stock = sum(b['qty'] for b in stock_batches)

        # Заказываем столько, чтобы поднять текущий склад до нужного квантиля
        delivery_qty = int(max(0, np.ceil(target_q) - current_stock))
        if delivery_qty > 0:
            stock_batches.append({'qty': delivery_qty, 'weeks_left': shelf_life})

        start_stock = sum(b['qty'] for b in stock_batches)
        # Собираем реальный спрос из файла
        demand = prod_data[(prod_data['Дата'] >= current_date) & (prod_data['Дата'] < next_date)]['Количество'].sum()

        # Реализация продаж
        to_sell = demand
        sold = 0
        for b in stock_batches:
            if to_sell <= 0: break
            take = min(b['qty'], to_sell)
            b['qty'] -= take
            to_sell -= take
            sold += take

        # Моделирование старения партий товара и просрочки
        expired = 0
        active = []
        for b in stock_batches:
            b['weeks_left'] -= 1
            if b['weeks_left'] <= 0:
                expired += b['qty']
            elif b['qty'] > 0:
                active.append(b)
        stock_batches = active

        # Добавление подробного отчета за прошедшую неделю
        deliveries.append({
            'Дата': current_date, 'Поставка, шт': delivery_qty, 'Остаток начало, шт/кг': start_stock,
            'Спрос за неделю, шт/кг': demand, 'Продано, шт/кг': sold, 'Списано по сроку, шт/кг': expired,
            'Остаток конец, шт/кг': sum(b['qty'] for b in stock_batches),
            'Стоимость хранения, руб': start_stock * storage_cost, 'Прибыль от продаж, руб': sold * unit_price,
            'Чистая прибыль, руб': (sold * unit_price) - (start_stock * storage_cost),
            'Упущенная выгода (дефицит), руб': to_sell * unit_price, 'Убыток от списаний, руб': expired * unit_price,
            'Общая потерянная прибыль, руб': (to_sell + expired) * unit_price
        })
        current_date = next_date  # Переход к следующей неделе

    return pd.DataFrame(deliveries), stock_batches


def main():
    """
    Главная функция программы. Инициализирует UI, поиск лучшей стратегии поставок среди
    всех квантилей, и развертывание главного меню.
    """
    root = tk.Tk()
    root.withdraw()  # Временно скрываем корневое окно на время выбора файла и настроек

    # Диалоговое окно выбора исходного файла
    file_path = filedialog.askopenfilename(
        title="Выберите файл с данными о поставках (CSV)",
        filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")]
    )
    if not file_path: return
    metrics['table_name'] = os.path.splitext(os.path.basename(file_path))[0]

    # Чтение и обработка файла через
    try:
        data = pd.read_csv(file_path)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")
        return

    # Список уникальных товаров из файла для выпадающего списка
    available_products = sorted(data['Наименование товара'].dropna().unique())

    # Окно настроек параметров
    setup_win = tk.Toplevel(root)
    setup_win.title("Настройки симуляции")
    setup_win.configure(bg="#212529")
    center_window(setup_win, 450, 280)
    setup_win.grab_set()

    # Переменные для хранения ввода пользователя
    prod_var = tk.StringVar(value=available_products[0])
    shelf_var = tk.IntVar(value=4)
    cost_var = tk.DoubleVar(value=1.5)
    confirmed = [False]

    def on_submit():
        """Метод обработки клика по кнопке продолжения"""
        confirmed[0] = True
        setup_win.destroy()

    # Отрисовка элементов интерфейса настроек
    tk.Label(setup_win, text="⚙ ПАРАМЕТРЫ", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#212529").pack(pady=15)
    f = tk.Frame(setup_win, bg="#212529")
    f.pack(fill="both", expand=True, padx=20)

    tk.Label(f, text="Выберите товар:", font=("Segoe UI", 9), fg="#b2bdc6", bg="#212529").grid(row=0, column=0,
                                                                                               sticky="w", pady=10)
    ttk.Combobox(f, textvariable=prod_var, values=available_products, state="readonly", width=30).grid(row=0, column=1,
                                                                                                       padx=10, pady=10)

    tk.Label(f, text="Срок годности (нед):", font=("Segoe UI", 9), fg="#b2bdc6", bg="#212529").grid(row=1, column=0,
                                                                                                    sticky="w", pady=10)
    ttk.Spinbox(f, from_=1, to=1000, textvariable=shelf_var, width=10).grid(row=1, column=1, sticky="w", padx=10,
                                                                            pady=10)

    tk.Label(f, text="Цена хранения (руб):", font=("Segoe UI", 9), fg="#b2bdc6", bg="#212529").grid(row=2, column=0,
                                                                                                    sticky="w", pady=10)
    ttk.Entry(f, textvariable=cost_var, width=12).grid(row=2, column=1, sticky="w", padx=10, pady=10)

    tk.Button(setup_win, text="ПРОДОЛЖИТЬ", command=on_submit, bg="#27ae60", fg="#ffffff", font=("Segoe UI", 9, "bold"),
              bd=0, cursor="hand2", width=20, height=1).pack(pady=15)

    root.wait_window(setup_win)
    if not confirmed[0]: return

    # Раздел товаров по штучным и весовым
    data['is_int'] = data['Количество'].apply(lambda x: float(x).is_integer())
    p_data = data[data['is_int']]
    w_data = data[~data['is_int']]

    # Метрики объемов для круговой диаграммы и топ-5 гистограмм
    metrics['total_packs'] = p_data['Количество'].sum()
    metrics['total_weight'] = w_data['Количество'].sum()
    metrics['top_packs'] = p_data.groupby('Наименование товара')['Количество'].sum().reset_index().sort_values(
        'Количество', ascending=False).head(5)
    metrics['top_weight'] = w_data.groupby('Наименование товара')['Количество'].sum().reset_index().sort_values(
        'Количество', ascending=False).head(5)

    # Подготовка данных для построения графиков динамики продаж в Plotly
    data['Дата'] = pd.to_datetime(data['Дата'])
    merged = pd.merge(data, metrics['top_weight'][['Наименование товара']], on='Наименование товара')
    metrics['plotly_weekly'] = merged.groupby(['Наименование товара', pd.Grouper(key='Дата', freq='W')])[
        'Количество'].sum().reset_index()

    # Извлечение данных выбранного товара
    sel_prod = prod_var.get()
    prod_df = data[data['Наименование товара'] == sel_prod].copy()
    # расчет цены за единицу
    u_price = np.ceil(prod_df['Сумма к оплате'].sum() / prod_df['Количество'].sum()) if not prod_df.empty else 0
    w_series = prod_df.groupby(pd.Grouper(key='Дата', freq='W'))['Количество'].sum()

    # Поиск лучшего кванитля
    q_maps = {'0.25': 0.25, '0.50': 0.50, '0.75': 0.75, '0.85': 0.85, '0.95': 0.95}
    comp_data = []  # Массив для сравнительной таблицы
    best_p = -float('inf')
    best_n, best_df, best_b = "", None, []

    # Цикл перебора стратегий
    for n, v in q_maps.items():
        q_val = w_series.quantile(v) if not w_series.empty else 0
        s_df, f_batches = run_quantile_simulation(prod_df, q_val, shelf_var.get(), cost_var.get(), u_price)
        p_val = s_df['Чистая прибыль, руб'].sum() if not s_df.empty else 0
        comp_data.append({'Квантиль': n, 'Общая прибыль': p_val, 'Списано': s_df['Списано по сроку, шт/кг'].sum()})

        # Стратегия с большей прибылью из всех
        if p_val > best_p:
            best_p, best_n, best_df, best_b = p_val, n, s_df, f_batches

    # Фиксируем лучшую стратегию в state
    state.update({
        'df': best_df, 'batches': best_b, 'q_value': w_series.quantile(q_maps[best_n]) if not w_series.empty else 0,
        'last_date': pd.to_datetime(best_df['Дата'].iloc[-1]) if not best_df.empty else pd.Timestamp.now(),
        'shelf_life': shelf_var.get(), 'storage_cost': cost_var.get(), 'price': u_price, 'product_name': sel_prod
    })

    # Отрисовка главного интерфейса
    root.deiconify()  # Показываем основное окно программы
    root.title("Аналитика управления запасами")
    center_window(root, 560, 580)
    root.configure(bg="#1a1c1e")

    # Шапка главного меню
    t_bar = tk.Frame(root, bg="#212529", height=65)
    t_bar.pack(fill="x", side="top")
    tk.Label(t_bar, text="📊 ПАНЕЛЬ УПРАВЛЕНИЯ ЗАПАСАМИ", font=("Segoe UI", 12, "bold"), fg="#ffffff",
             bg="#212529").pack(pady=10)
    tk.Label(root, text=f"Файл: {metrics['table_name']}  |  Товар: {state['product_name']}",
             font=("Segoe UI", 9, "italic"), fg="#9e9e9e", bg="#1a1c1e").pack(pady=8)

    # Список кнопок меню:
    menu = [
        ("1.  Диаграмма: Доли распределения", lambda: (plt.figure(figsize=(7, 5)),
                                                       plt.pie([metrics['total_weight'], metrics['total_packs']],
                                                               labels=['Вес', 'Пачки'], autopct='%1.1f%%',
                                                               colors=['#5865F2', '#F47B67']), plt.show()), "#3a3f44",
         "#4e545c"),
        ("2. Гистограмма: Топ-5 Пачки", lambda: (plt.figure(figsize=(10, 5)),
                                                 sns.barplot(x='Количество', y='Наименование товара',
                                                             data=metrics['top_packs'], palette='viridis'), plt.show()),
         "#3a3f44", "#4e545c"),
        ("3. Гистограмма: Топ-5 Вес", lambda: (plt.figure(figsize=(10, 5)),
                                               sns.barplot(x='Количество', y='Наименование товара',
                                                           data=metrics['top_weight'], palette='magma'), plt.show()),
         "#3a3f44", "#4e545c"),
        ("4. Plotly: Динамика продаж",
         lambda: px.line(metrics['plotly_weekly'], x='Дата', y='Количество', color='Наименование товара').show(),
         "#3a3f44", "#4e545c"),
        ("5. Таблица: Отчет по неделям",
         lambda: show_treeview_window(root, w_series.reset_index(), "Еженедельные объемы"), "#2c3e50", "#34495e"),
        ("6. Сравнение стратегий (Матрица)",
         lambda: show_treeview_window(root, pd.DataFrame(comp_data), "Сравнение квантилей"), "#b7950b", "#d4ac0d"),
        (f"7. Оптимальный прогноз (Квантиль {best_n})",
         lambda: show_treeview_window(root, state['df'], f"Детализация модели {best_n}"), "#27ae60", "#2ecc71"),
        ("8. СИМУЛИРОВАТЬ СЛЕДУЮЩУЮ НЕДЕЛЮ", lambda: add_interactive_week(root), "#2980b9", "#3498db")
    ]

    # Генерация кнопок в интерфейсе
    for txt, cmd, bg, hov in menu:
        b = tk.Button(root, text=txt, command=cmd, width=58, bd=0, font=("Segoe UI", 9, "bold"), fg="#ffffff", bg=bg,
                      activebackground=hov, cursor="hand2")
        b.pack(pady=4)
        b.bind("<Enter>", lambda e, h=hov, btn=b: btn.config(bg=h))
        b.bind("<Leave>", lambda e, n=bg, btn=b: btn.config(bg=n))

    # Кнопка закрытия проекта
    tk.Button(root, text="ЗАКРЫТЬ ПРОЕКТ", command=root.destroy, width=22, bd=0, font=("Segoe UI", 9, "bold"),
              fg="#ffffff", bg="#c0392b", activebackground="#e74c3c", cursor="hand2").pack(pady=15)

    root.mainloop()


if __name__ == "__main__":
    main()
