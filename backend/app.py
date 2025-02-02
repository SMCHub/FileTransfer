from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash
import os
import uuid
from flask_mail import Mail, Message  # Für den Email-Versand
from werkzeug.utils import secure_filename
import json

app = Flask(__name__, static_folder='../static', static_url_path='/static')
app.secret_key = 'dein_geheimer_schluessel'  # Ändere diesen Schlüssel in etwas Einzigartiges!

# Konfiguration für Flask-Mail (SMTP-Verbindung)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'      # Beispiel: Gmail SMTP-Server
app.config['MAIL_PORT'] = 587                     # Port für TLS-Verschlüsselung
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'info@bonlivre.ch'  # Gib hier Deine Email-Adresse ein!
app.config['MAIL_PASSWORD'] = 'ejtj dtho zbdc jlsh'          # Gib hier Dein Email-Passwort oder App-Passwort ein!
app.config['MAIL_DEFAULT_SENDER'] = ('FileTransfer', 'deine_email@gmail.com')

mail = Mail(app)

# Legt den Ordner fest, in dem hochgeladene Dateien gespeichert werden
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # Maximale Dateigröße: 100 MB

# Funktionen für persistente Speicherung der Metadaten in metadata.json
def load_metadata():
    metadata_file = os.path.join(app.config['UPLOAD_FOLDER'], 'metadata.json')
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    else:
        return {}

def save_metadata(metadata):
    metadata_file = os.path.join(app.config['UPLOAD_FOLDER'], 'metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f)

# Startseite: Hier wird das Upload-Formular angezeigt
@app.route('/')
def index():
    return render_template('index.html')

# Route zum Hochladen der Datei
@app.route('/upload', methods=['POST'])
def upload_file():
    # Prüfe, ob die Datei im Formular enthalten ist
    if 'datei' not in request.files:
        # Hier kannst Du eine Fehlermeldung anzeigen
        return "Keine Datei gefunden!", 400
    file = request.files['datei']
    if file.filename == "":
        # Prüfe, ob ein Dateiname vorhanden ist
        return "Keine Datei ausgewählt", 400
    
    # Sichere den Dateinamen
    filename = secure_filename(file.filename)
    # Speichere die Datei in den Upload-Ordner
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    # Holen der anderen Formularfelder
    email = request.form.get('email')
    password = request.form.get('password')  # kann leer sein

    # Lade bestehende Metadaten, update diese mit den neuen Informationen und speichere sie
    metadata = load_metadata()
    metadata[filename] = {
        'password': password,
        'original_filename': file.filename
    }
    save_metadata(metadata)

    # Weiterverarbeitung (Zum Beispiel Download-Link generieren)
    download_link = url_for('download_file', filename=filename, _external=True)
    
    # Sende Email, falls eine Email-Adresse angegeben wurde
    if email:
        try:
            msg = Message("Ihre Datei ist bereit zum Download",
                          recipients=[email])
            msg.body = f"Hallo,\n\nEine Datei wurde für Sie hochgeladen. Sie können die Datei unter folgendem Link herunterladen:\n{download_link}\n\nMit freundlichen Grüßen,\nIhr FileTransfer Team"
            mail.send(msg)
            flash("Email wurde gesendet!")
        except Exception as e:
            flash(f"Fehler beim Senden der Email: {e}")
    
    return render_template('upload_success.html', download_link=download_link, original_filename=file.filename, password=password, email_sent=(email is not None))

# Route zum Herunterladen der Datei
@app.route('/download/<filename>', methods=['GET', 'POST'])
def download_file(filename):
    # Lade die Metadaten aus der JSON-Datei
    metadata = load_metadata()
    info = metadata.get(filename)
    if not info:
        return "Datei nicht gefunden!", 404

    required_password = info.get('password')
    if required_password:  # Falls die Datei passwortgeschützt ist
        if request.method == 'POST':
            provided_password = request.form.get('password')
            if provided_password == required_password:
                # Passwort korrekt → Datei zum Download anbieten
                return send_from_directory(
                    app.config['UPLOAD_FOLDER'], filename,
                    as_attachment=True, download_name=info.get('original_filename', filename)
                )
            else:
                error = "Falsches Passwort."
                return render_template('download.html', filename=filename, error=error, password_required=True)
        else:
            # Passwortabfrage anzeigen
            return render_template('download.html', filename=filename, password_required=True)
    else:
        # Kein Passwort erforderlich
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], filename,
            as_attachment=True, download_name=info.get('original_filename', filename)
        )

if __name__ == '__main__':
    app.run(debug=True)
