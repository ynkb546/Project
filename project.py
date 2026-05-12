import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

interactive_data = {
    'df': None,
    'batches': [],
    'last_date': None,
    'q_value': 0,
    'shelf_life': 0,
    'storage_cost': 0,
    'price': 0
}

plt.rcParams['figure.facecolor'] = '#1a1c1e'
plt.rcParams['axes.facecolor'] = '#212529'
plt.rcParams['text.color'] = '#ffffff'
plt.rcParams['xtick.color'] = '#b2bdc6'
plt.rcParams['ytick.color'] = '#b2bdc6'
plt.rcParams['axes.labelcolor'] = '#ffffff'
plt.rcParams['axes.edgecolor'] = '#4f545c'


def main():
    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Выберите файл с данными о поставках (CSV)",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if not file_path: return
    table_name = os.path.splitext(os.path.basename(file_path))[0]

    try:
        data = pd.read_csv(file_path, sep=',')
    except Exception as e:
        messagebox.showerror("Ошибка", f"Файл не прочитан: {e}")
        return

    available_products = sorted(data['Наименование товара'].dropna().unique())
    if not available_products:
        messagebox.showerror("Ошибка", "Не найдены товары в файле.")
        return

    setup_win = tk.Toplevel(root)
    setup_win.title("Настройки симуляции")
    setup_win.geometry("450x280")
    setup_win.configure(bg="#212529")
    setup_win.resizable(False, False)

    setup_win.update_idletasks()
    x = (setup_win.winfo_screenwidth() // 2) - (450 // 2)
    y = (setup_win.winfo_screenheight() // 2) - (280 // 2)
    setup_win.geometry(f"+{x}+{y}")

    setup_win.grab_set()

    prod_var = tk.StringVar(value=available_products[0])
    shelf_var = tk.IntVar(value=4)
    cost_var = tk.DoubleVar(value=1.5)

    user_confirmed = False

    def on_submit():
        nonlocal user_confirmed
        try:
            if shelf_var.get() < 1:
                raise ValueError("Срок годности должен быть >= 1")
            if cost_var.get() < 0:
                raise ValueError("Стоимость хранения не может быть отрицательной")
            user_confirmed = True
            setup_win.destroy()
        except tk.TclError:
            messagebox.showwarning("Внимание", "Пожалуйста, введите корректные числа", parent=setup_win)
        except ValueError as e:
            messagebox.showwarning("Внимание", str(e), parent=setup_win)

    tk.Label(setup_win, text="⚙ НАСТРОЙКИ", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#212529").pack(
        pady=15)

    form_frame = tk.Frame(setup_win, bg="#212529")
    form_frame.pack(fill="both", expand=True, padx=20)

    style = ttk.Style()
    style.theme_use('clam')

    tk.Label(form_frame, text="Выберите товар:", font=("Segoe UI", 9), fg="#b2bdc6", bg="#212529").grid(row=0, column=0,
                                                                                                        sticky="w",
                                                                                                        pady=10)
    combo_prod = ttk.Combobox(form_frame, textvariable=prod_var, values=available_products, state="readonly", width=30)
    combo_prod.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(form_frame, text="Срок годности (недели):", font=("Segoe UI", 9), fg="#b2bdc6", bg="#212529").grid(row=1,
                                                                                                                column=0,
                                                                                                                sticky="w",
                                                                                                                pady=10)
    spin_shelf = ttk.Spinbox(form_frame, from_=1, to=1000, textvariable=shelf_var, width=10)
    spin_shelf.grid(row=1, column=1, sticky="w", padx=10, pady=10)

    tk.Label(form_frame, text="Стоимость хранения (руб):", font=("Segoe UI", 9), fg="#b2bdc6", bg="#212529").grid(row=2,
                                                                                                                  column=0,
                                                                                                                  sticky="w",
                                                                                                                  pady=10)
    entry_cost = ttk.Entry(form_frame, textvariable=cost_var, width=12)
    entry_cost.grid(row=2, column=1, sticky="w", padx=10, pady=10)

    btn_submit = tk.Button(setup_win, text="ПРОДОЛЖИТЬ", command=on_submit, bg="#27ae60", fg="#ffffff",
                           font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", width=20, height=1)
    btn_submit.pack(pady=15)

    root.wait_window(setup_win)

    if not user_confirmed:
        return

    selected_product = prod_var.get()
    shelf_life = shelf_var.get()
    storage_cost_per_week = cost_var.get()

    packs_data = data[data['Количество'].apply(lambda x: float(x).is_integer())]
    weight_data = data[~data['Количество'].apply(lambda x: float(x).is_integer())]

    kol_packs = packs_data['Количество'].sum()
    kol_weight = weight_data['Количество'].sum()

    sorted_total_packs = packs_data.groupby(['Товарная группа', 'Код товара', 'Наименование товара'])[
        'Количество'].sum().reset_index().sort_values(by='Количество', ascending=False)
    sorted_total_weight = weight_data.groupby(['Товарная группа', 'Код товара', 'Наименование товара'])[
        'Количество'].sum().reset_index().sort_values(by='Количество', ascending=False)

    top_5_weight = sorted_total_weight.head(5)
    top_5_packs = sorted_total_packs.head(5)
    merged_weight = pd.merge(data, top_5_weight[['Товарная группа', 'Код товара']],
                             on=['Товарная группа', 'Код товара'])
    merged_weight['Дата'] = pd.to_datetime(merged_weight['Дата'])
    weekly_weight = merged_weight.groupby(['Наименование товара', pd.Grouper(key='Дата', freq='W')])[
        'Количество'].sum().reset_index()
    grafic_data = weekly_weight.melt(id_vars=['Дата', 'Наименование товара'], value_vars='Количество',
                                     var_name='Метрика', value_name='Значение')

    cumulative_quantity = weekly_weight.copy()
    cumulative_quantity['Количество'] = cumulative_quantity.groupby('Наименование товара')['Количество'].cumsum()

    product_data = data[data['Наименование товара'] == selected_product].copy()
    product_data['Дата'] = pd.to_datetime(product_data['Дата'])

    value_for_kg = np.ceil(
        product_data['Сумма к оплате'].sum() / product_data['Количество'].sum()) if not product_data.empty else 0
    product_weekly = product_data.groupby(pd.Grouper(key='Дата', freq='W'))['Количество'].sum()

    product_q_values = {q: (product_weekly.quantile(float(q)) if not product_weekly.empty else 0) for q in
                        ['0.25', '0.50', '0.75', '0.85', '0.95']}

    def run_simulation(target_quantile_val):
        if product_data.empty: return pd.DataFrame(), []
        current_date = product_data['Дата'].min()
        max_date = product_data['Дата'].max()
        stock_batches = []
        deliveries = []

        while current_date <= max_date:
            next_date = current_date + pd.DateOffset(days=7)
            q_ceil = np.ceil(target_quantile_val)

            c_stock = sum(b['qty'] for b in stock_batches)
            deliv_qty = int(max(0, q_ceil - c_stock))
            if deliv_qty > 0: stock_batches.append({'qty': deliv_qty, 'weeks_left': shelf_life})

            start_stock = sum(b['qty'] for b in stock_batches)
            demand = product_data[(product_data['Дата'] >= current_date) & (product_data['Дата'] < next_date)][
                'Количество'].sum()

            to_sell = demand
            sold = 0
            for b in stock_batches:
                if to_sell <= 0: break
                take = min(b['qty'], to_sell)
                b['qty'] -= take
                to_sell -= take
                sold += take

            expired = 0
            active = []
            for b in stock_batches:
                b['weeks_left'] -= 1
                if b['weeks_left'] <= 0:
                    expired += b['qty']
                elif b['qty'] > 0:
                    active.append(b)
            stock_batches = active

            missed_money = to_sell * value_for_kg
            exp_money = expired * value_for_kg

            deliveries.append({
                'Дата': current_date,
                'Поставка, шт': deliv_qty,
                'Остаток начало, шт/кг': start_stock,
                'Спрос за неделю, шт/кг': demand,
                'Продано, шт/кг': sold,
                'Списано по сроку, шт/кг': expired,
                'Остаток конец, шт/кг': sum(b['qty'] for b in stock_batches),
                'Стоимость хранения, руб': start_stock * storage_cost_per_week,
                'Прибыль от продаж, руб': sold * value_for_kg,
                'Чистая прибыль, руб': (sold * value_for_kg) - (start_stock * storage_cost_per_week),
                'Упущенная выгода (дефицит), руб': missed_money,
                'Убыток от списаний, руб': exp_money,
                'Общая потерянная прибыль, руб': missed_money + exp_money
            })
            current_date = next_date
        return pd.DataFrame(deliveries), stock_batches

    comparison = []
    best_profit = -float('inf')
    best_q_name = ""
    best_df = None
    best_batches = []

    for q_name, q_val in product_q_values.items():
        sim_df, final_batches = run_simulation(q_val)
        net_p = sim_df['Чистая прибыль, руб'].sum() if not sim_df.empty else 0
        comparison.append({
            'Квантиль': q_name,
            'Общая чистая прибыль, руб': net_p,
            'Упущенная выгода, руб': sim_df['Общая потерянная прибыль, руб'].sum() if not sim_df.empty else 0,
            'Всего списано': sim_df['Списано по сроку, шт/кг'].sum() if not sim_df.empty else 0
        })
        if net_p > best_profit:
            best_profit = net_p
            best_q_name = q_name
            best_df = sim_df
            best_batches = final_batches

    comparison_df = pd.DataFrame(comparison)

    interactive_data['df'] = best_df.copy() if best_df is not None else pd.DataFrame()
    interactive_data['batches'] = best_batches
    interactive_data['last_date'] = pd.to_datetime(
        best_df['Дата'].iloc[-1]) if (best_df is not None and not best_df.empty) else pd.Timestamp.now()
    interactive_data['q_value'] = product_q_values[best_q_name]
    interactive_data['shelf_life'] = shelf_life
    interactive_data['storage_cost'] = storage_cost_per_week
    interactive_data['price'] = value_for_kg

    def show_dataframe_window(df, title):
        top = tk.Toplevel(root)
        top.title(title)
        top.geometry("1150x550")
        top.configure(bg="#1a1c1e")

        header_frame = tk.Frame(top, bg="#212529", height=50)
        header_frame.pack(fill="x", side="top")
        header_label = tk.Label(header_frame, text=title.upper(), font=("Segoe UI", 11, "bold"), fg="#ffffff",
                                bg="#212529")
        header_label.pack(pady=12, padx=15, side="left")

        table_frame = tk.Frame(top, bg="#1a1c1e")
        table_frame.pack(fill="both", expand=True, padx=15, pady=15)

        display_df = df.copy()
        for col in display_df.columns:
            if pd.api.types.is_datetime64_any_dtype(display_df[col]):
                display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')
            elif pd.api.types.is_float_dtype(display_df[col]):
                display_df[col] = display_df[col].round(2)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#212529",
                        foreground="#ffffff",
                        fieldbackground="#212529",
                        rowheight=28,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
                        background="#2f343a",
                        foreground="#ffffff",
                        bordercolor="#1a1c1e",
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#3a3f44")])
        scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")

        tree = ttk.Treeview(table_frame, columns=list(display_df.columns), show="headings",
                            yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        for col in display_df.columns:
            tree.heading(col, text=col)
            anchor_pos = "center" if pd.api.types.is_numeric_dtype(df[col]) else "w"

            max_len = max(display_df[col].astype(str).map(len).max(), len(col)) if not display_df.empty else len(col)
            col_width = min(max(max_len * 9, 110), 320)
            tree.column(col, width=col_width, anchor=anchor_pos)

        scroll_y.config(command=tree.yview)
        scroll_x.config(command=tree.xview)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)

        for idx, row in display_df.iterrows():
            tree.insert("", "end", values=list(row))

    def add_interactive_week():
        new_date = interactive_data['last_date'] + pd.DateOffset(days=7)
        q_target = np.ceil(interactive_data['q_value'])

        current_stock = sum(b['qty'] for b in interactive_data['batches'])
        delivery = int(max(0, q_target - current_stock))

        import tkinter.simpledialog as sd
        user_sales = sd.askfloat("Новая неделя",
                                 f"Дата: {new_date.strftime('%Y-%m-%d')}\n"
                                 f"Рекомендуемая поставка: {delivery} ед.\n"
                                 f"Будет на складе с поставкой: {current_stock + delivery} ед.\n\n"
                                 f"Введите фактический объем продаж за неделю:")

        if user_sales is None: return

        if delivery > 0:
            interactive_data['batches'].append({'qty': delivery, 'weeks_left': interactive_data['shelf_life']})

        start_stock = sum(b['qty'] for b in interactive_data['batches'])
        to_sell = user_sales
        sold = 0
        for b in interactive_data['batches']:
            if to_sell <= 0: break
            take = min(b['qty'], to_sell)
            b['qty'] -= take
            to_sell -= take
            sold += take

        expired = 0
        active = []
        for b in interactive_data['batches']:
            b['weeks_left'] -= 1
            if b['weeks_left'] <= 0:
                expired += b['qty']
            elif b['qty'] > 0:
                active.append(b)
        interactive_data['batches'] = active

        new_row = {
            'Дата': new_date, 'Поставка, шт': delivery,
            'Остаток начало, шт/кг': start_stock, 'Спрос за неделю, шт/кг': user_sales,
            'Продано, шт/кг': sold, 'Списано по сроку, шт/кг': expired,
            'Остаток конец, шт/кг': sum(b['qty'] for b in interactive_data['batches']),
            'Стоимость хранения, руб': start_stock * interactive_data['storage_cost'],
            'Прибыль от продаж, руб': sold * interactive_data['price'],
            'Чистая прибыль, руб': (sold * interactive_data['price']) - (
                    start_stock * interactive_data['storage_cost']),
            'Упущенная выгода (дефицит), руб': to_sell * interactive_data['price'],
            'Убыток от списаний, руб': expired * interactive_data['price'],
            'Общая потерянная прибыль, руб': (to_sell + expired) * interactive_data['price']
        }

        interactive_data['df'] = pd.concat([interactive_data['df'], pd.DataFrame([new_row])], ignore_index=True)
        interactive_data['last_date'] = new_date
        show_dataframe_window(interactive_data['df'], "Обновленный интерактивный прогноз")

    def show_pie_chart():
        plt.figure(figsize=(7, 5))
        sizes = [kol_weight, kol_packs]
        labels = ['Развесные товары', 'Товары в упаковках']
        colors = ['#5865F2', '#F47B67']

        wedges, texts, autotexts = plt.pie(
            sizes, labels=labels, autopct='%1.1f%%',
            startangle=90, colors=colors,
            textprops=dict(color="#ffffff", weight="bold"),
            wedgeprops=dict(width=0.4, edgecolor='#1a1c1e', linewidth=2)
        )
        plt.setp(texts, size=10)
        plt.setp(autotexts, size=10)
        plt.title(f'Соотношение продаж\n(Таблица: {table_name})', fontsize=12, weight='bold', pad=15)
        plt.show()

    def show_packs_bar():
        plt.figure(figsize=(10, 5))
        ax = plt.subplot(111)

        bars = sns.barplot(
            x='Количество', y='Наименование товара',
            data=top_5_packs, palette='viridis', ax=ax
        )

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#4f545c')
        ax.spines['bottom'].set_color('#4f545c')

        for bar in bars.patches:
            val = bar.get_width()
            ax.text(
                val + (max(top_5_packs['Количество']) * 0.015),
                bar.get_y() + bar.get_height() / 2,
                f'{int(val):,}',
                va='center', ha='left', color='#ffffff', fontweight='bold', fontsize=9
            )

        plt.title(f'Топ-5 продаж поштучно/в пачках\n(Таблица: {table_name})', fontsize=12, weight='bold', pad=15)
        plt.tight_layout()
        plt.show()

    def show_weight_bar():
        plt.figure(figsize=(10, 5))
        ax = plt.subplot(111)

        bars = sns.barplot(
            x='Количество', y='Наименование товара',
            data=top_5_weight, palette='magma', ax=ax
        )

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#4f545c')
        ax.spines['bottom'].set_color('#4f545c')

        for bar in bars.patches:
            val = bar.get_width()
            ax.text(
                val + (max(top_5_weight['Количество']) * 0.015),
                bar.get_y() + bar.get_height() / 2,
                f'{int(val):,}',
                va='center', ha='left', color='#ffffff', fontweight='bold', fontsize=9
            )

        plt.title(f'Топ-5 продаж на развес\n(Таблица: {table_name})', fontsize=12, weight='bold', pad=15)
        plt.tight_layout()
        plt.show()

    def show_plotly_w():
        px.line(grafic_data, x='Дата', y='Значение', color='Наименование товара', template='plotly_white',
                title=f"Продажи по неделям ({table_name})").show()

    def show_plotly_c():
        px.line(cumulative_quantity, x='Дата', y='Количество', color='Наименование товара', template='plotly_white',
                title=f"Накопление ({table_name})").show()

    root.deiconify()
    root.title("Аналитика запасов")
    root.geometry("560x580")
    root.configure(bg="#1a1c1e")

    top_bar = tk.Frame(root, bg="#212529", height=65)
    top_bar.pack(fill="x", side="top")

    title_label = tk.Label(top_bar, text="📊 УПРАВЛЕНИЕ ЗАПАСАМИ", font=("Segoe UI", 12, "bold"), fg="#ffffff",
                           bg="#212529")
    title_label.pack(pady=10)

    sub_label = tk.Label(root, text=f"Файл: {table_name}   |   Товар: {selected_product}",
                         font=("Segoe UI", 9, "italic"), fg="#9e9e9e", bg="#1a1c1e")
    sub_label.pack(pady=8)

    menu_buttons = [
        ("1. Диаграмма: Соотношение", show_pie_chart, "#3a3f44", "#4e545c"),
        ("2. Диаграмма: Топ-5 Пачки", show_packs_bar, "#3a3f44", "#4e545c"),
        ("3. Диаграмма: Топ-5 Развес", show_weight_bar, "#3a3f44", "#4e545c"),
        ("4. График: Динамика продаж (Plotly)", show_plotly_w, "#3a3f44", "#4e545c"),
        ("5. График: Накопление продаж (Plotly)", show_plotly_c, "#3a3f44", "#4e545c"),
        ("6. Таблица: Продажи по неделям", lambda: show_dataframe_window(weekly_weight, "Продажи по неделям"),
         "#2c3e50", "#34495e"),
        ("7. Сравнение стратегий",
         lambda: show_dataframe_window(comparison_df, "Сравнение стратегий поставок"), "#b7950b", "#d4ac0d"),
        ("8. Лучший прогноз(" + best_q_name + ")",
         lambda: show_dataframe_window(interactive_data['df'], f"Детализация лучшего прогноза ({best_q_name})"),
         "#27ae60", "#2ecc71"),
        ("9. Добавить неделю продаж", add_interactive_week, "#2980b9", "#3498db")
    ]
    def on_enter(e, hover_color):
        e.widget['background'] = hover_color

    def on_leave(e, normal_color):
        e.widget['background'] = normal_color

    for txt, cmd, bg_color, hover_color in menu_buttons:
        btn = tk.Button(
            root, text=txt, command=cmd,
            width=58, height=1, bd=0, relief="flat",
            font=("Segoe UI", 9, "bold"), fg="#ffffff", bg=bg_color,
            activebackground=hover_color, activeforeground="#ffffff", cursor="hand2"
        )
        btn.pack(pady=4)
        btn.bind("<Enter>", lambda e, h=hover_color: on_enter(e, h))
        btn.bind("<Leave>", lambda e, n=bg_color: on_leave(e, n))

    exit_btn = tk.Button(
        root, text="ВЫХОД", command=root.destroy,
        width=22, bd=0, relief="flat",
        font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#c0392b",
        activebackground="#e74c3c", activeforeground="#ffffff", cursor="hand2"
    )
    exit_btn.pack(pady=15)
    exit_btn.bind("<Enter>", lambda e: on_enter(e, "#e74c3c"))
    exit_btn.bind("<Leave>", lambda e: on_leave(e, "#c0392b"))

    root.mainloop()


if __name__ == "__main__":
    main()