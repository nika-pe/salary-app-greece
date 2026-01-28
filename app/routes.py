import sqlite3
import os
from flask import Blueprint, render_template, request, jsonify
from app.models.payroll import PayrollCalculator 

main_bp = Blueprint('main', __name__)
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
            contract_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@main_bp.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@main_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Просмотр истории расчетов"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM calculations ORDER BY timestamp DESC LIMIT 10")
        history = cursor.fetchall()
        conn.close()
        return render_template('dashboard.html', history=history)
    except Exception as e:
        return f"Database error: {e}", 500

@main_bp.route('/api/payroll', methods=['POST'])
def payroll_api():
    try:
        data = request.get_json()
        gross_salary = float(data['gross_salary'])
        contract_type = data.get('contract_type', 'private')

        calculator = PayrollCalculator(gross_salary, contract_type)
        result = calculator.calculate_net()

        # Сохранение в SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calculations (gross, net, contract_type) VALUES (?, ?, ?)",
            (gross_salary, result.get('net_salary'), contract_type)
        )
        conn.commit()
        conn.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500