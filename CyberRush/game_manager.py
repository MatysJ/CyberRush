import pygame
from ui.main_menu_pygame import MainMenuPygame

class GameManager:
    def __init__(self):
        pygame.init()
        self.screen_width = 1200 
        self.screen_height = 800 
        
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        self.clock = pygame.time.Clock()
        
        self.network_client = None 
        
        self.current_screen = MainMenuPygame(self, user=None)

    def run(self):
        while self.current_screen:
            new_screen = self.current_screen.run()
            self.current_screen = new_screen
            
        if self.network_client:
            try:
                self.network_client.close()
            except:
                pass
        
        pygame.quit()

if __name__ == "__main__":
    game_manager = GameManager()
    game_manager.run()