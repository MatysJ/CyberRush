import socket
import threading
import json
from db import Connect

HOST = "0.0.0.0"
PORT = 5555

connected_clients = {} 
game_rooms = {}        

def handle_client(client_socket):
    user_id = None
    current_game_id = None
    
    try:
        while True:
            data = client_socket.recv(4096).decode('utf-8')
            if not data: break
            
            message = json.loads(data)
            action = message.get("action")
            
            if action == "connect":
                user_id = message.get("user_id")
                connected_clients[user_id] = client_socket
                print(f"[Serveur] Joueur {user_id} connecté.")
                
                db = Connect()
                if db:
                    try:
                        c = db.cursor()
                        c.execute("UPDATE users SET Online = 1, last_activity = NOW() WHERE ID_Users = %s", (user_id,))
                        db.commit()
                        c.close()
                    except Exception as e:
                        print(f"Erreur DB Online: {e}")
                    finally:
                        db.close()

            elif action == "join_game":
                game_id = message.get("game_id")
                current_game_id = game_id
                if game_id not in game_rooms:
                    game_rooms[game_id] = []
                if client_socket not in game_rooms[game_id]:
                    game_rooms[game_id].append(client_socket)
                print(f"[Serveur] Joueur {user_id} rejoint la salle {game_id}")

            elif action == "place_unit":
                game_id = message.get("game_id")
                if game_id in game_rooms:
                    for sock in game_rooms[game_id]:
                        if sock != client_socket: 
                            relay_msg = message.copy()
                            relay_msg["action"] = "opponent_place_unit"
                            try:
                                sock.sendall(json.dumps(relay_msg).encode('utf-8'))
                            except: pass

            elif action == "spawn_enemy":
                game_id = message.get("game_id")
                if game_id in game_rooms:
                    for sock in game_rooms[game_id]:
                        if sock != client_socket:
                            relay_msg = message.copy()
                            relay_msg["action"] = "opponent_spawn_enemy"
                            print(f"[Serveur] Relais Spawn Ennemi vers adversaire dans salle {game_id}")
                            try:
                                sock.sendall(json.dumps(relay_msg).encode('utf-8'))
                            except Exception as e:
                                print(f"Erreur envoi spawn: {e}")

    except Exception as e:
        print(f"[Serveur] Déconnexion brutale ou erreur: {e}")
    finally:
        if user_id:
            if user_id in connected_clients:
                del connected_clients[user_id]
            
            db = Connect()
            if db:
                try:
                    c = db.cursor()
                    c.execute("UPDATE users SET Online = 0, last_activity = NOW() WHERE ID_Users = %s", (user_id,))
                    db.commit()
                    c.close()
                except Exception as e:
                    print(f"Erreur DB Offline: {e}")
                finally:
                    db.close()
                    
            print(f"[Serveur] Joueur {user_id} est maintenant hors ligne.")

        if current_game_id and current_game_id in game_rooms:
            if client_socket in game_rooms[current_game_id]:
                game_rooms[current_game_id].remove(client_socket)
            if not game_rooms[current_game_id]:
                del game_rooms[current_game_id]
        
        client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[Serveur] En écoute sur {HOST}:{PORT}")
    while True:
        client_sock, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()

if __name__ == "__main__":
    start_server()