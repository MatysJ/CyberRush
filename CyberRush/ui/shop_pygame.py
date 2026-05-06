import pygame
import sys
import io
from db import Connect
from ui.button import Button

class ShopPygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        self.gold = user[9] 

        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Boutique")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        self.GOLD_COLOR = (255, 215, 0)
        
        self.font_title = pygame.font.Font(None, 50)
        self.font_item = pygame.font.Font(None, 32)
        self.font_desc = pygame.font.Font(None, 24)

        self.back_button = Button("Retour", (self.screen_width // 2, self.screen_height - 60), self.go_back, size=(200, 50))
        self.list_bottom_y = self.screen_height - 100 

        self.scroll_y = 0
        self.item_height = 150 
        self.list_top_y = 100
        self.viewable_height = self.list_bottom_y - self.list_top_y
        
        # --- CHARGEMENT DES DEUX CATÉGORIES ---
        self.units_data = self.load_units_from_db()
        self.legends_data = self.load_legends_from_db()
        
        # La hauteur totale prend en compte les unités + 1 séparation + les légendes
        self.total_content_height = (len(self.units_data) * self.item_height) + 100 + (len(self.legends_data) * self.item_height)
        
        self.unit_buttons = []
        self.legend_buttons = []
        self._build_buttons()

        self.dragging_scroll = False

    def _build_buttons(self):
        """Génère la liste des boutons pour les Unités et les Légendes."""
        self.unit_buttons.clear()
        for i, unit in enumerate(self.units_data):
            y_pos = self.list_top_y + (i * self.item_height) - self.scroll_y + 50
            btn = Button(f"Acheter ({unit['price']})", (self.screen_width - 150, y_pos), 
                         lambda u=unit: self.buy_unit(u['id'], u['price']), size=(200, 50))
            self.unit_buttons.append(btn)
            
        self.legend_buttons.clear()
        # Les légendes commencent après les unités + 100 pixels de séparation
        y_offset_legends = (len(self.units_data) * self.item_height) + 100
        for i, legend in enumerate(self.legends_data):
            y_pos = self.list_top_y + y_offset_legends + (i * self.item_height) - self.scroll_y + 50
            
            if legend['owned']:
                btn = Button("Possédé", (self.screen_width - 150, y_pos), lambda: None, size=(200, 50), color=(100, 100, 100))
            else:
                btn = Button(f"Acheter (5000)", (self.screen_width - 150, y_pos), 
                             lambda l=legend: self.buy_legend(l['id'], 5000), size=(200, 50), color=(180, 0, 255))
            self.legend_buttons.append(btn)

    def load_units_from_db(self):
        units = []
        db = Connect()
        if not db: return units
        try:
            cursor = db.cursor(dictionary=True)
            query = """
                SELECT u.*, COALESCE(pu.Card_Count, 0) as OwnedCount
                FROM units u
                LEFT JOIN player_units pu ON u.ID_Unit = pu.ID_Unit AND pu.ID_Users = %s
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
                
                units.append({
                    'id': row['ID_Unit'],
                    'name': row['Name'],
                    'price': row['Price'],
                    'description': row.get('SpecialEffect', 'Aucune description'),
                    'owned': row['OwnedCount'],
                    'image': unit_img
                })
            cursor.close()
            db.close()
        except Exception as e:
            print(f"Erreur chargement unités boutique : {e}")
        return units

    def load_legends_from_db(self):
        legends = []
        db = Connect()
        if not db: return legends
        
        # Dictionnaire des résumés de compétences (ajout de 'None')
        summaries = {
            "Garen": "Passif: Toute les 25 vagues, augmente les HP de 1.",
            "Azir": "Passif : Invoque une unité lvl 2 aléatoire (évolue toutes les 20 vagues).",
            "Kindred": "Actif (CD 20) : Invulnérabilité totale aux dégâts pendant une vague.",
            "Briar": "Passif : +12% de dégâts pour chaque point de vie manquant.",
            "Mordekaiser": "Passif : Toute les 5 vagues, ajoute 3 ennemis de façon permanente à l'adversaire.",
            "Karthus": "Passif : Survit au premier coup fatal. Actif (CD 15) : Détruit une unité ennemie aléatoire.",
            "Ornn": "Actif (CD 5) : Améliore le niveau d'une unité alliée aléatoire."
        }
        
        try:
            cursor = db.cursor(dictionary=True)
            # MODIFICATION ICI : On force IsOwned à 1 si l'ID_Legend est 0.
            query = """
                SELECT l.*, 
                       CASE 
                           WHEN l.ID_Legend = 0 THEN 1
                           WHEN pl.ID_PlayerLegend IS NOT NULL THEN 1 
                           ELSE 0 
                       END as IsOwned
                FROM legend l
                LEFT JOIN player_legends pl ON l.ID_Legend = pl.ID_Legend AND pl.ID_Users = %s
            """
            cursor.execute(query, (self.user_id,))
            result = cursor.fetchall()
            
            for row in result:
                legend_img = None
                if row.get('Image_Data'):
                    try:
                        image_stream = io.BytesIO(row['Image_Data'])
                        loaded_img = pygame.image.load(image_stream).convert_alpha()
                        legend_img = pygame.transform.scale(loaded_img, (100, 100))
                    except: pass
                
                l_name = row['legend_name']
                desc = summaries.get(l_name, "Compétence inconnue")
                
                # Petit nettoyage visuel pour la boutique
                display_name = "Garen" if row['ID_Legend'] == 0 else l_name
                
                legends.append({
                    'id': row['ID_Legend'],
                    'name': display_name,
                    'description': desc,
                    'owned': bool(row['IsOwned']),
                    'image': legend_img
                })
            cursor.close()
            db.close()
        except Exception as e:
            print(f"Erreur chargement légendes boutique : {e}")
        return legends

    def buy_unit(self, unit_id, price):
        if self.gold >= price:
            # 1. CHANGEMENT VISUEL IMMÉDIAT (UI Optimiste)
            self.gold -= price
            for u in self.units_data:
                if u['id'] == unit_id:
                    u['owned'] += 1
                    break
            self._build_buttons() # On rafraîchit l'écran tout de suite !

            # 2. ENVOI À LA BDD EN TÂCHE DE FOND
            def _db_buy():
                db = Connect()
                if db:
                    try:
                        cursor = db.cursor()
                        cursor.execute("UPDATE users SET Gold = %s WHERE ID_Users = %s", (self.gold, self.user_id))
                        cursor.execute("SELECT * FROM player_units WHERE ID_Users = %s AND ID_Unit = %s", (self.user_id, unit_id))
                        if cursor.fetchone():
                            cursor.execute("UPDATE player_units SET Card_Count = Card_Count + 1 WHERE ID_Users = %s AND ID_Unit = %s", (self.user_id, unit_id))
                        else:
                            cursor.execute("INSERT INTO player_units (ID_Users, ID_Unit, Level, Card_Count) VALUES (%s, %s, 1, 1)", (self.user_id, unit_id))
                            cursor.execute("INSERT INTO user_deck (ID_Users, ID_Unit, Deck_Slot) VALUES (%s, %s, 0)", (self.user_id, unit_id))
                        db.commit()
                    except Exception as e:
                        print(f"Erreur transaction BDD: {e}")
                    finally:
                        try: cursor.close()
                        except: pass
                        db.close()
            
            import threading
            threading.Thread(target=_db_buy, daemon=True).start()

    def buy_legend(self, legend_id, price=5000):
        if self.gold >= price:
            # 1. CHANGEMENT VISUEL IMMÉDIAT (UI Optimiste)
            self.gold -= price
            for l in self.legends_data:
                if l['id'] == legend_id:
                    l['owned'] = True
                    break
            self._build_buttons() # Rafraîchissement instantané du bouton en gris "Possédé" !
            print(f"Légende {legend_id} achetée avec succès ! Or restant : {self.gold}")

            # 2. ENVOI À LA BDD EN TÂCHE DE FOND
            def _db_buy_legend():
                db = Connect()
                if db:
                    try:
                        cursor = db.cursor()
                        # Sécurité BDD : On vérifie qu'on ne l'a pas déjà achetée
                        cursor.execute("SELECT * FROM player_legends WHERE ID_Users = %s AND ID_Legend = %s", (self.user_id, legend_id))
                        if not cursor.fetchone():
                            # Sauvegarde des nouvelles données
                            cursor.execute("UPDATE users SET Gold = %s WHERE ID_Users = %s", (self.gold, self.user_id))
                            cursor.execute("INSERT INTO player_legends (ID_Users, ID_Legend) VALUES (%s, %s)", (self.user_id, legend_id))
                            db.commit()
                    except Exception as e:
                        print(f"Erreur transaction BDD légende : {e}")
                    finally:
                        try: cursor.close()
                        except: pass
                        db.close()
            
            import threading
            threading.Thread(target=_db_buy_legend, daemon=True).start()
        else:
            print("Pas assez d'or pour acheter cette Légende.")

    def go_back(self):
        # On met à jour l'or dans la mémoire locale SANS refaire un SELECT lourd
        user_list = list(self.user)
        user_list[9] = self.gold 
        self.user = tuple(user_list)
        
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, self.user)

    def draw_wrapped_text(self, text, font, color, rect):
        if not text: return
        words = text.split(' ')
        space = font.size(' ')[0]
        x, y = rect.x, rect.y
        for word in words:
            word_surf = font.render(word, True, color)
            word_w, word_h = word_surf.get_size()
            if x + word_w >= rect.right:
                x = rect.x
                y += word_h
            self.screen.blit(word_surf, (x, y))
            x += word_w + space

    def run(self):
        while True:
            mouse_pos = pygame.mouse.get_pos()
            
            max_scroll = max(0, self.total_content_height - self.viewable_height)
            
            scrollbar_x = self.screen_width - 20
            if self.total_content_height > 0:
                thumb_height = max(30, (self.viewable_height / self.total_content_height) * self.viewable_height)
            else:
                thumb_height = self.viewable_height
                
            scroll_progress = self.scroll_y / max_scroll if max_scroll > 0 else 0
            thumb_y = self.list_top_y + scroll_progress * (self.viewable_height - thumb_height)
            thumb_rect = pygame.Rect(scrollbar_x, thumb_y, 10, thumb_height)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                
                if event.type == pygame.MOUSEWHEEL:
                    self.scroll_y -= event.y * 30
                    self.scroll_y = max(0, min(self.scroll_y, max_scroll))
                    self._build_buttons()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if thumb_rect.collidepoint(event.pos):
                            self.dragging_scroll = True
                            
                        if self.back_button.handle_event(event):
                            return self.back_button.action()

                        # Clics sur les boutons d'unités
                        for i, btn in enumerate(self.unit_buttons):
                            item_y_start = self.list_top_y + (i * self.item_height) - self.scroll_y
                            if item_y_start + self.item_height > self.list_top_y and item_y_start < self.list_bottom_y:
                                if btn.handle_event(event): btn.action()
                                
                        # Clics sur les boutons de légendes
                        y_offset_legends = (len(self.units_data) * self.item_height) + 100
                        for i, btn in enumerate(self.legend_buttons):
                            item_y_start = self.list_top_y + y_offset_legends + (i * self.item_height) - self.scroll_y
                            if item_y_start + self.item_height > self.list_top_y and item_y_start < self.list_bottom_y:
                                if btn.handle_event(event): btn.action()

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.dragging_scroll = False

                if event.type == pygame.MOUSEMOTION:
                    if getattr(self, 'dragging_scroll', False):
                        rel_y = mouse_pos[1] - self.list_top_y - (thumb_height / 2)
                        track_height = self.viewable_height - thumb_height
                        if track_height > 0:
                            new_progress = rel_y / track_height
                            self.scroll_y = max(0, min(new_progress * max_scroll, max_scroll))
                            self._build_buttons()

            self.screen.fill(self.CYBER_GREY)

            # =========================================================
            # DESSIN DES UNITÉS
            # =========================================================
            for i, unit in enumerate(self.units_data):
                current_y = self.list_top_y + (i * self.item_height) - self.scroll_y
                
                if current_y + self.item_height > self.list_top_y and current_y < self.list_bottom_y:
                    card_rect = pygame.Rect(50, current_y, self.screen_width - 100, self.item_height - 10)
                    pygame.draw.rect(self.screen, (40, 40, 40), card_rect, border_radius=10)
                    
                    if unit['image']:
                        self.screen.blit(unit['image'], (60, current_y + 10))
                    else:
                        pygame.draw.rect(self.screen, (0, 0, 0), (60, current_y + 10, 100, 100))
                    
                    name_surf = self.font_item.render(unit['name'], True, self.CYBER_BLUE)
                    self.screen.blit(name_surf, (180, current_y + 20))
                    
                    owned_surf = self.font_desc.render(f"Possédé : {unit['owned']}", True, self.GOLD_COLOR)
                    self.screen.blit(owned_surf, (self.screen_width - 400, current_y + 25))
                    
                    desc_rect = pygame.Rect(180, current_y + 55, self.screen_width - 450, 80)
                    self.draw_wrapped_text(unit['description'], self.font_desc, self.LIGHT_GREY, desc_rect)
                    
                    if i < len(self.unit_buttons):
                        self.unit_buttons[i].draw(self.screen)

            # =========================================================
            # SÉPARATEUR
            # =========================================================
            separator_y = self.list_top_y + (len(self.units_data) * self.item_height) - self.scroll_y + 50
            if separator_y > self.list_top_y and separator_y < self.list_bottom_y:
                pygame.draw.line(self.screen, self.CYBER_BLUE, (50, separator_y), (self.screen_width - 50, separator_y), 3)
                sep_title = self.font_title.render("LES LÉGENDES", True, (180, 0, 255))
                # MODIFICATION : On place le texte juste au-dessus de la ligne (-10 pixels)
                self.screen.blit(sep_title, sep_title.get_rect(midbottom=(self.screen_width // 2, separator_y - 10)))

            # =========================================================
            # DESSIN DES LÉGENDES
            # =========================================================
            y_offset_legends = (len(self.units_data) * self.item_height) + 100
            for i, legend in enumerate(self.legends_data):
                current_y = self.list_top_y + y_offset_legends + (i * self.item_height) - self.scroll_y
                
                if current_y + self.item_height > self.list_top_y and current_y < self.list_bottom_y:
                    card_rect = pygame.Rect(50, current_y, self.screen_width - 100, self.item_height - 10)
                    pygame.draw.rect(self.screen, (30, 20, 40), card_rect, border_radius=10) # Fond légèrement violacé
                    
                    if legend['image']:
                        self.screen.blit(legend['image'], (60, current_y + 10))
                    else:
                        pygame.draw.rect(self.screen, (0, 0, 0), (60, current_y + 10, 100, 100))
                    
                    name_surf = self.font_item.render(legend['name'], True, (180, 0, 255))
                    self.screen.blit(name_surf, (180, current_y + 20))
                    
                    desc_rect = pygame.Rect(180, current_y + 55, self.screen_width - 450, 80)
                    self.draw_wrapped_text(legend['description'], self.font_desc, self.LIGHT_GREY, desc_rect)
                    
                    if i < len(self.legend_buttons):
                        self.legend_buttons[i].draw(self.screen)

            # --- MASQUES DES MENUS (HAUT ET BAS) ---
            pygame.draw.rect(self.screen, self.CYBER_GREY, (0, 0, self.screen_width, self.list_top_y))
            pygame.draw.rect(self.screen, self.CYBER_GREY, (0, self.list_bottom_y, self.screen_width, 150))
            
            title_surf = self.font_title.render("BOUTIQUE", True, self.CYBER_BLUE)
            self.screen.blit(title_surf, (20, 20))
            
            gold_surf = self.font_title.render(f"Or : {self.gold}", True, self.GOLD_COLOR)
            gold_rect = gold_surf.get_rect(topright=(self.screen_width - 20, 20))
            self.screen.blit(gold_surf, gold_rect)

            self.back_button.draw(self.screen)

            # --- DESSIN DE LA BARRE DE SCROLL INTERACTIVE ---
            if max_scroll > 0:
                pygame.draw.rect(self.screen, (30, 30, 30), (scrollbar_x, self.list_top_y, 10, self.viewable_height), border_radius=5)
                thumb_color = (0, 200, 255) if getattr(self, 'dragging_scroll', False) else self.CYBER_BLUE
                pygame.draw.rect(self.screen, thumb_color, thumb_rect, border_radius=5)

            pygame.display.flip()
            self.clock.tick(60)