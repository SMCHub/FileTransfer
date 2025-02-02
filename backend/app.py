from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash, jsonify
import os
import uuid
from flask_mail import Mail, Message  # Für den Email-Versand
from werkzeug.utils import secure_filename
import json
from datetime import datetime, timedelta

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
        json.dump(metadata, f, indent=4, default=str)

def send_email(recipient, subject, message):
    msg = Message(subject, recipients=[recipient])
    msg.body = message
    try:
        mail.send(msg)
        print("E-Mail erfolgreich gesendet an", recipient)
    except Exception as e:
        print("Fehler beim Senden der E-Mail:", e)

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

    # Speichere Upload-Zeit und berechne Ablaufzeit (7 Tage)
    now = datetime.utcnow()
    expiration = now + timedelta(days=7)

    # Lade bestehende Metadaten, update diese mit den neuen Informationen und speichere sie
    metadata = load_metadata()
    metadata[filename] = {
        'password': password,
        'original_filename': file.filename,
        'upload_time': now.isoformat(),
        'expiration_time': expiration.isoformat(),
        'email': email,
        'download_count': 0
    }
    save_metadata(metadata)

    # Generiere den vollständigen Download-Link
    download_link = url_for('download_file', filename=filename, _external=True)
    
    # Falls eine E-Mail angegeben wurde, sende den Download-Link per E-Mail
    if email:
        subject = "Dein FileTransfer Download-Link"
        message = (
            f"Hallo,\n\nDein Download-Link lautet: {download_link}\n\n"
            "Bitte beachte, dass der Link in 7 Tagen abläuft.\n\nViele Grüße,\nDein FileTransfer Team"
        )
        send_email(email, subject, message)

    # Generiere Redirect-URL zur Upload-Erfolgsseite
    redirect_url = url_for('upload_success', filename=filename)

    # Wenn der Request per AJAX (XMLHttpRequest) erfolgt, liefern wir eine JSON-Antwort
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'redirect_url': redirect_url})
    else:
        return redirect(redirect_url)

@app.route('/upload_success')
def upload_success():
    filename = request.args.get('filename')
    if not filename:
        return redirect(url_for('index'))
    data = load_metadata().get(filename)
    if not data:
        return "Upload-Daten nicht gefunden", 404
    download_link = url_for('download_file', filename=filename, _external=True)
    return render_template('upload_success.html',
                           download_link=download_link,
                           original_filename=data.get('original_filename'),
                           password=data.get('password'),
                           email_sent=True)

# Route zum Herunterladen der Datei
@app.route('/download/<filename>', methods=['GET', 'POST'])
def download_file(filename):
    # Lade die Metadaten aus der JSON-Datei
    metadata = load_metadata()
    info = metadata.get(filename)
    if not info:
        return "Datei nicht gefunden!", 404

    # Prüfe, ob die Datei abgelaufen ist
    expiration_time = datetime.fromisoformat(info.get('expiration_time'))
    if datetime.utcnow() > expiration_time:
        return "Der Download-Link ist abgelaufen!", 410

    required_password = info.get('password')
    if required_password:  # Falls die Datei passwortgeschützt ist
        if request.method == 'POST':
            provided_password = request.form.get('password')
            if provided_password == required_password:
                # Passwort korrekt → Datei zum Download anbieten
                # Nach erfolgreichem Download wird der Download-Zähler erhöht
                info['download_count'] = info.get('download_count', 0) + 1
                metadata[filename] = info
                save_metadata(metadata)
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
        # Nach erfolgreichem Download wird der Download-Zähler erhöht
        info['download_count'] = info.get('download_count', 0) + 1
        metadata[filename] = info
        save_metadata(metadata)
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], filename,
            as_attachment=True, download_name=info.get('original_filename', filename)
        )

@app.route('/admin')
def admin_panel():
    # Einfaches Admin-Panel (ohne Authentifizierung)
    metadata = load_metadata()
    uploads = []
    for fname, data in metadata.items():
        uploads.append({
            'filename': fname,
            'original_filename': data.get('original_filename'),
            'upload_time': data.get('upload_time'),
            'expiration_time': data.get('expiration_time'),
            'email': data.get('email'),
            'download_count': data.get('download_count')
        })
    return render_template('admin.html', uploads=uploads)

@app.route('/cleanup')
def cleanup():
    # Diese Route durchsucht die Uploads, löscht abgelaufene Dateien und sendet Benachrichtigungen per E-Mail.
    metadata = load_metadata()
    now = datetime.utcnow()
    removed = []
    for filename, data in list(metadata.items()):
        expiration_time = datetime.fromisoformat(data.get('expiration_time'))
        if now > expiration_time:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            recipient = data.get('email')
            subject = "Deine Datei ist abgelaufen"
            message = f"Die Datei '{data.get('original_filename')}' ist abgelaufen und wurde entfernt."
            send_email(recipient, subject, message)
            removed.append(filename)
            del metadata[filename]
    save_metadata(metadata)
    return f"Aufgeräumt: {', '.join(removed)}" if removed else "Keine Dateien zu entfernen."

if __name__ == '__main__':
    app.run(debug=True)
