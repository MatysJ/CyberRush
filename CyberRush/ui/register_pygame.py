import pygame
import sys
import bcrypt
import re 
from datetime import datetime
from db import Connect
from ui.button import Button
from ui.text_input import TextInput
from ui.popup import Popup 

class RegisterPygame:
    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Inscription")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.title_font = pygame.font.Font(None, 60)
        self.label_font = pygame.font.Font(None, 24)

        center_x = self.screen_width // 2
        start_y = self.screen_height // 2 - 240 
        spacing = 80 

        self.email_input = TextInput(center_x - 200, start_y, 400, 50, "Email")
        self.pseudo_input = TextInput(center_x - 200, start_y + spacing, 400, 50, "Pseudo")
        
        date_y = start_y + spacing * 2
        self.day_input = TextInput(center_x - 160, date_y, 80, 50, "JJ")
        self.month_input = TextInput(center_x - 60, date_y, 80, 50, "MM")
        self.year_input = TextInput(center_x + 40, date_y, 120, 50, "AAAA")
        
        self.password_input = TextInput(center_x - 200, start_y + spacing * 3, 400, 50, "Mot de passe", is_password=True)
        self.confirm_password_input = TextInput(center_x - 200, start_y + spacing * 4, 400, 50, "Confirmer mot de passe", is_password=True)
        
        self.show_password = False
        self.eye_rect_1 = pygame.Rect(center_x + 210, start_y + spacing * 3 + 10, 30, 30)
        self.eye_rect_2 = pygame.Rect(center_x + 210, start_y + spacing * 4 + 10, 30, 30)

        self.register_button = Button("Créer le compte", (center_x, start_y + spacing * 5 + 40), self.try_register, size=(300, 60))
        self.back_button = Button("Retour", (center_x, self.screen_height - 60), self.go_back, size=(200, 50))

        self.input_fields = [
            self.email_input, self.pseudo_input, 
            self.day_input, self.month_input, self.year_input, 
            self.password_input, self.confirm_password_input
        ]
        
        self.popup = None

    def show_error(self, message):
        self.popup = Popup(self.screen_width, self.screen_height, "Erreur", message)

    def toggle_eye_1(self): self.password_input.toggle_password()
    def toggle_eye_2(self): self.confirm_password_input.toggle_password()
        
    def draw_eye(self, rect, is_visible):
        pygame.draw.circle(self.screen, self.CYBER_BLUE, rect.center, 12, 2)
        if is_visible: pygame.draw.circle(self.screen, self.CYBER_BLUE, rect.center, 5)
        else: pygame.draw.line(self.screen, self.CYBER_BLUE, rect.topleft, rect.bottomright, 2)

    def try_register(self):
        email = self.email_input.get_text()
        pseudo = self.pseudo_input.get_text()
        day = self.day_input.get_text()
        month = self.month_input.get_text()
        year = self.year_input.get_text()
        password = self.password_input.get_text()
        confirm_password = self.confirm_password_input.get_text()

        if not email or not pseudo or not password:
            self.show_error("Tous les champs doivent être remplis.")
            return self

        if password != confirm_password:
            self.show_error("Les mots de passe ne correspondent pas.")
            return self

        if len(password) < 8:
            self.show_error("Le mot de passe doit faire au moins 8 caractères.")
            return self
        if not re.search(r"[A-Z]", password):
            self.show_error("Le mot de passe doit contenir au moins une Majuscule.")
            return self
        if not re.search(r"[a-z]", password):
            self.show_error("Le mot de passe doit contenir au moins une minuscule.")
            return self
        if not re.search(r"[0-9!@#$%^&*(),.?\":{}|<>]", password):
            self.show_error("Le mot de passe doit contenir un chiffre ou un caractère spécial.")
            return self

        sql_birthday = ""
        try:
            full_date_str = f"{day}/{month}/{year}"
            date_obj = datetime.strptime(full_date_str, "%d/%m/%Y")
            sql_birthday = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            self.show_error("Date invalide ! Vérifiez Jour (1-31), Mois (1-12), Année.")
            return self

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        db = Connect()
        if db is None: 
            self.show_error("Impossible de connecter à la base de données.")
            return self

        cursor = db.cursor()
        cursor.execute("SELECT ID_Users FROM users WHERE Email = %s", (email,))
        if cursor.fetchone():
            self.show_error("Cet email est déjà utilisé.")
            cursor.close()
            db.close()
            return self

        try:
            query_insert = "INSERT INTO users (Email, Password, Pseudo, Birthday, Avatar, Level, Gold, Experience, Energy) VALUES (%s, %s, %s, %s, 1, 1, 100, 0, 100)"
            cursor.execute(query_insert, (email, hashed_password.decode("utf-8"), pseudo, sql_birthday))
            db.commit()
            
            print("Inscription réussie !") 
            from ui.main_menu_pygame import MainMenuPygame
            return MainMenuPygame(self.game_manager)

        except Exception as err:
            self.show_error(f"Erreur technique SQL : {err}")
        
        cursor.close()
        db.close()
        return self

    def go_back(self):
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager)
    
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None
                
                if self.popup and self.popup.active:
                    if self.popup.handle_event(event):
                        if not self.popup.active: self.popup = None
                    continue

                # --- NOUVEAU : GESTION DE LA TOUCHE TAB ---
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

                # === NOUVEAU : VALIDATION AVEC ENTRÉE ===
                if event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER):
                    return self.register_button.action()
                # ========================================

                for field in self.input_fields: field.handle_event(event)
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.eye_rect_1.collidepoint(event.pos): self.toggle_eye_1()
                    if self.eye_rect_2.collidepoint(event.pos): self.toggle_eye_2()
                
                if self.register_button.handle_event(event): return self.register_button.action()
                if self.back_button.handle_event(event): return self.back_button.action()
            
            self.screen.fill(self.CYBER_GREY)
            
            title_surf = self.title_font.render("INSCRIPTION", True, self.CYBER_BLUE)
            self.screen.blit(title_surf, title_surf.get_rect(center=(self.screen_width // 2, 50)))
            date_label = self.label_font.render("Date de naissance :", True, (200, 200, 200))
            self.screen.blit(date_label, (self.screen_width // 2 - 200, self.day_input.rect.top - 25))

            for field in self.input_fields: field.draw(self.screen)
            self.draw_eye(self.eye_rect_1, not self.password_input.is_password)
            self.draw_eye(self.eye_rect_2, not self.confirm_password_input.is_password)
            
            self.register_button.draw(self.screen)
            self.back_button.draw(self.screen)
            
            if self.popup: self.popup.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(60)