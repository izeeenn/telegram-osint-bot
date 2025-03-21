import os

SESSION_FILE = "session_id.txt"

def load_session():
    """ Cargar SESSION_ID desde un archivo o entorno """
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return f.read().strip()
    return os.getenv("SESSION_ID", "")

def save_session(new_session):
    """ Guardar SESSION_ID en un archivo """
    with open(SESSION_FILE, "w") as f:
        f.write(new_session)
