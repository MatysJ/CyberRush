from db import Connect
import bcrypt
import mysql.connector

def delete_account(email, password):
        db = Connect()
        if db is None:
            return False, "Connexion à la base de données impossible."

        cursor = db.cursor()
        cursor.execute("SELECT Password FROM users WHERE Email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            db.close()
            return False, "Email incorrect."

        stored_password = user[0]
        if isinstance(stored_password, str):  
            stored_password = stored_password.encode("utf-8")

        if not bcrypt.checkpw(password.encode("utf-8"), stored_password):
            cursor.close()
            db.close()
            return False, "Mot de passe incorrect."

        try:
            cursor.execute("DELETE FROM users WHERE Email = %s", (email,))
            db.commit()
            cursor.close()
            db.close()
            return True, "Compte supprimé avec succès."
        except mysql.connector.Error as err:
            cursor.close()
            db.close()
            return False, f"Erreur lors de la suppression : {err}"

def update_account(old_email, old_password, new_email, new_pseudo, new_password):
    db = Connect()
    if db is None:
        return False, "Connexion à la base de données impossible."

    cursor = db.cursor()
    cursor.execute("SELECT Password FROM users WHERE Email = %s", (old_email,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        db.close()
        return False, "Email introuvable."

    stored_password = user[0]
    if isinstance(stored_password, str):  
        stored_password = stored_password.encode("utf-8")

    if not bcrypt.checkpw(old_password.encode("utf-8"), stored_password):
        cursor.close()
        db.close()
        return False, "Mot de passe actuel incorrect."

    try:
        hashed_new_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

        cursor.execute("""
            UPDATE users SET Email = %s, Pseudo = %s, Password = %s
            WHERE Email = %s
        """, (new_email, new_pseudo, hashed_new_password, old_email))
        db.commit()
        cursor.close()
        db.close()
        return True, "Informations mises à jour avec succès."
    except Exception as err:
        cursor.close()
        db.close()
        return False, f"Erreur lors de la mise à jour : {err}"