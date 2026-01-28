import os
import sqlite3
import pandas as pd
from flask import Flask, render_template, request
from salary_greece import calculate_salary 

app = Flask(__name__)
DB_NAME = "salary_agent.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            brutto REAL,
            net REAL,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        try:
            brutto = float(request.form.get("brutto", 0))
            category = request.form.get("category", "misthotos")
            
            # Твой расчет из salary_greece.py
            net, ika, tax = calculate_salary(brutto, category)
            result = {'brutto': brutto, 'net': net, 'ika': ika, 'tax': tax, 'category': category}
            
            # Сохраняем в память
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO calculations (brutto, net, category) VALUES (?, ?, ?)",
                           (brutto, net, category))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка: {e}")

    # Получаем историю для отображения
    conn = sqlite3.connect(DB_NAME)
    history = pd.read_sql_query("SELECT timestamp, brutto, net FROM calculations ORDER BY timestamp DESC LIMIT 5", conn)
    conn.close()

    return render_template("index.html", result=result, history=history.to_dict(orient='records'))

if __name__ == "__main__":
    app.run(debug=True)
