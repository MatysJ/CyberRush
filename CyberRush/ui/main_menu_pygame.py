import pygame
import sys
import io
from ui.button import Button
from db import Connect
from ui.lobby_pygame import LobbyPygame 
from ui.messaging_pygame import MessagingPygame 

class MainMenuPygame:
    def __init__(self, game_manager, user=None):
        self.game_manager = game_manager
        self.user = user
        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Menu Principal")
        self.clock = pygame.time.Clock()
        
        self.network_client = self.game_manager.network_client

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        self.GOLD_COLOR = (255, 215, 0)
        
        self.font_title = pygame.font.Font(None, 60)
        self.font_info = pygame.font.Font(None, 28)

        self.buttons = []
        self.avatar_image = None

        if self.user:
            self.refresh_user_data() # NOUVEAU : On charge les données 1 seule fois !
            self.load_avatar()

        self.setup_ui()

    def load_avatar(self):
        if not self.user: return
        db = Connect()
        if not db: return
        try:
            user_id = self.user[0]
            cursor = db.cursor()
            query = """
                SELECT a.Image_Data 
                FROM avatars a
                JOIN users u ON u.Avatar = a.ID_Avatar
                WHERE u.ID_Users = %s
            """
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            cursor.close()
            db.close()
            if result and result[0]:
                image_data = result[0]
                image_stream = io.BytesIO(image_data)
                avatar_img = pygame.image.load(image_stream)
                self.avatar_image = pygame.transform.scale(avatar_img, (80, 80))
        except Exception as e:
            print(f"Erreur lors du chargement de l'avatar pour le menu : {e}")

    def setup_ui(self):
        self.buttons.clear()
        y_pos = 200
        if self.user:
            self.buttons.append(Button("Jouer", (self.screen_width // 2, y_pos), self.on_play))
            self.buttons.append(Button("Boutique", (self.screen_width // 2, y_pos + 60), self.on_shop))
            self.buttons.append(Button("Amélioration", (self.screen_width // 2, y_pos + 120), self.on_upgrade))
            
            self.buttons.append(Button("Gérer mes amis", (self.screen_width // 2, y_pos + 180), self.on_friends))
            self.buttons.append(Button("Mon Profil", (self.screen_width // 2, y_pos + 240), self.on_profile))
            self.buttons.append(Button("Gérer mon Deck", (self.screen_width // 2, y_pos + 300), self.on_deck))
            self.buttons.append(Button("Déconnexion", (self.screen_width // 2, y_pos + 360), self.on_logout))
            
            self.buttons.append(Button("Messagerie", (120, self.screen_height - 60), self.open_messaging, size=(180, 50), color=(0, 150, 255)))
        else:
            self.buttons.append(Button("Se connecter", (self.screen_width // 2, y_pos), self.on_login))
            self.buttons.append(Button("S'inscrire", (self.screen_width // 2, y_pos + 60), self.on_register))

        self.buttons.append(Button("Quitter", (self.screen_width // 2, self.screen_height - 60), self.on_quit))
        self.buttons.append(Button("Paramètres", (self.screen_width - 100, self.screen_height - 60), self.open_settings, size=(160, 50), color=(100, 100, 100)))

    def refresh_user_data(self):
        db = Connect()
        
        # Valeurs par défaut au cas où
        self.display_gold = self.user[9]
        self.display_level = self.user[6] if self.user[6] else 1
        self.display_xp = self.user[10] if self.user[10] else 0

        if db:
            try:
                c = db.cursor()
                c.execute("SELECT Gold, Level, Experience FROM users WHERE ID_Users = %s", (self.user[0],))
                res = c.fetchone()
                if res:
                    self.display_gold, self.display_level, self.display_xp = res
                
                # Gestion du Level UP
                xp_required = int(100 * (1.25 ** (self.display_level - 1)))
                leveled_up = False
                
                while self.display_xp >= xp_required:
                    self.display_xp -= xp_required
                    self.display_level += 1
                    xp_required = int(100 * (1.25 ** (self.display_level - 1)))
                    leveled_up = True
                    
                if leveled_up:
                    c.execute("UPDATE users SET Level = %s, Experience = %s WHERE ID_Users = %s", (self.display_level, self.display_xp, self.user[0]))
                    db.commit()
                    print(f"LEVEL UP ! Niveau {self.display_level} atteint !")
                    
                c.close()
            except Exception as e:
                print(f"Erreur chargement infos: {e}")
            finally:
                db.close()

    def draw_user_info(self):
        if self.user:
            pseudo = self.user[3] 
            email = self.user[1]
            
            # On utilise les variables pré-calculées
            gold = getattr(self, 'display_gold', 0)
            level = getattr(self, 'display_level', 1)
            xp = getattr(self, 'display_xp', 0)
            xp_required = int(100 * (1.25 ** (level - 1)))
            
            pseudo_surface = self.font_info.render(f"Pseudo: {pseudo}", True, self.LIGHT_GREY)
            self.screen.blit(pseudo_surface, (20, 20))
            
            email_surface = self.font_info.render(f"Email: {email}", True, self.LIGHT_GREY)
            self.screen.blit(email_surface, (20, 50))

            gold_surface = self.font_info.render(f"Or: {gold}", True, self.GOLD_COLOR)
            self.screen.blit(gold_surface, (20, 80))
            
            level_surface = self.font_info.render(f"Niveau: {level}", True, self.CYBER_BLUE)
            self.screen.blit(level_surface, (20, 110))

            xp_surface = self.font_info.render(f"XP: {int(xp)} / {xp_required}", True, (50, 200, 50))
            self.screen.blit(xp_surface, (20, 140))
            
            if self.avatar_image:
                avatar_pos = (self.screen_width - self.avatar_image.get_width() - 20, 20)
                self.screen.blit(self.avatar_image, avatar_pos)

    
    def on_deck(self):
        from ui.deck_editor_pygame import DeckEditorPygame
        return DeckEditorPygame(self.game_manager, self.user)

    def on_play(self):
        if self.network_client and self.network_client.client_socket:
            return LobbyPygame(self.game_manager, self.user)
        else:
            print("Erreur : Non connecté au serveur.")
            return self

    def on_shop(self):
        from ui.shop_pygame import ShopPygame
        return ShopPygame(self.game_manager, self.user)

    def on_friends(self):
        from ui.friends_pygame import FriendsPygame
        return FriendsPygame(self.game_manager, self.user)

    def on_logout(self):
        if self.network_client:
            self.network_client.close()
            self.game_manager.network_client = None
        return MainMenuPygame(self.game_manager, user=None)

    def on_login(self):
        from ui.login_pygame import LoginPygame
        return LoginPygame(self.game_manager)

    def on_register(self):
        from ui.register_pygame import RegisterPygame
        return RegisterPygame(self.game_manager)
    
    def on_profile(self):
        from ui.profile_pygame import ProfilePygame
        return ProfilePygame(self.game_manager, user=self.user)
        
    def on_quit(self):
        if self.network_client:
            self.network_client.close()
        return None
    
    def open_messaging(self):
        return MessagingPygame(self.game_manager, self.user)
    
    def on_upgrade(self):
        from ui.upgrade_pygame import UpgradePygame
        return UpgradePygame(self.game_manager, self.user)
    
    def open_settings(self):
        from ui.settings_pygame import SettingsPygame
        return SettingsPygame(self.game_manager, self.user)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return self.on_quit()
                
                for button in self.buttons:
                    if button.handle_event(event):
                        return button.action()

            self.screen.fill(self.CYBER_GREY)
            
            title_render = self.font_title.render("Cyber Rush", True, self.CYBER_BLUE)
            title_rect = title_render.get_rect(center=(self.screen_width // 2, 80))
            self.screen.blit(title_render, title_rect)
            
            self.draw_user_info()

            for button in self.buttons:
                button.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(60)