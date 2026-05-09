import pygame
import io
from db import Connect
from ui.button import Button

class LegendSelectionPygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface()

        self.font_title = pygame.font.Font(None, 60)
        self.font = pygame.font.Font(None, 30)
        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.WHITE = (255, 255, 255)

        self.back_button = Button("Retour au Deck", (self.screen_width // 2, self.screen_height - 60), self.go_back, size=(200, 50))

        self.legends = []
        self.load_legends()

    def load_legends(self):
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                query = """
                    SELECT l.ID_Legend, l.legend_name, l.Image_Data
                    FROM legend l
                    LEFT JOIN player_legends pl ON l.ID_Legend = pl.ID_Legend AND pl.ID_Users = %s
                    WHERE l.ID_Legend = 0 OR pl.ID_PlayerLegend IS NOT NULL
                """
                cursor.execute(query, (self.user_id,))
                results = cursor.fetchall()

                start_x = 150
                start_y = 150
                spacing_x = 200
                spacing_y = 200
                col = 0
                row = 0

                for row_data in results:
                    l_id = row_data[0]
                    l_name = row_data[1]
                    img_data = row_data[2]

                    img_surface = None
                    if img_data:
                        try:
                            img_surface = pygame.image.load(io.BytesIO(img_data)).convert_alpha()
                            img_surface = pygame.transform.scale(img_surface, (100, 100))
                        except Exception as e:
                            print(f"Erreur image légende {l_id}: {e}")

                    if not img_surface:
                        img_surface = pygame.Surface((100, 100))
                        img_surface.fill((100, 100, 100))

                    x = start_x + col * spacing_x
                    y = start_y + row * spacing_y

                    btn = Button(l_name, (x + 50, y + 130), lambda i=l_id: self.select_legend(i), size=(120, 30))

                    self.legends.append({
                        'id': l_id,
                        'image': img_surface,
                        'rect': img_surface.get_rect(topleft=(x, y)),
                        'button': btn
                    })

                    col += 1
                    if col > 4: 
                        col = 0
                        row += 1

            except Exception as e:
                print(f"Erreur chargement légendes : {e}")
            finally:
                db.close()

    def select_legend(self, legend_id):
        def _db_update_legend():
            db = Connect()
            if db:
                try:
                    cursor = db.cursor()
                    cursor.execute("UPDATE users SET Legend = %s WHERE ID_Users = %s", (legend_id, self.user_id))
                    db.commit()
                except Exception as e:
                    pass
                finally:
                    try: cursor.close()
                    except: pass
                    db.close()
                    
        import threading
        threading.Thread(target=_db_update_legend, daemon=True).start()
        
        return self.go_back()

    def go_back(self):
        from ui.deck_editor_pygame import DeckEditorPygame 
        return DeckEditorPygame(self.game_manager, self.user)

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None

                if self.back_button.handle_event(event):
                    return self.back_button.action()

                for leg in self.legends:
                    if leg['button'].handle_event(event):
                        return leg['button'].action()
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if leg['rect'].collidepoint(event.pos):
                            return self.select_legend(leg['id'])

            self.screen.fill(self.CYBER_GREY)

            title = self.font_title.render("SÉLECTION DE LÉGENDE", True, self.CYBER_BLUE)
            self.screen.blit(title, title.get_rect(center=(self.screen_width // 2, 50)))
            
            for leg in self.legends:
                self.screen.blit(leg['image'], leg['rect'])
                leg['button'].draw(self.screen)

            self.back_button.draw(self.screen)

            pygame.display.flip()
            clock.tick(60)
