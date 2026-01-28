import os
import io
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from salary_greece import calculate_salary

# --- ВАЖНО: OpenAI подключаем здесь, когда получишь ключ ---
# import openai

app = Flask(__name__)

# Настройки папок и безопасности
UPLOAD_FOLDER = 'uploads'
DB_NAME = "salary_agent.db"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf'}

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ (ПАМЯТЬ АΓЕНТА) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            brutto REAL,
            category TEXT,
            net REAL,
            source_file TEXT,
            ai_comment TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ВСΠΟΜΟΓАТЕЛЬНЫЕ ФУНКЦИИ ---
def save_to_history(brutto, category, net, source, comment):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO calculations (brutto, category, net, source_file, ai_comment) VALUES (?, ?, ?, ?, ?)",
                   (brutto, category, net, source, comment))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_NAME)
    # Читаем последние 10 записей через Pandas
    try:
        df = pd.read_sql_query("SELECT * FROM calculations ORDER BY timestamp DESC LIMIT 10", conn)
        return df.to_dict(orient='records')
    except:
        return []
    finally:
        conn.close()

# --- ОСНОВНЫЕ МАРШРУТЫ (ROUTES) ---

@app.route("/", methods=["GET", "POST"])
def index():
    result = False
    ika, tax, net = 0.0, 0.0, 0.0
    brutto_input = ''
    category_input = 'misthotos'
    upload_message = None

    if request.method == "POST":
        if 'brutto' in request.form and 'category' in request.form:
            try:
                brutto = float(request.form["brutto"])
                category = request.form["category"]
                
                # Расчет через твой модуль
                net, ika, tax = calculate_salary(brutto, category)
                
                # Сохраняем в историю (Память)
                save_to_history(brutto, category, net, "Manual Entry", "Υπολογισμός από χρήστη")
                
                result = True
                brutto_input = brutto
                category_input = category
            except ValueError:
                upload_message = "Σφάλμα: Μη έγκυρη τιμή μισθού."

    history = get_history()
    return render_template("index.html", result=result, ika=ika, tax=tax, net=net,
                           brutto_input=brutto_input, category_input=category_input,
                           upload_message=upload_message, history=history)

@app.route("/download_excel", methods=["POST"])
def download_excel():
    try:
        data = {
            "Παράμετρος": ["Μικτός μισθός", "Κατηγορία", "Καθαρός μισθός", "ΙΚΑ", "Φόρος"],
            "Τιμή": [request.form["brutto"], request.form["category"], 
                    request.form["net"], request.form["ika"], request.form["tax"]]
        }
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Salary')
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         download_name='salary_calculation.xlsx', as_attachment=True)
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/upload_data', methods=['POST'])
def upload_data():
    if 'file' not in request.files:
        return "No file", 400
    
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # ЛОГИКА АГЕНТА: Обработка файлов
        if filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(filepath)
            upload_message = f"Το αρχείο '{filename}' επεξεργάστηκε επιτυχώς."
        elif filename.lower().endswith('.pdf'):
            # ТУТ БУДЕТ ВЫЗОВ OpenAI (AI Act Compliance)
            upload_message = f"Το PDF '{filename}' φορτώθηκε. Έτοιμο για ανάλυση AI."
        
        os.remove(filepath) # Чистим за собой
        return render_template("index.html", upload_message=upload_message, history=get_history())
    
    return "Invalid file type", 400

@app.route('/generate_report', methods=['GET'])
def generate_report():
    # Агент анализирует историю и выдает инсайт
    history = get_history()
    if not history:
        report_text = "Δεν υπάρχουν δεδομένα για αναφορά."
    else:
        avg_net = sum(item['net'] for item in history) / len(history)
        report_text = f"Συνοπτική Αναφορά: Ο μέσος καθαρός μισθός σας είναι {avg_net:.2f}€."
    
    return render_template("index.html", report_data=report_text, history=history)

if __name__ == "__main__":
    app.run(debug=True)
