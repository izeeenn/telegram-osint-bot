import os

SESSION_FILE = "session.txt"

def load_session():
    """ Cargar SESSION_ID desde archivo """
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as file:
            return file.read().strip()
    return os.getenv("SESSION_ID", "")

def save_session(new_session):
    """ Guardar SESSION_ID en archivo """
    with open(SESSION_FILE, "w") as file:
        file.write(new_session)
