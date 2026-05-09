import pygame
import io
from db import Connect
from ui.button import Button
from ui.avatar_selector_pygame import AvatarSelectorPygame
from ui.update_account_pygame import UpdateAccountPygame
from ui.delete_account_pygame import DeleteAccountPygame

class ProfilePygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        
        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Mon Profil")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        self.font_large = pygame.font.Font(None, 60)
        self.font_medium = pygame.font.Font(None, 36)

        self.avatar_image = self.load_avatar()
        
        center_x = self.screen_width // 2
        start_y = 350
        spacing = 70

        self.modify_avatar_button = Button("Changer d'avatar", (center_x, start_y), self.go_to_avatar_selector, size=(300, 60))
        self.update_account_button = Button("Modifier le compte", (center_x, start_y + spacing), self.go_to_update_account, size=(300, 60))
        self.delete_account_button = Button("Supprimer le compte", (center_x, start_y + spacing * 2), self.go_to_delete_account, size=(300, 60))
        
        self.back_button = Button("Retour", (center_x, self.screen_height - 60), self.go_back, size=(200, 50))

    def load_avatar(self):
        db = Connect()
        if not db: return None
        try:
            cursor = db.cursor()
            query = "SELECT a.Image_Data FROM avatars a JOIN users u ON u.Avatar = a.ID_Avatar WHERE u.ID_Users = %s"
            cursor.execute(query, (self.user_id,))
            result = cursor.fetchone()
            cursor.close()
            db.close()
            if result and result[0]:
                image_stream = io.BytesIO(result[0])
                img = pygame.image.load(image_stream)
                return pygame.transform.scale(img, (150, 150))
        except: pass
        return None

    def go_back(self):
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, self.user)
    
    def go_to_avatar_selector(self):
        return AvatarSelectorPygame(self.game_manager, self.user)
    
    def go_to_update_account(self):
        return UpdateAccountPygame(self.game_manager, self.user)
    
    def go_to_delete_account(self):
        return DeleteAccountPygame(self.game_manager)

    def draw_text(self, text, font, color, pos):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=pos)
        self.screen.blit(surface, rect)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                
                if self.back_button.handle_event(event): return self.back_button.action()
                if self.modify_avatar_button.handle_event(event): return self.modify_avatar_button.action()
                if self.update_account_button.handle_event(event): return self.update_account_button.action()
                if self.delete_account_button.handle_event(event): return self.delete_account_button.action()
            
            self.screen.fill(self.CYBER_GREY)
            self.draw_text("MON PROFIL", self.font_large, self.CYBER_BLUE, (self.screen_width // 2, 60))
            
            if self.avatar_image:
                avatar_rect = self.avatar_image.get_rect(center=(self.screen_width // 2, 200))
                self.screen.blit(self.avatar_image, avatar_rect)
            
            self.draw_text(f"Pseudo: {self.user[3]}", self.font_medium, self.LIGHT_GREY, (self.screen_width // 2, 290))

            self.modify_avatar_button.draw(self.screen)
            self.update_account_button.draw(self.screen)
            self.delete_account_button.draw(self.screen)
            self.back_button.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(60)
