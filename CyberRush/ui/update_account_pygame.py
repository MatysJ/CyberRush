import pygame
import bcrypt
import re 
from db import Connect
from ui.button import Button
from ui.text_input import TextInput
from ui.popup import Popup

class UpdateAccountPygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        
        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Modifier Compte")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.title_font = pygame.font.Font(None, 60)

        center_x = self.screen_width // 2
        start_y = 150 
        spacing = 70

        self.pseudo_input = TextInput(center_x - 200, start_y, 400, 50, f"Nouveau Pseudo")
        self.email_input = TextInput(center_x - 200, start_y + spacing, 400, 50, f"Nouvel Email")
        
        self.new_password_input = TextInput(center_x - 200, start_y + spacing * 2, 400, 50, "Nouveau Mot de passe (Optionnel)", is_password=True)
        self.current_password_input = TextInput(center_x - 200, start_y + spacing * 3, 400, 50, "Mot de passe ACTUEL (Obligatoire)", is_password=True)
        
        self.eye_rect_new = pygame.Rect(center_x + 210, start_y + spacing * 2 + 10, 30, 30)
        self.eye_rect_current = pygame.Rect(center_x + 210, start_y + spacing * 3 + 10, 30, 30)

        self.update_button = Button("Sauvegarder", (center_x, start_y + spacing * 4 + 30), self.try_update, size=(300, 60))
        self.back_button = Button("Retour", (center_x, self.screen_height - 60), self.go_back, size=(200, 50))
        
        self.popup = None

        self.input_fields = [
            self.pseudo_input, 
            self.email_input, 
            self.new_password_input, 
            self.current_password_input
        ]

    def show_error(self, message):
        self.popup = Popup(self.screen_width, self.screen_height, "Erreur", message)

    def toggle_eye_new(self):
        self.new_password_input.toggle_password()
        
    def toggle_eye_current(self):
        self.current_password_input.toggle_password()

    def draw_eyes(self):
        is_visible_new = not self.new_password_input.is_password
        pygame.draw.circle(self.screen, self.CYBER_BLUE, self.eye_rect_new.center, 12, 2)
        if is_visible_new:
            pygame.draw.circle(self.screen, self.CYBER_BLUE, self.eye_rect_new.center, 5)
        else:
            pygame.draw.line(self.screen, self.CYBER_BLUE, self.eye_rect_new.topleft, self.eye_rect_new.bottomright, 2)
            
        is_visible_current = not self.current_password_input.is_password
        pygame.draw.circle(self.screen, self.CYBER_BLUE, self.eye_rect_current.center, 12, 2)
        if is_visible_current:
            pygame.draw.circle(self.screen, self.CYBER_BLUE, self.eye_rect_current.center, 5)
        else:
            pygame.draw.line(self.screen, self.CYBER_BLUE, self.eye_rect_current.topleft, self.eye_rect_current.bottomright, 2)

    def try_update(self):
        new_pseudo = self.pseudo_input.get_text().strip()
        new_email = self.email_input.get_text().strip()
        new_password = self.new_password_input.get_text()
        current_password = self.current_password_input.get_text()
        
        if not current_password:
            self.show_error("Le mot de passe actuel est requis.")
            return self
            
        if not new_pseudo and not new_email and not new_password:
            self.show_error("Aucune modification à sauvegarder.")
            return self
        
        db = Connect()
        if db:
            try:
                c = db.cursor(dictionary=True)
                
                c.execute("SELECT Password FROM users WHERE ID_Users = %s", (self.user_id,))
                result = c.fetchone()
                
                if not result:
                    self.show_error("Erreur: Utilisateur introuvable.")
                    return self
                    
                db_password = result['Password']
                
                if not bcrypt.checkpw(current_password.encode('utf-8'), db_password.encode('utf-8')):
                    self.show_error("Mot de passe actuel incorrect.")
                    return self
                
                if new_pseudo:
                    c.execute("UPDATE users SET Pseudo = %s WHERE ID_Users = %s", (new_pseudo, self.user_id))
                    
                if new_email:
                    if "@" not in new_email or "." not in new_email:
                        self.show_error("Format d'email invalide.")
                        return self
                    c.execute("UPDATE users SET Email = %s WHERE ID_Users = %s", (new_email, self.user_id))
                
                if new_password:
                    if len(new_password) < 8:
                        self.show_error("Le nouveau mot de passe doit faire au moins 8 caractères.")
                        return self
                    if not re.search(r"[A-Z]", new_password):
                        self.show_error("Manque une Majuscule dans le nouveau mot de passe.")
                        return self
                    if not re.search(r"[a-z]", new_password):
                        self.show_error("Manque une minuscule dans le nouveau mot de passe.")
                        return self
                    if not re.search(r"[0-9!@#$%^&*(),.?\":{}|<>]", new_password):
                        self.show_error("Manque un chiffre ou caractère spécial.")
                        return self
                    
                    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                    c.execute("UPDATE users SET Password = %s WHERE ID_Users = %s", (hashed.decode('utf-8'), self.user_id))
                
                db.commit()
                
                self.popup = Popup(self.screen_width, self.screen_height, "Succès", "Informations mises à jour !", color=(50, 255, 50))
                
                c.close()
                db.close()
                return self 

            except Exception as e:
                self.show_error(f"Erreur update : {e}")
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

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None
                
                if self.popup and self.popup.active:
                    if self.popup.handle_event(event):
                         if not self.popup.active: self.popup = None
                    continue

                self.pseudo_input.handle_event(event)
                self.email_input.handle_event(event)
                self.new_password_input.handle_event(event)
                self.current_password_input.handle_event(event)

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
                    return self.update_button.action()
                # ========================================
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.eye_rect_new.collidepoint(event.pos): self.toggle_eye_new()
                    if self.eye_rect_current.collidepoint(event.pos): self.toggle_eye_current()

                if self.update_button.handle_event(event): return self.update_button.action()
                if self.back_button.handle_event(event): return self.back_button.action()
            
            self.screen.fill(self.CYBER_GREY)
            
            title = self.title_font.render("MODIFIER LE COMPTE", True, self.CYBER_BLUE)
            self.screen.blit(title, title.get_rect(center=(self.screen_width // 2, 80)))
            
            self.pseudo_input.draw(self.screen)
            self.email_input.draw(self.screen)
            self.new_password_input.draw(self.screen)
            self.current_password_input.draw(self.screen)
            
            self.draw_eyes()
            self.update_button.draw(self.screen)
            self.back_button.draw(self.screen)
            
            if self.popup: self.popup.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)