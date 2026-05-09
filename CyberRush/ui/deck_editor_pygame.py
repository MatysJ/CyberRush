import pygame
import threading 
import io
from db import Connect
from ui.button import Button

class DeckEditorPygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        
        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Gérer mon Deck")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        
        self.font_title = pygame.font.Font(None, 50)
        self.font_item = pygame.font.Font(None, 24)
        
        self.back_button = Button("Retour", (self.screen_width // 2, self.screen_height - 60), self.go_back, size=(200, 50))
        self.btn_legend_menu = Button("Légendes", (self.screen_width - 130, 50), self.open_legend_menu, size=(200, 40), color=(180, 0, 255))
        
        self.item_height = 80
        self.list_top_y = 100
        self.list_bottom_y = self.screen_height - 100
        
        self.divider_x = self.screen_width // 2

        self.collection_scroll_y = 0
        self.deck_scroll_y = 0
        
        self.collection = []
        self.current_deck = []
        
        self.coll_buttons = []
        self.deck_buttons = []
        
        self.load_data()

    def load_data(self):
        self.collection.clear()
        self.current_deck.clear()
        
        db = Connect()
        if db:
            try:
                c = db.cursor(dictionary=True)
                
                c.execute("""
                    SELECT ud.ID, u.Name, u.Image_Data 
                    FROM user_deck ud 
                    JOIN units u ON ud.ID_Unit = u.ID_Unit 
                    WHERE ud.ID_Users = %s AND ud.Deck_Slot = 0
                """, (self.user_id,))
                for r in c.fetchall():
                    img = self.blob_to_img(r['Image_Data'])
                    self.collection.append({'id_entry': r['ID'], 'name': r['Name'], 'image': img})

                c.execute("""
                    SELECT ud.ID, u.Name, u.Image_Data, ud.Deck_Slot 
                    FROM user_deck ud 
                    JOIN units u ON ud.ID_Unit = u.ID_Unit 
                    WHERE ud.ID_Users = %s AND ud.Deck_Slot > 0 
                    ORDER BY ud.Deck_Slot
                """, (self.user_id,))
                for r in c.fetchall():
                    img = self.blob_to_img(r['Image_Data'])
                    self.current_deck.append({
                        'id_entry': r['ID'], 
                        'name': r['Name'], 
                        'image': img, 
                        'slot': r['Deck_Slot']
                    })
                c.close()
                db.close()
            except Exception as e:
                print(f"[Erreur Chargement Deck] : {e}")
                
        self._build_buttons()

    def _build_buttons(self):
        """Construit les boutons d'ajout et de retrait pour éviter de les recréer chaque frame"""
        self.coll_buttons.clear()
        for i, unit in enumerate(self.collection):
            y = self.list_top_y + i * self.item_height - self.collection_scroll_y
            btn = Button(">", (self.divider_x - 50, y + 40), lambda ue=unit['id_entry']: self.move_to_deck(ue), size=(40, 40))
            self.coll_buttons.append(btn)

        self.deck_buttons.clear()
        for i, unit in enumerate(self.current_deck):
            y = self.list_top_y + i * self.item_height - self.deck_scroll_y
            btn = Button("<", (self.divider_x + 50, y + 40), lambda ue=unit['id_entry']: self.remove_from_deck(ue), size=(40, 40))
            self.deck_buttons.append(btn)

    def blob_to_img(self, blob):
        if not blob: return None
        try:
            return pygame.transform.scale(pygame.image.load(io.BytesIO(blob)), (60, 60))
        except: return None

    def move_to_deck(self, id_entry):
        if len(self.current_deck) >= 8:
            print("Votre deck est plein (8 cartes maximum) !")
            return

        used_slots = [u['slot'] for u in self.current_deck]
        free_slot = 1
        while free_slot in used_slots:
            free_slot += 1
        
        self.update_slot(id_entry, free_slot)
        
        for i, u in enumerate(self.collection):
            if u['id_entry'] == id_entry:
                item = self.collection.pop(i)
                item['slot'] = free_slot
                self.current_deck.append(item)
                self.current_deck.sort(key=lambda x: x['slot'])
                break
        
        self._build_buttons()

    def remove_from_deck(self, id_entry):
        self.update_slot(id_entry, 0)
        
        for i, u in enumerate(self.current_deck):
            if u['id_entry'] == id_entry:
                item = self.current_deck.pop(i)
                if 'slot' in item: 
                    del item['slot']
                self.collection.append(item)
                break
                
        self._build_buttons()

    def _db_update_slot_thread(self, id_entry, new_slot):
        """La vraie requête qui tourne en secret pour ne pas bloquer l'écran"""
        db = Connect()
        if db:
            try:
                c = db.cursor()
                c.execute("UPDATE user_deck SET Deck_Slot = %s WHERE ID = %s", (new_slot, id_entry))
                db.commit()
            except Exception as e:
                pass
            finally:
                try: c.close()
                except: pass
                db.close()

    def update_slot(self, id_entry, new_slot):
        """Lance la requête en tâche de fond instantanément !"""
        threading.Thread(target=self._db_update_slot_thread, args=(id_entry, new_slot), daemon=True).start()

    def go_back(self):
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, self.user)
    
    def open_legend_menu(self):
        from ui.legend_selection_pygame import LegendSelectionPygame
        return LegendSelectionPygame(self.game_manager, self.user)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None
                if event.type == pygame.MOUSEWHEEL:
                    self.collection_scroll_y = max(0, self.collection_scroll_y - event.y * 20)
                    self.deck_scroll_y = max(0, self.deck_scroll_y - event.y * 20)
                    self._build_buttons()
                
                if self.back_button.handle_event(event): return self.back_button.action()

                if self.btn_legend_menu.handle_event(event): return self.btn_legend_menu.action()
                
                for i, btn in enumerate(self.coll_buttons):
                    row_top = self.list_top_y + i * self.item_height - self.collection_scroll_y
                    if row_top + 80 > self.list_top_y and row_top < self.list_bottom_y:
                        if btn.handle_event(event): btn.action()
                
                for i, btn in enumerate(self.deck_buttons):
                    row_top = self.list_top_y + i * self.item_height - self.deck_scroll_y
                    if row_top + 80 > self.list_top_y and row_top < self.list_bottom_y:
                        if btn.handle_event(event): btn.action()

            self.screen.fill(self.CYBER_GREY)
            
            title_coll = self.font_title.render("COLLECTION", True, self.CYBER_BLUE)
            self.screen.blit(title_coll, (50, 40))
            title_deck = self.font_title.render(f"MON DECK ({len(self.current_deck)}/8)", True, self.CYBER_BLUE)
            self.screen.blit(title_deck, (self.divider_x + 50, 40))
            
            pygame.draw.line(self.screen, self.CYBER_BLUE, (self.divider_x, 100), (self.divider_x, self.screen_height - 100), 2)

            for i, unit in enumerate(self.collection):
                y = self.list_top_y + i * self.item_height - self.collection_scroll_y
                if y + self.item_height > self.list_top_y and y < self.list_bottom_y:
                    if unit['image']: self.screen.blit(unit['image'], (50, y + 10))
                    name = self.font_item.render(unit['name'], True, self.LIGHT_GREY)
                    self.screen.blit(name, (130, y + 30))
                    self.coll_buttons[i].draw(self.screen)

            for i, unit in enumerate(self.current_deck):
                y = self.list_top_y + i * self.item_height - self.deck_scroll_y
                if y + self.item_height > self.list_top_y and y < self.list_bottom_y:
                    self.deck_buttons[i].draw(self.screen)
                    if unit['image']: self.screen.blit(unit['image'], (self.divider_x + 100, y + 10))
                    name = self.font_item.render(f"{unit['name']} (Slot {unit['slot']})", True, self.LIGHT_GREY)
                    self.screen.blit(name, (self.divider_x + 180, y + 30))

            pygame.draw.rect(self.screen, self.CYBER_GREY, (0, 0, self.screen_width, self.list_top_y))
            pygame.draw.rect(self.screen, self.CYBER_GREY, (0, self.list_bottom_y, self.screen_width, 100))
            self.screen.blit(title_coll, (50, 40))
            self.screen.blit(title_deck, (self.divider_x + 50, 40))

            self.back_button.draw(self.screen)

            self.btn_legend_menu.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)
