import pygame
import bcrypt
from db import Connect
from ui.button import Button
from ui.text_input import TextInput
from ui.popup import Popup

class DeleteAccountPygame:
    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.user_id = self.game_manager.network_client.user_id if self.game_manager.network_client else None
        
        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Suppression de compte")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.RED_ALERT = (255, 50, 50)
        self.font_title = pygame.font.Font(None, 60)
        self.font_ui = pygame.font.Font(None, 30)

        center_x = self.screen_width // 2
        start_y = self.screen_height // 2 - 100

        self.password_input = TextInput(center_x - 200, start_y, 400, 50, "Confirmer mot de passe", is_password=True)
        
        self.show_password = False
        self.eye_rect = pygame.Rect(center_x + 210, start_y + 10, 30, 30)

        self.delete_button = Button("SUPPRIMER DÉFINITIVEMENT", (center_x, start_y + 100), self.try_delete, size=(350, 60))
        self.back_button = Button("Annuler", (center_x, self.screen_height - 80), self.go_back, size=(200, 50))

        self.popup = None

    def show_error(self, message):
        self.popup = Popup(self.screen_width, self.screen_height, "Erreur", message)

    def toggle_eye(self):
        self.show_password = not self.show_password
        self.password_input.toggle_password()

    def try_delete(self):
        password = self.password_input.get_text()
        if not password:
            self.show_error("Veuillez entrer votre mot de passe.")
            return self

        db = Connect()
        if db:
            try:
                c = db.cursor()
                c.execute("SELECT Password FROM users WHERE ID_Users = %s", (self.user_id,))
                res = c.fetchone()
                if res:
                    stored_pwd = res[0]
                    if isinstance(stored_pwd, str): stored_pwd = stored_pwd.encode('utf-8')
                    
                    if bcrypt.checkpw(password.encode('utf-8'), stored_pwd):
                        c.execute("DELETE FROM users WHERE ID_Users = %s", (self.user_id,))
                        db.commit()
                        print("Compte supprimé.")
                        if self.game_manager.network_client:
                            self.game_manager.network_client.close()
                            self.game_manager.network_client = None
                        
                        from ui.main_menu_pygame import MainMenuPygame
                        return MainMenuPygame(self.game_manager, user=None)
                    else:
                        self.show_error("Mot de passe incorrect.")
                c.close()
                db.close()
            except Exception as e:
                self.show_error(f"Erreur suppression : {e}")
        return self

    def go_back(self):
        from ui.profile_pygame import ProfilePygame
        db = Connect()
        user = None
        if db:
            c = db.cursor()
            c.execute("SELECT * FROM users WHERE ID_Users = %s", (self.user_id,))
            user = c.fetchone()
            c.close()
            db.close()
        return ProfilePygame(self.game_manager, user)

    def draw_eye(self):
        pygame.draw.circle(self.screen, self.CYBER_BLUE, self.eye_rect.center, 12, 2)
        if self.show_password:
            pygame.draw.circle(self.screen, self.CYBER_BLUE, self.eye_rect.center, 5)
        else:
            pygame.draw.line(self.screen, self.CYBER_BLUE, self.eye_rect.topleft, self.eye_rect.bottomright, 2)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None
                
                if self.popup and self.popup.active:
                    if self.popup.handle_event(event):
                         if not self.popup.active: self.popup = None
                    continue

                self.password_input.handle_event(event)
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.eye_rect.collidepoint(event.pos):
                        self.toggle_eye()

                if self.delete_button.handle_event(event): return self.delete_button.action()
                if self.back_button.handle_event(event): return self.back_button.action()

            self.screen.fill(self.CYBER_GREY)
            
            title_surf = self.font_title.render("SUPPRESSION DU COMPTE", True, self.RED_ALERT)
            self.screen.blit(title_surf, title_surf.get_rect(center=(self.screen_width // 2, 80)))
            
            msg = self.font_ui.render("Cette action est irréversible.", True, (255, 255, 255))
            self.screen.blit(msg, msg.get_rect(center=(self.screen_width // 2, 140)))

            self.password_input.draw(self.screen)
            self.draw_eye()
            
            self.delete_button.draw(self.screen)
            self.back_button.draw(self.screen)
            
            if self.popup: self.popup.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)