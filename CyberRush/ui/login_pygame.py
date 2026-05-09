import pygame
import sys
import bcrypt
from db import Connect
from network import NetworkClient
from ui.button import Button
from ui.text_input import TextInput
from ui.popup import Popup

class LoginPygame:
    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Connexion")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.title_font = pygame.font.Font(None, 80)

        center_x = self.screen_width // 2
        start_y = self.screen_height // 2 - 100

        self.email_input = TextInput(center_x - 200, start_y, 400, 50, "Email")
        self.password_input = TextInput(center_x - 200, start_y + 80, 400, 50, "Mot de passe", is_password=True)
        
        self.show_password = False
        self.eye_rect = pygame.Rect(center_x + 210, start_y + 90, 30, 30)

        self.login_button = Button("Se connecter", (center_x, start_y + 180), self.try_login, size=(250, 60))
        self.back_button = Button("Retour", (center_x, self.screen_height - 60), self.go_back, size=(200, 50))

        self.popup = None

        self.input_fields = [self.email_input, self.password_input]

    def show_error(self, message):
        self.popup = Popup(self.screen_width, self.screen_height, "Erreur", message)

    def toggle_eye(self):
        self.show_password = not self.show_password
        self.password_input.toggle_password()

    def draw_eye(self):
        pygame.draw.circle(self.screen, self.CYBER_BLUE, self.eye_rect.center, 12, 2)
        if self.show_password:
            pygame.draw.circle(self.screen, self.CYBER_BLUE, self.eye_rect.center, 5)
        else:
            pygame.draw.line(self.screen, self.CYBER_BLUE, self.eye_rect.topleft, self.eye_rect.bottomright, 2)

    def try_login(self):
        email = self.email_input.get_text()
        password = self.password_input.get_text()

        db = Connect()
        if db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM users WHERE Email = %s", (email,))
            user = cursor.fetchone()
            cursor.close()
            db.close()

            if user:
                stored_password = user[2]
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode("utf-8")

                if bcrypt.checkpw(password.encode("utf-8"), stored_password):
                    user_id = user[0]
                    client = NetworkClient(user_id)
                    if client.connect():
                        print("[Réseau] Connecté au serveur !")
                        self.game_manager.network_client = client
                    else:
                        print("[Attention] Mode Hors Ligne")
                    
                    from ui.main_menu_pygame import MainMenuPygame
                    return MainMenuPygame(self.game_manager, user=user)
                else:
                    self.show_error("Mot de passe incorrect.")
            else:
                self.show_error("Email introuvable.")
        else:
            self.show_error("Impossible de contacter la Base de Données.")
        
        return self
        
    def go_back(self):
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, user=None)
    
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None
                
                if self.popup and self.popup.active:
                    if self.popup.handle_event(event):
                         if not self.popup.active: self.popup = None
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                    active_idx = -1
                    for i, field in enumerate(self.input_fields):
                        if field.active:
                            active_idx = i
                            field.active = False 
                            break

                    next_idx = (active_idx + 1) % len(self.input_fields)
                    self.input_fields[next_idx].active = True
                    self.input_fields[next_idx].cursor_pos = len(self.input_fields[next_idx].text)
                    continue 

                if event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER):
                    return self.login_button.action()

                self.email_input.handle_event(event)
                self.password_input.handle_event(event)

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.eye_rect.collidepoint(event.pos): self.toggle_eye()
                
                if self.login_button.handle_event(event): return self.login_button.action()
                if self.back_button.handle_event(event): return self.back_button.action()
                
            self.screen.fill(self.CYBER_GREY)
            
            title_surf = self.title_font.render("CONNEXION", True, self.CYBER_BLUE)
            title_rect = title_surf.get_rect(center=(self.screen_width // 2, 100))
            self.screen.blit(title_surf, title_rect)

            self.email_input.draw(self.screen)
            self.password_input.draw(self.screen)
            self.draw_eye()

            self.login_button.draw(self.screen)
            self.back_button.draw(self.screen)

            if self.popup: self.popup.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)
