import pygame
import sys
import io
from db import Connect
from ui.button import Button

class AvatarSelectorPygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]

        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Choisir un Avatar")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        self.HOVER_COLOR = (255, 215, 0) 

        self.font_title = pygame.font.Font(None, 60)

        self.back_button = Button("Retour", (self.screen_width // 2, self.screen_height - 60), self.go_back, size=(200, 50))

        self.avatars = self.load_avatars()
        
        self.avatar_size = 120
        self.padding = 50
        self.cols = 5
        
        total_grid_width = (self.cols * self.avatar_size) + ((self.cols - 1) * self.padding)
        self.start_x = (self.screen_width - total_grid_width) // 2
        self.start_y = 200 

    def load_avatars(self):
        avatars_list = []
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT ID_Avatar, Image_Data FROM avatars")
                rows = cursor.fetchall()
                for row in rows:
                    if row[1]:
                        image_stream = io.BytesIO(row[1])
                        img = pygame.image.load(image_stream).convert_alpha()
                        scaled_img = pygame.transform.scale(img, (120, 120))
                        avatars_list.append({'id': row[0], 'image': scaled_img})
                cursor.close()
                db.close()
            except Exception as e:
                print(f"Erreur chargement avatars: {e}")
        return avatars_list

    def select_avatar(self, avatar_id):
        print(f"Avatar {avatar_id} sélectionné.")
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("UPDATE users SET Avatar = %s WHERE ID_Users = %s", (avatar_id, self.user_id))
                db.commit()
                cursor.execute("SELECT * FROM users WHERE ID_Users = %s", (self.user_id,))
                updated_user = cursor.fetchone()
                cursor.close()
                db.close()
                from ui.profile_pygame import ProfilePygame
                return ProfilePygame(self.game_manager, updated_user)
            except Exception as e:
                print(f"Erreur update avatar: {e}")
        return self

    def go_back(self):
        from ui.profile_pygame import ProfilePygame
        return ProfilePygame(self.game_manager, self.user)

    def run(self):
        while True:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                
                if self.back_button.handle_event(event):
                    return self.back_button.action()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        for i, av in enumerate(self.avatars):
                            row = i // self.cols
                            col = i % self.cols
                            
                            x = self.start_x + col * (self.avatar_size + self.padding)
                            y = self.start_y + row * (self.avatar_size + self.padding)
                            
                            rect = pygame.Rect(x, y, self.avatar_size, self.avatar_size)
                            if rect.collidepoint(mouse_pos):
                                return self.select_avatar(av['id'])

            self.screen.fill(self.CYBER_GREY)
            
            title_surf = self.font_title.render("SÉLECTIONNEZ VOTRE AVATAR", True, self.CYBER_BLUE)
            title_rect = title_surf.get_rect(center=(self.screen_width // 2, 80))
            self.screen.blit(title_surf, title_rect)

            for i, av in enumerate(self.avatars):
                row = i // self.cols
                col = i % self.cols
                
                x = self.start_x + col * (self.avatar_size + self.padding)
                y = self.start_y + row * (self.avatar_size + self.padding)
                
                rect = pygame.Rect(x, y, self.avatar_size, self.avatar_size)
                
                if rect.collidepoint(mouse_pos):
                    pygame.draw.rect(self.screen, self.HOVER_COLOR, (x - 5, y - 5, self.avatar_size + 10, self.avatar_size + 10), 3)
                else:
                    pygame.draw.rect(self.screen, self.LIGHT_GREY, (x - 2, y - 2, self.avatar_size + 4, self.avatar_size + 4), 1)

                self.screen.blit(av['image'], (x, y))

            self.back_button.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(60)