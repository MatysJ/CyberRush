import pygame
import sys
from db import Connect
from ui.button import Button
from ui.popup import Popup
import time 
from ui.waiting_room_pygame import WaitingRoomPygame
from ui.game_board_pygame import GameBoardPygame 

class LobbyPygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        self.network_client = game_manager.network_client

        if self.network_client:
            self.network_client.lobby_frame = self

        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Lobby")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        self.font = pygame.font.Font(None, 28)
        self.font_title = pygame.font.Font(None, 60)

        center_x = (self.screen_width // 2) - 100
        self.back_button = Button("Retour Menu", (self.screen_width // 4, self.screen_height - 60), self.go_back, size=(200, 50))
        
        self.matchmaking_button = Button("Matchmaking Rapide", (self.screen_width - 270, self.screen_height - 60), self.start_matchmaking, size=(250, 60))
        self.popup = None

        self.friends = self.load_friends()
        self.pending_games = self.load_pending_games_from_db()
        
        self.last_refresh = time.time()
        self.refresh_interval = 2.0 

    def show_error(self, message):
        self.popup = Popup(self.screen_width, self.screen_height, "Erreur", message)

    def has_valid_deck(self):
        """Vérifie si le joueur a exactement 8 cartes équipées dans son deck."""
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT COUNT(*) FROM user_deck WHERE ID_Users = %s AND Deck_Slot > 0", (self.user_id,))
                count = cursor.fetchone()[0]
                cursor.close()
                db.close()
                return count == 8
            except Exception as e:
                print(f"Erreur vérification deck: {e}")
        return False

    def load_friends(self):
        db = Connect()
        friends = []
        if db:
            try:
                cursor = db.cursor()
                query = """
                    SELECT u.ID_Users, u.Pseudo, u.Online
                    FROM friends f
                    JOIN users u ON (f.Sender_ID = u.ID_Users OR f.Receiver_ID = u.ID_Users)
                    WHERE (f.Sender_ID = %s OR f.Receiver_ID = %s)
                    AND f.Status = 'Accepted' 
                    AND u.ID_Users != %s
                    AND u.Online = 1
                """
                cursor.execute(query, (self.user_id, self.user_id, self.user_id))
                friends = cursor.fetchall()
            except Exception as e:
                print(f"Erreur chargement amis lobby : {e}")
            finally:
                db.close()
        return friends

    def load_pending_games_from_db(self):
        games = []
        db = Connect()
        if db:
            try:
                cursor = db.cursor(dictionary=True)
                query = """
                    SELECT g.ID_Game, u.Pseudo as SenderName
                    FROM game_invitations gi
                    JOIN game_sessions g ON gi.ID_Game = g.ID_Game
                    JOIN users u ON gi.Sender_ID = u.ID_Users
                    WHERE gi.Receiver_ID = %s AND g.Status = 'Waiting'
                """
                cursor.execute(query, (self.user_id,))
                games = cursor.fetchall()
                cursor.close()
                db.close()
            except Exception as e:
                print(f"Erreur chargement invitations: {e}")
        return games

    def create_game_session_db(self, opponent_id):
        game_id = None
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                
                cursor.execute("SELECT Legend FROM users WHERE ID_Users = %s", (self.user_id,))
                result = cursor.fetchone()
                p1_legend = result[0] if result and result[0] is not None else 0
                
                query_session = """
                    INSERT INTO game_sessions (Player1_ID, Player2_ID, Status, Player1_Legend, Player2_Legend) 
                    VALUES (%s, %s, 'Waiting', %s, 0)
                """
                cursor.execute(query_session, (self.user_id, opponent_id, p1_legend))
                game_id = cursor.lastrowid
                
                query_invite = "INSERT INTO game_invitations (Sender_ID, Receiver_ID, ID_Game) VALUES (%s, %s, %s)"
                cursor.execute(query_invite, (self.user_id, opponent_id, game_id))
                
                db.commit()
                print(f"Session {game_id} créée en BDD avec la Légende {p1_legend}.")
            except Exception as e:
                self.show_error(f"Erreur création session : {e}")
            finally:
                try: cursor.close()
                except: pass
                db.close()
                
        return game_id

    def invite_friend(self, friend_id, friend_pseudo):
        if not self.has_valid_deck():
            self.show_error("Vous devez équiper 8 cartes dans votre deck pour jouer.")
            return self

        print(f"Invitation envoyée à {friend_pseudo}...")
        game_id = self.create_game_session_db(friend_id)
        
        if game_id:
            if self.network_client:
                self.network_client.send_message({
                    "action": "invite",
                    "sender_id": self.user_id,
                    "sender_pseudo": self.user[3],
                    "receiver_id": friend_id,
                    "game_id": game_id
                })
                return WaitingRoomPygame(self.game_manager, self.user, friend_pseudo, game_id, is_host=True)
            else:
                self.show_error("Vous n'êtes pas connecté au serveur de jeu.")
        return self

    def join_game(self, game_id, sender_name):
        if not self.has_valid_deck():
            self.show_error("Vous devez équiper 8 cartes dans votre deck pour rejoindre.")
            return self

        print(f"Rejoindre la partie {game_id} de {sender_name}")
        
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                
                cursor.execute("SELECT Legend FROM users WHERE ID_Users = %s", (self.user_id,))
                result = cursor.fetchone()
                p2_legend = result[0] if result and result[0] is not None else 0
                
                cursor.execute("""
                    UPDATE game_sessions 
                    SET Player2_ID = %s, Status = 'InProgress', Player2_Legend = %s 
                    WHERE ID_Game = %s
                """, (self.user_id, p2_legend, game_id))
                
                cursor.execute("DELETE FROM game_invitations WHERE ID_Game = %s AND Receiver_ID = %s", (game_id, self.user_id))
                
                db.commit()
            except Exception as e:
                print(f"Erreur lors de l'acceptation de l'invitation: {e}")
            finally:
                try: cursor.close()
                except: pass
                db.close()
        
        return WaitingRoomPygame(self.game_manager, self.user, sender_name, game_id, is_host=False)

    def go_back(self):
        # Le Lobby ne modifie pas le compte, on renvoie simplement l'utilisateur instantanément
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, self.user)
    
    def start_matchmaking(self):
        if not self.has_valid_deck():
            self.show_error("Vous devez équiper 8 cartes dans votre deck pour lancer le test.")
            return self

        self.show_error("Le matchmaking public n'est pas encore disponible.")
        return self

    def display_new_invite(self, message):
        print(f"Nouvelle invitation reçue de {message.get('sender_pseudo')} !")
        self.pending_games = self.load_pending_games_from_db()

    def draw_text(self, text, font, color, pos, align="center"):
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        if align == "center":
            rect.center = pos
        elif align == "midleft":
            rect.midleft = pos
        self.screen.blit(surface, rect)

    def run(self):
        self.friend_buttons = []
        y_offset = 150
        for friend in self.friends:
            f_id = friend[0]    
            pseudo = friend[1] 
            
            btn = Button("Inviter", (self.screen_width // 4 + 150, y_offset), 
                         lambda fid=f_id, fpseudo=pseudo: self.invite_friend(fid, fpseudo), 
                         size=(100, 30))
            self.friend_buttons.append({'pseudo': pseudo, 'button': btn, 'y': y_offset})
            y_offset += 50

        self.game_buttons = []
        self.last_refresh = 0 
        last_pending_ids = [] 
        
        while True:
            current_time = time.time()
            
            if current_time - self.last_refresh > self.refresh_interval:
                self.pending_games = self.load_pending_games_from_db()
                self.last_refresh = current_time
                
                current_pending_ids = [g['ID_Game'] for g in self.pending_games]
                
                if current_pending_ids != last_pending_ids:
                    self.game_buttons = []
                    y_offset = 150
                    for game in self.pending_games:
                        g_id = game['ID_Game']
                        sender = game['SenderName']
                        btn = Button("Rejoindre", (self.screen_width * 3 // 4 + 150, y_offset), 
                                     lambda gid=g_id, s=sender: self.join_game(gid, s), 
                                     size=(120, 30))
                        self.game_buttons.append({'text': f"Vs {sender}", 'button': btn, 'y': y_offset})
                        y_offset += 50
                        
                    last_pending_ids = current_pending_ids
                    
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None
                
                if self.popup and self.popup.active:
                    if self.popup.handle_event(event):
                         if not self.popup.active: self.popup = None
                    continue 
                
                if self.back_button.handle_event(event): return self.back_button.action()
                if self.matchmaking_button.handle_event(event): return self.matchmaking_button.action()
                
                for fb in self.friend_buttons:
                    if fb['button'].handle_event(event): return fb['button'].action()
                    
                for gb in self.game_buttons:
                    if gb['button'].handle_event(event): return gb['button'].action()
                        
            self.screen.fill(self.CYBER_GREY)

            title_render = self.font_title.render("Lobby Multijoueur", True, self.CYBER_BLUE)
            self.screen.blit(title_render, title_render.get_rect(center=(self.screen_width // 2, 50)))
            pygame.draw.line(self.screen, self.CYBER_BLUE, (self.screen_width // 2, 100), (self.screen_width // 2, self.screen_height - 100), 2)

            self.draw_text("Amis en ligne", self.font, self.CYBER_BLUE, (self.screen_width // 4, 110))
            if not self.friend_buttons:
                self.draw_text("Aucun ami connecté", self.font, self.LIGHT_GREY, (self.screen_width // 4, 150))
            else:
                for fb in self.friend_buttons:
                    self.draw_text(fb['pseudo'], self.font, self.LIGHT_GREY, (100, fb['y']), align="midleft")
                    fb['button'].draw(self.screen)

            self.draw_text("Invitations reçues", self.font, self.CYBER_BLUE, (self.screen_width * 3 // 4, 110))
            if not self.game_buttons:
                self.draw_text("Aucune invitation", self.font, self.LIGHT_GREY, (self.screen_width * 3 // 4, 150))
            else:
                for gb in self.game_buttons:
                    self.draw_text(gb['text'], self.font, self.LIGHT_GREY, (self.screen_width // 2 + 50, gb['y']), align="midleft")
                    gb['button'].draw(self.screen)

            self.back_button.draw(self.screen)
            self.matchmaking_button.draw(self.screen)

            if self.popup and self.popup.active:
                self.popup.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)
