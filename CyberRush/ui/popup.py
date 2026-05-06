import pygame
from ui.button import Button

class Popup:
    def __init__(self, screen_width, screen_height, title, message, color=(255, 50, 50)):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.title = title
        self.message = message
        self.color = color
        
        self.width = 500
        self.height = 300
        self.rect = pygame.Rect((screen_width - self.width) // 2, (screen_height - self.height) // 2, self.width, self.height)
        
        self.font_title = pygame.font.Font(None, 40)
        self.font_msg = pygame.font.Font(None, 26)
        
        btn_x = self.rect.centerx
        btn_y = self.rect.bottom - 50
        self.ok_button = Button("OK", (btn_x, btn_y), self.close, size=(120, 40))
        
        self.active = True

    def close(self):
        self.active = False

    def handle_event(self, event):
        if self.active:
            if self.ok_button.handle_event(event):
                self.ok_button.action()
            return True 
        return False

    def draw_text_wrapped(self, surface, text, color, rect, font):
        """Découpe le texte pour qu'il rentre dans la largeur"""
        words = text.split(' ')
        lines = []
        while words:
            line = ''
            while words and font.size(line + words[0])[0] < rect.width:
                line += words.pop(0) + ' '
            lines.append(line)
        
        y = rect.y
        for line in lines:
            img = font.render(line, True, color)
            surface.blit(img, (rect.x + (rect.width - img.get_width()) // 2, y))
            y += font.get_height() + 5

    def draw(self, screen):
        if not self.active: return

        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(150) 
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, (30, 30, 30), self.rect)
        pygame.draw.rect(screen, self.color, self.rect, 3) 

        title_surf = self.font_title.render(self.title, True, self.color)
        title_rect = title_surf.get_rect(center=(self.rect.centerx, self.rect.y + 40))
        screen.blit(title_surf, title_rect)

        msg_rect = pygame.Rect(self.rect.x + 20, self.rect.y + 80, self.rect.width - 40, self.rect.height - 130)
        self.draw_text_wrapped(screen, self.message, (255, 255, 255), msg_rect, self.font_msg)

        self.ok_button.draw(screen)