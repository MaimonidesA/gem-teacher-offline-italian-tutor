"""Local learner identities with independent learning databases.

The original database stays in place as the default profile. Model/voice assets
remain shared; teaching history, settings and exports belong to one learner.
"""
from pathlib import Path
import sqlite3
import threading
import unicodedata
import uuid

from .store import Store, now


class Profiles:
    def __init__(self, original):
        self.root = Path(original.path).parent
        self.path = self.root / "profiles.sqlite3"
        self.lock = threading.Lock()
        self.stores = {"default": original}
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, created TEXT NOT NULL)""")
            db.execute("INSERT OR IGNORE INTO profiles VALUES (?,?,?)", ("default", "Mon profil", now()))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def name(value):
        if not isinstance(value, str):
            raise ValueError("Choisissez un nom de 1 à 40 caractères.")
        value = value.strip()
        if not 1 <= len(value) <= 40 or any(unicodedata.category(c).startswith("C") for c in value):
            raise ValueError("Choisissez un nom de 1 à 40 caractères.")
        return value

    def list(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM profiles ORDER BY created,id")]

    def resolve(self, pid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM profiles WHERE id=?", (pid,)).fetchone()
        if not row:
            raise ValueError("Ce profil est introuvable. Choisissez un autre profil.")
        # Only registry IDs may resolve to a path. No client-supplied filenames.
        with self.lock:
            if pid not in self.stores:
                self.stores[pid] = Store(self.root / "profiles" / (pid + ".sqlite3"))
            store = self.stores[pid]
        return dict(row), store

    def create(self, name, base="fr"):
        name = self.name(name)
        if base not in ("fr", "en"):
            raise ValueError("Choisissez le français ou l’anglais.")
        profile = {"id": uuid.uuid4().hex, "name": name, "created": now()}
        folder = self.root / "profiles"
        folder.mkdir(exist_ok=True)
        store = Store(folder / (profile["id"] + ".sqlite3"))
        store.update_settings({"base": base})
        with self.connect() as db:
            db.execute("INSERT INTO profiles VALUES (:id,:name,:created)", profile)
        with self.lock:
            self.stores[profile["id"]] = store
        return profile

    def rename(self, pid, name):
        name = self.name(name)
        with self.connect() as db:
            if not db.execute("UPDATE profiles SET name=? WHERE id=?", (name, pid)).rowcount:
                raise ValueError("Ce profil est introuvable. Choisissez un autre profil.")
        return self.resolve(pid)[0]
