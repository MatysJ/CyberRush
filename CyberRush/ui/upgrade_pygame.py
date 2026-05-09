import pygame
import io
from db import Connect
from ui.button import Button

class UpgradePygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        
        self.gold = self._get_latest_gold()

        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Améliorations")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        self.GOLD_COLOR = (255, 215, 0)
        self.GREEN_COLOR = (50, 200, 50)
        self.RED_COLOR = (200, 50, 50)
        
        self.font_title = pygame.font.Font(None, 50)
        self.font_item = pygame.font.Font(None, 32)
        self.font_desc = pygame.font.Font(None, 24)

        self.back_button = Button("Retour Menu", (self.screen_width // 2, self.screen_height - 60), self.go_back, size=(200, 50))
        self.list_bottom_y = self.screen_height - 100

        self.scroll_y = 0
        self.item_height = 150 
        self.list_top_y = 100
        self.viewable_height = self.list_bottom_y - self.list_top_y
        
        self.action_buttons = []
        self.my_units = self.load_player_units()
        self.total_content_height = len(self.my_units) * self.item_height
        self._build_buttons()

    def _build_buttons(self):
        """Construit les boutons d'amélioration dynamiquement sans les recréer à chaque frame."""
        self.action_buttons.clear()
        for i, unit in enumerate(self.my_units):
            y_pos = self.list_top_y + (i * self.item_height) - self.scroll_y + 50
            
            if unit['level'] >= 10:
                btn = Button("Niveau Max", (self.screen_width - 150, y_pos), lambda: None, size=(200, 50), color=self.CYBER_GREY)
            elif self.gold >= unit['cost'] and unit['copies'] >= unit['copies_needed']:
                btn = Button(f"Améliorer ({unit['cost']} Or)", (self.screen_width - 150, y_pos), 
                             lambda u=unit: self.upgrade_unit(u), size=(200, 50), color=self.GREEN_COLOR)
            else:
                btn = Button("Fonds/Copies", (self.screen_width - 150, y_pos), lambda: None, size=(200, 50), color=self.RED_COLOR)
                
            self.action_buttons.append(btn)
        
    def _get_latest_gold(self):
        db = Connect()
        if db:
            c = db.cursor()
            c.execute("SELECT Gold FROM users WHERE ID_Users = %s", (self.user_id,))
            res = c.fetchone()
            c.close()
            db.close()
            if res: return res[0]
        return self.user[9]

    def load_player_units(self):
        units = []
        db = Connect()
        if not db: return units
        try:
            cursor = db.cursor(dictionary=True)
            query = """
                SELECT u.ID_Unit, u.Name, u.Image_Data, pu.Level, pu.Card_Count 
                FROM player_units pu
                JOIN units u ON pu.ID_Unit = u.ID_Unit
                WHERE pu.ID_Users = %s
            """
            cursor.execute(query, (self.user_id,))
            result = cursor.fetchall()
            
            for row in result:
                unit_img = None
                if row.get('Image_Data'):
                    try:
                        image_stream = io.BytesIO(row['Image_Data'])
                        loaded_img = pygame.image.load(image_stream).convert_alpha()
                        unit_img = pygame.transform.scale(loaded_img, (100, 100))
                    except: pass
                
                lvl = row['Level']
                cost = lvl * 100
                copies_needed = lvl * 5
                
                units.append({
                    'id': row['ID_Unit'],
                    'name': row['Name'],
                    'level': lvl,
                    'copies': row['Card_Count'],
                    'cost': cost,
                    'copies_needed': copies_needed,
                    'image': unit_img
                })
            cursor.close()
            db.close()
        except Exception as e:
            print(f"Erreur chargement unités du joueur : {e}")
        return units

    def upgrade_unit(self, unit):
        lvl = unit['level']
        if lvl >= 10: return
        
        cost = unit['cost']
        copies_needed = unit['copies_needed']
        
        if self.gold >= cost and unit['copies'] >= copies_needed:
            db = Connect()
            if db:
                try:
                    cursor = db.cursor()
                    new_gold = self.gold - cost
                    cursor.execute("UPDATE users SET Gold = %s WHERE ID_Users = %s", (new_gold, self.user_id))
                    
                    new_copies = unit['copies'] - copies_needed
                    new_level = lvl + 1
                    cursor.execute("UPDATE player_units SET Level = %s, Card_Count = %s WHERE ID_Users = %s AND ID_Unit = %s", 
                                   (new_level, new_copies, self.user_id, unit['id']))
                    
                    db.commit()
                    self.gold = new_gold
                    
                    unit['level'] = new_level
                    unit['copies'] = new_copies
                    unit['cost'] = new_level * 100
                    unit['copies_needed'] = new_level * 5
                    
                    self._build_buttons()
                    
                except Exception as e:
                    print(f"Erreur amélioration : {e}")
                finally:
                    cursor.close()
                    db.close()

    def go_back(self):
        user_list = list(self.user)
        user_list[9] = self.gold 
        self.user = tuple(user_list)
        
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, self.user)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                
                if event.type == pygame.MOUSEWHEEL:
                    self.scroll_y -= event.y * 20
                    max_scroll = max(0, self.total_content_height - self.viewable_height + 100)
                    self.scroll_y = max(0, min(self.scroll_y, max_scroll))
                    self._build_buttons()
                
                if self.back_button.handle_event(event):
                    return self.back_button.action()

                for i, btn in enumerate(self.action_buttons):
                    item_y_start = self.list_top_y + (i * self.item_height) - self.scroll_y
                    if item_y_start + self.item_height > self.list_top_y and item_y_start < self.list_bottom_y:
                        if btn.handle_event(event):
                            btn.action()

            self.screen.fill(self.CYBER_GREY)

            for i, unit in enumerate(self.my_units):
                current_y = self.list_top_y + (i * self.item_height) - self.scroll_y
                
                if current_y + self.item_height > self.list_top_y and current_y < self.list_bottom_y:
                    card_rect = pygame.Rect(50, current_y, self.screen_width - 100, self.item_height - 10)
                    pygame.draw.rect(self.screen, (40, 40, 40), card_rect, border_radius=10)
                    
                    if unit['image']:
                        self.screen.blit(unit['image'], (60, current_y + 10))
                    else:
                        pygame.draw.rect(self.screen, (0, 0, 0), (60, current_y + 10, 100, 100))
                    
                    name_surf = self.font_item.render(f"{unit['name']} - NV {unit['level']}", True, self.CYBER_BLUE)
                    self.screen.blit(name_surf, (180, current_y + 20))
                    
                    bonus = (unit['level'] - 1) * 20
                    desc_text = f"Dégâts de base en jeu : +{bonus}%"
                    desc_surf = self.font_desc.render(desc_text, True, self.LIGHT_GREY)
                    self.screen.blit(desc_surf, (180, current_y + 55))
                    
                    if unit['level'] < 10:
                        copies_color = self.GREEN_COLOR if unit['copies'] >= unit['copies_needed'] else self.RED_COLOR
                        copies_text = f"Copies possedées: {unit['copies']} / {unit['copies_needed']}"
                        copies_surf = self.font_desc.render(copies_text, True, copies_color)
                        self.screen.blit(copies_surf, (180, current_y + 85))
                    else:
                        max_surf = self.font_desc.render("Niveau maximum atteint !", True, self.GOLD_COLOR)
                        self.screen.blit(max_surf, (180, current_y + 85))
                    
                    self.action_buttons[i].draw(self.screen)

            pygame.draw.rect(self.screen, self.CYBER_GREY, (0, 0, self.screen_width, self.list_top_y))
            pygame.draw.rect(self.screen, self.CYBER_GREY, (0, self.list_bottom_y, self.screen_width, 150))
            
            title_surf = self.font_title.render("AMÉLIORER VOS UNITÉS", True, self.CYBER_BLUE)
            self.screen.blit(title_surf, (20, 20))
            
            gold_surf = self.font_title.render(f"Or : {self.gold}", True, self.GOLD_COLOR)
            gold_rect = gold_surf.get_rect(topright=(self.screen_width - 20, 20))
            self.screen.blit(gold_surf, gold_rect)

            self.back_button.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(60)
