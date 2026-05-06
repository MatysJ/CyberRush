import pygame
import time

class TextInput:
    def __init__(self, x, y, width, height, placeholder="", is_password=False, text_color=(255, 255, 255), box_color=(50, 50, 50)):
        self.rect = pygame.Rect(x, y, width, height)
        self.placeholder = placeholder
        self.is_password = is_password
        self.text_color = text_color
        self.box_color = box_color
        self.active_color = (0, 150, 255)
        self.passive_color = (100, 100, 100) 
        self.font = pygame.font.Font(None, 32)
        
        self.text = ""
        self.active = False
        
        self.cursor_pos = 0        
        self.cursor_visible = True
        self.last_blink_time = time.time()
        self.blink_interval = 0.5  

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
                click_x = event.pos[0] - self.rect.x - 5 
                
                display_text = self._get_display_text()
                best_index = len(display_text) 
                
                for i in range(len(display_text) + 1):
                    substring = display_text[:i]
                    w, h = self.font.size(substring)
                    if w > click_x:
                        best_index = max(0, i - 1)
                        break
                    best_index = i
                
                self.cursor_pos = best_index
                
            else:
                self.active = False
            
            self.cursor_visible = True
            self.last_blink_time = time.time()

        if event.type == pygame.KEYDOWN and self.active:
            
            if event.key == pygame.K_LEFT:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                    
            elif event.key == pygame.K_RIGHT:
                if self.cursor_pos < len(self.text):
                    self.cursor_pos += 1
            
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
            
            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]

            elif event.key == pygame.K_RETURN:
                pass 

            else:
                if event.unicode and event.unicode.isprintable():
                    self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                    self.cursor_pos += 1

            self.cursor_visible = True
            self.last_blink_time = time.time()

    def _get_display_text(self):
        """Retourne le texte tel qu'il doit être affiché (vrai texte ou étoiles)"""
        if self.is_password:
            return "*" * len(self.text)
        return self.text

    def toggle_password(self):
        """Active/Désactive l'affichage du mot de passe"""
        self.is_password = not self.is_password

    def get_text(self):
        return self.text

    def draw(self, screen):
        current_time = time.time()
        if current_time - self.last_blink_time > self.blink_interval:
            self.cursor_visible = not self.cursor_visible
            self.last_blink_time = current_time

        border_color = self.active_color if self.active else self.passive_color
        
        pygame.draw.rect(screen, self.box_color, self.rect)
        pygame.draw.rect(screen, border_color, self.rect, 2)

        display_text = self._get_display_text()
        
        if not self.text and not self.active:
            txt_surface = self.font.render(self.placeholder, True, (150, 150, 150))
            screen.blit(txt_surface, (self.rect.x + 5, self.rect.y + 10))
        else:
            txt_surface = self.font.render(display_text, True, self.text_color)
            screen.blit(txt_surface, (self.rect.x + 5, self.rect.y + 10))

            if self.active and self.cursor_visible:
                text_before_cursor = display_text[:self.cursor_pos]
                cursor_x_offset = self.font.size(text_before_cursor)[0]
                
                cursor_x = self.rect.x + 5 + cursor_x_offset
                cursor_y_top = self.rect.y + 8
                cursor_y_bot = self.rect.y + self.rect.height - 8
                
                pygame.draw.line(screen, self.text_color, (cursor_x, cursor_y_top), (cursor_x, cursor_y_bot), 2)