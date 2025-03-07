from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
import json
import datetime
import os
import random
import string

app = Flask(__name__)
app.secret_key = "fantaprof_secret_key"  # Chiave per gestire sessioni e flash messages

DATA_FILE = "data.json"

def load_data():
    # Controlla se il file esiste
    if not os.path.exists(DATA_FILE):
        # Crea il file con dati predefiniti
        default_data = {
            "teams": [
                {"name": "Squadra A", "weekly_score": 0, "total_score": 0, "code": "42MCW5", "color": "#10a574"},
                {"name": "Squadra B", "weekly_score": 0, "total_score": 0, "code": "J7NUEF", "color": "#d26171"},
                {"name": "Squadra C", "weekly_score": 0, "total_score": 0, "code": "JRLHSC", "color": "#4e5a0d"}
            ],
            "admin_code": "8824",
            "last_reset": None,
            "history": []
        }
        save_data(default_data)
        return default_data
    
    try:
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    except Exception as e:
        print(f"Errore nel caricamento dei dati: {e}")
        # Ritorna dati di default in caso di errore
        return {
            "teams": [
                {"name": "Squadra A", "weekly_score": 0, "total_score": 0, "code": "42MCW5", "color": "#10a574"},
                {"name": "Squadra B", "weekly_score": 0, "total_score": 0, "code": "J7NUEF", "color": "#d26171"},
                {"name": "Squadra C", "weekly_score": 0, "total_score": 0, "code": "JRLHSC", "color": "#4e5a0d"}
            ],
            "admin_code": "8824",
            "last_reset": None,
            "history": []
        }

def save_data(data):
    try:
        with open(DATA_FILE, "w") as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(f"Errore nel salvataggio dei dati: {e}")

def should_reset_weekly():
    data = load_data()
    today = datetime.datetime.now().date()
    
    # Data di inizio (10 marzo 2025, lunedì)
    start_date = datetime.date(2025, 3, 10)
    
    # Se la data attuale è prima della data di inizio, non fare nulla
    if today < start_date:
        return False
    
    # Converti last_reset in oggetto datetime.date se non è None
    last_reset = None
    if data.get("last_reset"):
        try:
            last_reset_parts = [int(part) for part in data["last_reset"].split("-")]
            last_reset = datetime.date(last_reset_parts[0], last_reset_parts[1], last_reset_parts[2])
        except Exception:
            last_reset = None
    
    # Se oggi è lunedì e non abbiamo già resettato oggi
    if today.weekday() == 0 and (last_reset is None or last_reset != today):
        return True
    
    return False

def perform_weekly_reset():
    data = load_data()
    today = datetime.datetime.now().date()
    
    # Salva i punteggi settimanali nello storico prima del reset
    week_number = get_week_number(today)
    week_history = {
        "week": week_number,
        "date": today.isoformat(),
        "scores": []
    }
    
    for team in data["teams"]:
        week_history["scores"].append({
            "team": team["name"],
            "score": team["weekly_score"]
        })
    
    # Aggiungi i dati della settimana alla cronologia
    if "history" not in data:
        data["history"] = []
    data["history"].append(week_history)
    
    # Reset dei punteggi settimanali
    for team in data["teams"]:
        team["weekly_score"] = 0
    
    # Aggiorna la data dell'ultimo reset
    data["last_reset"] = today.isoformat()
    
    save_data(data)

