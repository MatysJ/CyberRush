import pygame

class Button:
    def __init__(self, text, pos, action, size=(200, 50), font_size=30, color=None):
        self.text = text
        self.x, self.y = pos
        self.width, self.height = size
        self.action = action
        
        self.default_color = color if color else (0, 150, 255)
        self.hover_color = (120, 0, 180)
        self.text_color = (255, 255, 255)
        
        self.current_color = self.default_color
        
        self.font = pygame.font.Font(None, font_size)
        self.rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)
        
        self.clicked = False

    def handle_event(self, event):
        mouse_pos = pygame.mouse.get_pos()
        
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.hover_color
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.clicked:
                    self.clicked = True
                    return True 
        else:
            self.current_color = self.default_color
            
        if event.type == pygame.MOUSEBUTTONUP:
            self.clicked = False
            
        return False

    def draw(self, screen):
        pygame.draw.rect(screen, (0, 0, 0), (self.rect.x + 3, self.rect.y + 3, self.rect.width, self.rect.height), border_radius=10)
        
        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=10)
        
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 2, border_radius=10)
        
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
    
    def action(self):
        if self.action:
            return self.action()