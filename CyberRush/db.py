import mysql.connector
import bcrypt

def Connect():
    try:
        db = mysql.connector.connect(
            host="72.60.185.73",
            user= "matys",
            password="M4tYs!92qvL7cBx",
            database="RushData"
        )
        return db
    except mysql.connector.Error as err:
        print(f"Erreur de connexion : {err}")
        return None