import pygame
from ui.button import Button

class SettingsPygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        
        if not hasattr(self.game_manager, 'language'):
            self.game_manager.language = "FR"

        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Paramètres")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.font_title = pygame.font.Font(None, 60)

        center_x = self.screen_width // 2
        
        lang_text = "Langue : Français" if self.game_manager.language == "FR" else "Language : English"
        self.lang_button = Button(lang_text, (center_x, 300), self.toggle_language, size=(300, 60))
        
        back_text = "Retour" if self.game_manager.language == "FR" else "Back"
        self.back_button = Button(back_text, (center_x, self.screen_height - 60), self.go_back, size=(200, 50))

    def toggle_language(self):
        if self.game_manager.language == "FR":
            self.game_manager.language = "EN"
            self.lang_button.text = "Language : English"
            self.back_button.text = "Back"
        else:
            self.game_manager.language = "FR"
            self.lang_button.text = "Langue : Français"
            self.back_button.text = "Retour"
        return self

    def go_back(self):
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, self.user)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                
                if self.lang_button.handle_event(event): return self.lang_button.action()
                if self.back_button.handle_event(event): return self.back_button.action()

            self.screen.fill(self.CYBER_GREY)
            
            title_text = "PARAMÈTRES" if self.game_manager.language == "FR" else "SETTINGS"
            title = self.font_title.render(title_text, True, self.CYBER_BLUE)
            self.screen.blit(title, title.get_rect(center=(self.screen_width // 2, 80)))
            
            self.lang_button.draw(self.screen)
            self.back_button.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(60)