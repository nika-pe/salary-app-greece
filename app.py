import os
import io
import pandas as pd
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from salary_greece import calculate_salary

# Initialization of Flask application
app = Flask(__name__)

# Folder for temporary storage of uploaded files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Maximum file size 16 MB

# Allowed file extensions
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf'}

def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"]) # УБЕДИТЕСЬ, ЧТО ЗДЕСЬ ЕСТЬ methods=["GET", "POST"]
def index():
    """
    Main route for the salary calculator.
    Handles GET requests (displaying the form) and POST requests (salary calculation).
    """
    # Initialization of variables for results and messages
    result = False
    ika = 0.0
    tax = 0.0
    net = 0.0
    brutto_input = ''  # To preserve the value in the brutto input field
    category_input = 'misthotos'  # To preserve the selected category
    upload_message = None # Message about file upload status
    report_data = None # Data for report display

    if request.method == "POST":
        # Check if the request is a POST request for salary calculation
        # (i.e., if it contains 'brutto' and 'category' fields)
        if 'brutto' in request.form and 'category' in request.form:
            try:
                brutto = float(request.form["brutto"])
                brutto_input = brutto
                category = request.form["category"]
                category_input = category

                net, ika, tax = calculate_salary(brutto, category)
                result = True
            except ValueError:
                upload_message = "Σφάλμα: Εισήχθη μη έγκυρη τιμή για τον μικτό μισθό."
            except KeyError:
                upload_message = "Σφάλμα: Λείπουν τα απαιτούμενα πεδία φόρμας (μικτός ή κατηγορία)."
            except Exception as e:
                upload_message = f"Προέκυψε απρόβλεπτο σφάλμα κατά τον υπολογισμό: {e}"
        else:
            # If it's not a salary calculation, it might be another POST request form,
            # but /download_excel and /upload_data have their own routes.
            # This branch should ideally not be reached during correct operation.
            pass

    # Pass variables to the template
    return render_template("index.html", result=result, ika=ika, tax=tax, net=net,
                           brutto_input=brutto_input, category_input=category_input,
                           upload_message=upload_message, report_data=report_data)

@app.route("/download_excel", methods=["POST"])
def download_excel():
    """
    Handles the request to download calculation results in Excel format.
    """
    try:
        brutto = float(request.form["brutto"])
        category = request.form["category"]
        net = float(request.form["net"])
        ika = float(request.form["ika"])
        tax = float(request.form["tax"])

        data = {
            "Παράμετρος": ["Μικτός μισθός", "Κατηγορία", "Καθαρός μισθός", "ΙΚΑ (ασφάλιση)", "Φόρος"],
            "Τιμή": [brutto, category, net, ika, tax]
        }
        df = pd.DataFrame(data)

        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Υπολογισμός Μισθού')
        writer.close()
        output.seek(0)

        return send_file(output,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         download_name='salary_calculation.xlsx',
                         as_attachment=True)
    except Exception as e:
        print(f"Error creating or downloading Excel file: {e}")
        return "Προέκυψε σφάλμα κατά τη δημιουργία του αρχείου Excel.", 500

@app.route('/upload_data', methods=['POST'])
def upload_data():
    """
    Handles file uploads (Excel or PDF).
    """
    upload_message = None
    if 'file' not in request.files:
        upload_message = "Δεν επιλέχθηκε αρχείο."
    file = request.files['file']
    if file.filename == '':
        upload_message = "Δεν επιλέχθηκε αρχείο."
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Process the file based on its type
        if filename.lower().endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(filepath)
                # Here you can add logic to process data from Excel
                # For example, save them to a database or process them
                print(f"Excel αρχείο '{filename}' φορτώθηκε και διαβάστηκε επιτυχώς.") # Console message
                print("Πρώτες 5 γραμμές δεδομένων:") # Console message
                print(df.head()) # Console message
                upload_message = f"Το αρχείο '{filename}' φορτώθηκε και επεξεργάστηκε επιτυχώς ως Excel."
            except Exception as e:
                upload_message = f"Σφάλμα κατά την ανάγνωση του αρχείου Excel '{filename}': {e}"
        elif filename.lower().endswith('.pdf'):
            # PDF parsing requires more complex logic.
            # Here we just confirm the upload.
            print(f"PDF αρχείο '{filename}' φορτώθηκε επιτυχώς.") # Console message
            upload_message = f"Το αρχείο PDF '{filename}' φορτώθηκε επιτυχώς. (Η επεξεργασία PDF απαιτεί πρόσθετες βιβλιοθήκες)"
        else:
            upload_message = f"Μη υποστηριζόμενος τύπος αρχείου: {filename}"

        # Delete the temporary file after processing
        os.remove(filepath)
    else:
        upload_message = "Μη έγκυρος τύπος αρχείου. Επιτρέπονται μόνο .xlsx, .xls, .pdf."

    # Return to the main page with the upload message
    return render_template("index.html", upload_message=upload_message)


@app.route('/generate_report', methods=['GET'])
def generate_report():
    """
    Generates a simplified report.
    In a real application, this would involve logic to process uploaded data
    and generate a summary report.
    """
    # Example report data (can be replaced with data from uploaded files)
    sample_report_data = """
    --- Συνοπτική Αναφορά ---
    Ημερομηνία αναφοράς: 01.07.2025
    Σύνολο υπολογισμών που έγιναν: 10
    Μέσος καθαρός μισθός (Μισθωτός): 1200.50 €
    Μέσος καθαρός μισθός (Ελεύθερος επαγγελματίας): 950.75 €
    Μέσος καθαρός μισθός (Δημόσιος υπάλληλος): 1100.20 €
    --------------------
    """
    # In a real application, aggregation and analysis of data
    # from a database (where calculation results or uploaded data would be stored)
    # would occur here.

    return render_template("index.html", report_data=sample_report_data)


if __name__ == "__main__":
    app.run(debug=True)