def get_week_number(date):
    # Calcola il numero della settimana rispetto alla data di inizio (10 marzo 2025)
    start_date = datetime.date(2025, 3, 10)
    days_diff = (date - start_date).days
    return (days_diff // 7) + 1

def get_sorted_teams(teams, sort_by="total_score"):
    # Crea una copia delle squadre e le ordina per punteggio (totale o settimanale)
    sorted_teams = sorted(teams, key=lambda x: x[sort_by], reverse=True)
    return sorted_teams

def generate_team_code():
    # Genera un codice casuale di 6 caratteri alfanumerici
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_random_color():
    # Genera un colore casuale in formato hex
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

@app.route("/")
def index():
    # Controlla se è necessario resettare i punteggi settimanali
    if should_reset_weekly():
        perform_weekly_reset()
    
    data = load_data()
    # Ordina le squadre per punteggio totale
    sorted_teams = get_sorted_teams(data["teams"])
    # Verifica se l'utente è loggato come squadra
    team_auth = "team_code" in session
    return render_template("index.html", teams=data["teams"], ranking=sorted_teams, team_auth=team_auth)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    data = load_data()
    if request.method == "POST":
        code = request.form.get("code")
        if code == data["admin_code"]:
            session["admin"] = True
            flash("Accesso effettuato con successo!", "success")
            return render_template("admin.html", teams=data["teams"])
        flash("Codice admin non valido!", "error")
        return redirect(url_for("index"))
    
    # Verifica se l'utente è già autenticato come admin
    if session.get("admin"):
        return render_template("admin.html", teams=data["teams"])
    
    return render_template("admin_login.html")

@app.route("/logout")
def logout():
    # Rimuove tutte le informazioni di sessione
    session.clear()
    flash("Logout effettuato con successo!", "success")
    return redirect(url_for("index"))

@app.route("/add_points", methods=["POST"])
def add_points():
    if not session.get("admin"):
        flash("Accesso non autorizzato!", "error")
        return redirect(url_for("index"))
    
    data = load_data()
    team_name = request.form.get("team")
    action = request.form.get("action", "add")
    
    try:
        points = int(request.form.get("points"))
        # Se l'azione è sottrarre, rendi i punti negativi
        if action == "subtract":
            points = -points
    except ValueError:
        # Se i punti non sono un numero valido, reindirizza senza fare nulla
        flash("Inserisci un numero valido di punti!", "error")
        return redirect(url_for("admin"))
    
    for team in data["teams"]:
        if team["name"] == team_name:
            team["weekly_score"] += points
            team["total_score"] += points
            
            # Registra l'operazione nello storico delle attività
            timestamp = datetime.datetime.now().isoformat()
            activity = {
                "timestamp": timestamp,
                "team": team_name,
                "points": points,
                "action": "add" if points > 0 else "subtract",
                "weekly_score": team["weekly_score"],
                "total_score": team["total_score"]
            }
            
            if "activities" not in data:
                data["activities"] = []
            
            data["activities"].append(activity)
            
            save_data(data)
            
            flash(f"{'Aggiunti' if points > 0 else 'Sottratti'} {abs(points)} punti a {team_name}!", "success")
            break
    
    return redirect(url_for("admin"))

@app.route("/reset_weekly", methods=["GET"])
def reset_weekly():
    if not session.get("admin"):
        flash("Accesso non autorizzato!", "error")
        return redirect(url_for("index"))
    
    perform_weekly_reset()
    flash("Punteggi settimanali resettati con successo!", "success")
    return redirect(url_for("admin"))

@app.route("/add_new_team", methods=["POST"])
def add_new_team():
    if not session.get("admin"):
        flash("Accesso non autorizzato!", "error")
        return redirect(url_for("index"))
    
    data = load_data()
    team_name = request.form.get("team_name")
    
    # Verifica se esiste già una squadra con lo stesso nome
    if any(team["name"] == team_name for team in data["teams"]):
        flash(f"Esiste già una squadra con il nome '{team_name}'!", "error")
        return redirect(url_for("admin"))
    
    # Crea una nuova squadra
    new_team = {
        "name": team_name,
        "weekly_score": 0,
        "total_score": 0,
        "code": generate_team_code(),
        "color": get_random_color()
    }
    
    data["teams"].append(new_team)
    save_data(data)
    
    flash(f"Squadra '{team_name}' aggiunta con successo!", "success")
    return redirect(url_for("admin"))

@app.route("/delete_team", methods=["POST"])
def delete_team():
    if not session.get("admin"):
        flash("Accesso non autorizzato!", "error")
        return redirect(url_for("index"))
    
    data = load_data()
    team_name = request.form.get("team")
    
    # Trova e rimuovi la squadra
    data["teams"] = [team for team in data["teams"] if team["name"] != team_name]
    save_data(data)
    
    flash(f"Squadra '{team_name}' eliminata con successo!", "success")
    return redirect(url_for("admin"))

@app.route("/team_login", methods=["GET", "POST"])
def team_login():
    if request.method == "POST":
        team_code = request.form.get("team_code")
        data = load_data()
        
        # Cerca la squadra con il codice fornito
        for team in data["teams"]:
            if team.get("code") == team_code:
                session["team_code"] = team_code
                session["team_name"] = team["name"]
                flash(f"Benvenuto, {team['name']}!", "success")
                return redirect(url_for("team_management"))
        
        flash("Codice squadra non valido!", "error")
    
    return render_template("team_login.html")

@app.route("/team_management")
def team_management():
    if not session.get("team_code"):
        flash("Accesso non autorizzato!", "error")
        return redirect(url_for("team_login"))
    
    data = load_data()
    team_code = session.get("team_code")
    
    # Trova la squadra corrente
    current_team = next((team for team in data["teams"] if team.get("code") == team_code), None)
    
    if not current_team:
        flash("Squadra non trovata!", "error")
        session.pop("team_code", None)
        session.pop("team_name", None)
        return redirect(url_for("index"))
    
    return render_template("team_management.html", team=current_team)

@app.route("/history")
def history():
    data = load_data()
    
    # Ottieni la cronologia e ordinala per settimana (più recente prima)
    history_data = data.get("history", [])
    history_data.sort(key=lambda x: x.get("week", 0), reverse=True)
    
    # Ottieni anche lo storico delle attività se disponibile
    activities = data.get("activities", [])
    activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Limita le attività alle ultime 50
    recent_activities = activities[:50]
    
    return render_template("history.html", 
                           history=history_data, 
                           activities=recent_activities,
                           teams=data["teams"],
                           is_admin=session.get("admin", False))

@app.route("/api/teams", methods=["GET"])
def get_teams():
    data = load_data()
    return jsonify({"teams": data["teams"]})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)