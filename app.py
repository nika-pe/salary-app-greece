import sqlite3
import os
from flask import Blueprint, render_template, request, jsonify
from app.models.payroll import PayrollCalculator

# Создаем Blueprint один раз
main_bp = Blueprint('main', __name__)

# Путь к базе данных в корне проекта
DB_PATH = os.path.join(os.getcwd(), 'salary_agent.db')

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            gross REAL,
            net REAL,
            contract_type TEXT,
            ai_comment TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Запускаем создание БД при импорте роутов
init_db()

@main_bp.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@main_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Страница истории расчетов"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calculations ORDER BY timestamp DESC LIMIT 20")
    history = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', history=history)

@main_bp.route('/api/payroll', methods=['POST'])
def payroll_api():
    try:
        data = request.get_json()

        if not data or 'gross_salary' not in data or 'contract_type' not in data:
            return jsonify({"error": "Missing 'gross_salary' or 'contract_type'"}), 400

        gross_salary = float(data['gross_salary'])
        contract_type = data['contract_type']

        # Расчет
        calculator = PayrollCalculator(gross_salary, contract_type)
        result = calculator.calculate_net()

        # СОХРАНЕНИЕ В БАЗУ
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO calculations (gross, net, contract_type, ai_comment) VALUES (?, ?, ?, ?)",
                (gross_salary, result.get('net_salary'), contract_type, "Авто-сохранение")
            )
            conn.commit()
            conn.close()
        except Exception as db_e:
            print(f"Database error: {db_e}")

        return jsonify(result)

    except ValueError:
        return jsonify({"error": "Invalid value for 'gross_salary'."}), 400
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500
