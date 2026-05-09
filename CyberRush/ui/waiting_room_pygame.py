import pygame
import sys
import time
from db import Connect
from ui.button import Button
from ui.game_board_pygame import GameBoardPygame

class WaitingRoomPygame:
    def __init__(self, game_manager, user, opponent_pseudo, id_game, is_host=False):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        self.network_client = game_manager.network_client
        self.opponent_pseudo = opponent_pseudo
        self.id_game = id_game 
        self.is_host = is_host 

        self.game_ready = False
        self.game_session_data = None

        if self.network_client:
            self.network_client.lobby_frame = self

        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Salle d'attente")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        self.font = pygame.font.Font(None, 36)

        largeur_bouton = 200
        centre_x = self.screen_width // 2

        self.cancel_button = Button("Annuler", (centre_x, 380), 
                                    self.cancel_game, size=(largeur_bouton, 50), color=(200, 50, 50))

        self.launch_button = None

        self.last_db_check = time.time()
        self.check_interval = 2.0 

    def _get_session_status(self):
        db = Connect()
        status = None
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT Status FROM game_sessions WHERE ID_Game = %s", (self.id_game,))
                row = cursor.fetchone()
                if row:
                    status = row['Status'] if isinstance(row, dict) else row[0]
                cursor.close()
                db.close()
            except Exception as e:
                print(f"Erreur DB Status: {e}")
        return status

    def _check_invite_exists(self):
        db = Connect()
        exists = False
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT ID_Invite FROM game_invitations WHERE ID_Game = %s", (self.id_game,))
                exists = (cursor.fetchone() is not None)
                cursor.close()
                db.close()
            except Exception as e:
                print(f"Erreur DB Invite: {e}")
        return exists

    def check_game_status(self):
        status = self._get_session_status()

        if not status:
            if not self.is_host and self.game_ready:
                return self.cancel_game()
            return None

        if status == 'InProgress':
            return self.start_game()

        invite_exists = self._check_invite_exists()

        if not invite_exists:
            self.game_ready = True

            if self.is_host and not self.launch_button:
                largeur_bouton = 200
                centre_x = self.screen_width // 2
                
                self.launch_button = Button("Lancer la partie", (centre_x, 300), 
                                            self.launch_game, size=(largeur_bouton, 50))
        else:
            self.game_ready = False
            
        return None

    def launch_game(self):
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("UPDATE game_sessions SET Status = 'InProgress' WHERE ID_Game = %s", (self.id_game,))
                db.commit()
                cursor.close()
                db.close()
            except Exception as e:
                print(e)

    def cancel_game(self):
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                if self.is_host and not self.game_ready:
                    cursor.execute("DELETE FROM game_invitations WHERE ID_Game = %s", (self.id_game,))
                else:
                    cursor.execute("DELETE FROM game_sessions WHERE ID_Game = %s", (self.id_game,))
                db.commit()
                cursor.close()
                db.close()
            except Exception as e:
                print(e)
                
        from ui.lobby_pygame import LobbyPygame
        return LobbyPygame(self.game_manager, self.user)

    def start_game(self):
        from ui.loading_screen_pygame import LoadingScreenPygame
        return LoadingScreenPygame(self.game_manager, self.user, self.opponent_pseudo, self.id_game, self.is_host)
            
        game_data = {'game_id': self.id_game, 'opponent_pseudo': self.opponent_pseudo}
        return GameBoardPygame(self.game_manager, self.user, self.network_client, game_data)

    def draw_text(self, text, font, text_col, pos, align="center"):
        img = font.render(text, True, text_col)
        rect = img.get_rect()
        if align == "center":
            rect.center = pos
        elif align == "midleft":
            rect.midleft = pos
        self.screen.blit(img, rect)

    def run(self):
        while True:
            current_time = time.time()
            
            if current_time - self.last_db_check > self.check_interval:
                next_state = self.check_game_status()
                self.last_db_check = current_time
                if next_state:
                    return next_state 

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return self.cancel_game()

                if event.type == pygame.USEREVENT and hasattr(event, "action") and event.action == "force_lobby":
                    from ui.lobby_pygame import LobbyPygame
                    if self.network_client:
                        self.network_client.lobby_frame = None
                    return LobbyPygame(self.game_manager, self.user)

                if self.cancel_button and self.cancel_button.handle_event(event):
                    return self.cancel_button.action()
                    
                if self.launch_button and self.launch_button.handle_event(event):
                    self.launch_button.action()
                    
            self.screen.fill(self.CYBER_GREY)

            if self.game_ready:
                if self.is_host:
                    self.draw_text(f"{self.opponent_pseudo} a rejoint ! Prêt à lancer.", self.font, self.CYBER_BLUE, (self.screen_width // 2, 200))
                else:
                    self.draw_text(f"En attente de l'hôte ({self.opponent_pseudo})...", self.font, self.LIGHT_GREY, (self.screen_width // 2, 200))
            else:
                 self.draw_text(f"En attente de {self.opponent_pseudo}...", self.font, self.LIGHT_GREY, (self.screen_width // 2, 200))

            if self.cancel_button:
                self.cancel_button.draw(self.screen)
            if self.launch_button:
                self.launch_button.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)
