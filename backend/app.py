from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash
import os
import uuid
from flask_mail import Mail, Message  # Für den Email-Versand

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

# Startseite: Hier wird das Upload-Formular angezeigt
@app.route('/')
def index():
    return render_template('index.html')

# Route zum Hochladen der Datei
@app.route('/upload', methods=['POST'])
def upload_file():
    # Prüfen, ob die Datei im Formular vorhanden ist
    if 'datei' not in request.files:
        flash('Keine Datei ausgewählt')
        return redirect(url_for('index'))
    file = request.files['datei']
    if file.filename == '':
        flash('Keine Datei ausgewählt')
        return redirect(url_for('index'))
    
    # Hole Email aus dem Formular (damit der Download-Link per Email versendet werden kann)
    email_address = request.form.get('email', None)
    
    # Optional: Passwort, falls eingegeben, holen (hier noch nicht weiter verarbeitet)
    password = request.form.get('password', None)
    
    if file:
        # Erstellen eines eindeutigen Dateinamens, damit keine zwei Dateien denselben Namen bekommen
        filename = str(uuid.uuid4()) + "_" + file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        # Hier könnten weitere Schritte ergänzt werden, z.B.:
        # - Speicherung von Dateiinformationen in einer Datenbank
        # - Einrichten eines Timers, der die Datei nach 7 Tagen löscht
        download_link = url_for('download_file', filename=filename, _external=True)
        
        # Sende Email, falls eine Email-Adresse angegeben wurde
        if email_address:
            try:
                msg = Message("Ihre Datei ist bereit zum Download",
                              recipients=[email_address])
                msg.body = f"Hallo,\n\nEine Datei wurde für Sie hochgeladen. Sie können die Datei unter folgendem Link herunterladen:\n{download_link}\n\nMit freundlichen Grüßen,\nIhr FileTransfer Team"
                mail.send(msg)
                flash("Email wurde gesendet!")
            except Exception as e:
                flash(f"Fehler beim Senden der Email: {e}")
        
        return render_template('upload_success.html', download_link=download_link, password=password, email_sent=(email_address is not None))
    
    return redirect(url_for('index'))

# Route zum Herunterladen der Datei
@app.route('/download/<filename>')
def download_file(filename):
    # Hier könnte optional der Passwortschutz ergänzt werden.
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
