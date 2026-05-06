import socket
import json
import threading
import pygame

class NetworkClient:
    def __init__(self, user_id):
        self.host = "127.0.0.1" 
        self.port = 5555
        self.user_id = user_id
        self.client_socket = None
        self.lobby_frame = None 

    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            self.send_message({"action": "connect", "user_id": self.user_id})
            threading.Thread(target=self.listen, daemon=True).start()
            return True
        except Exception as e:
            print(f"[Network] Erreur connexion: {e}")
            return False

    def send_message(self, message):
        if self.client_socket:
            try:
                self.client_socket.sendall(json.dumps(message).encode('utf-8'))
            except Exception as e:
                print(f"[Network] Erreur envoi: {e}")

    def listen(self):
        while True:
            try:
                data = self.client_socket.recv(4096)
                if not data: break
                message = json.loads(data.decode('utf-8'))
                self.handle_message(message)
            except Exception as e:
                print(f"[Network] Erreur réception: {e}")
                break

    def handle_message(self, message):
        action = message.get("action")
        if action == "invite" and self.lobby_frame:
            try:
                self.lobby_frame.display_new_invite(message)
            except: pass

        elif action == "opponent_place_unit":
            pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"action": "opponent_place_unit", "data": message}))
        
        elif action == "opponent_spawn_enemy":
            print("[Network] Ennemi adverse détecté ! Création de l'événement...")
            pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"action": "opponent_spawn_enemy", "data": message}))
            
    def close(self):
        if self.client_socket:
            self.client_socket.close()