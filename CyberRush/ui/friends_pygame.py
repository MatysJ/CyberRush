import pygame
import sys
from db import Connect
from ui.button import Button
from ui.text_input import TextInput

class FriendsPygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Mes amis")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        self.font = pygame.font.Font(None, 28)
        self.font_title = pygame.font.Font(None, 50)

        center_left = self.screen_width // 4
        
        self.pseudo_input = TextInput(center_left - 150, 150, 300, 40, "Pseudo de l'ami")
        self.send_request_button = Button("Envoyer demande", (center_left, 220), self.send_request, size=(200, 40))
        self.back_button = Button("Retour", (self.screen_width // 2, self.screen_height - 50), self.go_back, size=(180, 40))

        self.incoming_requests = [] # Demandes reçues
        self.outgoing_requests = [] # Demandes envoyées en attente
        self.friends = []           # Amis acceptés
        self.load_data()

        # --- NOUVEAU : Chronomètre de rafraîchissement ---
        import time 
        self.last_refresh_time = time.time()
        self.refresh_interval = 5.0 # Rafraîchit toutes les 5 secondes

    def load_data(self):
        db = Connect()
        if db:
            try:
                c = db.cursor()
                # 1. Demandes reçues (En attente)
                c.execute("""
                    SELECT f.ID_Friends, u.Pseudo 
                    FROM friends f 
                    JOIN users u ON f.Sender_ID = u.ID_Users 
                    WHERE f.Receiver_ID = %s AND f.Status = 'Pending'
                """, (self.user_id,))
                self.incoming_requests = c.fetchall()

                # 2. Demandes envoyées (En attente) - NOUVEAU
                c.execute("""
                    SELECT f.ID_Friends, u.Pseudo 
                    FROM friends f 
                    JOIN users u ON f.Receiver_ID = u.ID_Users 
                    WHERE f.Sender_ID = %s AND f.Status = 'Pending'
                """, (self.user_id,))
                self.outgoing_requests = c.fetchall()

                # 3. Liste d'amis (Acceptés) - On récupère l'ID de la relation pour supprimer
                c.execute("""
                    SELECT f.ID_Friends, u.Pseudo 
                    FROM friends f 
                    JOIN users u ON (f.Sender_ID = u.ID_Users OR f.Receiver_ID = u.ID_Users)
                    WHERE (f.Sender_ID = %s OR f.Receiver_ID = %s) 
                    AND f.Status = 'Accepted' AND u.ID_Users != %s
                """, (self.user_id, self.user_id, self.user_id))
                self.friends = c.fetchall()
            except Exception as e:
                print(f"Erreur chargement amis : {e}")
            finally:
                c.close()
                db.close()

            # === NOUVEAU : On actualise les boutons après avoir chargé la BDD ===
            self._build_dynamic_buttons()

    def send_request(self):
        target_pseudo = self.pseudo_input.get_text()
        if not target_pseudo: return
        db = Connect()
        if db:
            try:
                # On ajoute buffered=True pour vider la mémoire de MySQL automatiquement
                c = db.cursor(buffered=True)
                # 1. On cherche l'ID de l'utilisateur cible
                c.execute("SELECT ID_Users FROM users WHERE Pseudo = %s", (target_pseudo,))
                target = c.fetchone()
                
                if target:
                    target_id = target[0]
                    if target_id == self.user_id:
                        print("Impossible de s'ajouter soi-même.")
                    else:
                        # 2. On vérifie si une relation (demande ou ami) existe déjà
                        c.execute("SELECT Status FROM friends WHERE (Sender_ID=%s AND Receiver_ID=%s) OR (Sender_ID=%s AND Receiver_ID=%s)", 
                                  (self.user_id, target_id, target_id, self.user_id))
                        
                        # FIX : On utilise fetchall() pour consommer tous les résultats et libérer le curseur
                        existing_relation = c.fetchall()
                        
                        if existing_relation:
                            print("Une relation existe déjà ou une demande est en cours.")
                        else:
                            # 3. On insère la nouvelle demande
                            c.execute("INSERT INTO friends (Sender_ID, Receiver_ID, Status) VALUES (%s, %s, 'Pending')", 
                                      (self.user_id, target_id))
                            db.commit()
                            print(f"Demande envoyée à {target_pseudo} !")
                            self.pseudo_input.text = ""
                else:
                    print("Utilisateur introuvable.")
                    
            except Exception as e:
                print(f"Erreur lors de l'envoi de la demande : {e}")
            finally:
                c.close()
                db.close()
                # On recharge les données pour mettre à jour la liste "Demandes envoyées"
                self.load_data()

    def respond_request(self, friend_request_id, status):
        db = Connect()
        if db:
            c = db.cursor()
            if status == 'Accepted':
                c.execute("UPDATE friends SET Status = 'Accepted' WHERE ID_Friends = %s", (friend_request_id,))
            else:
                c.execute("DELETE FROM friends WHERE ID_Friends = %s", (friend_request_id,))
            db.commit()
            c.close()
            db.close()
            self.load_data()

    def delete_relation(self, relation_id):
        """Utilisé pour annuler une demande envoyée ou supprimer un ami"""
        db = Connect()
        if db:
            c = db.cursor()
            c.execute("DELETE FROM friends WHERE ID_Friends = %s", (relation_id,))
            db.commit()
            c.close()
            db.close()
            self.load_data()

    def go_back(self):
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, self.user)

    def draw_text(self, text, font, color, pos, align='center'):
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if align == 'center': rect.center = pos
        elif align == 'left': rect.midleft = pos
        elif align == 'right': rect.midright = pos
        self.screen.blit(surf, rect)

    def _build_dynamic_buttons(self):
        # Boutons des demandes reçues
        self.inc_buttons = []
        for i, req in enumerate(self.incoming_requests):
            y = 150 + (i * 40)
            b_acc = Button("V", (self.screen_width - 150, y), lambda r=req[0]: self.respond_request(r, 'Accepted'), size=(40, 30))
            b_ref = Button("X", (self.screen_width - 100, y), lambda r=req[0]: self.respond_request(r, 'Rejected'), size=(40, 30))
            self.inc_buttons.append((b_acc, b_ref))

        # Boutons des demandes envoyées (Bouton Annuler décalé pour les pseudos longs !)
        self.out_buttons = []
        for i, req in enumerate(self.outgoing_requests):
            y = 350 + (i * 40)
            b_can = Button("Annuler", (self.screen_width // 4 + 180, y), lambda r=req[0]: self.delete_relation(r), size=(80, 25), font_size=20)
            self.out_buttons.append(b_can)

        # Boutons de suppression d'amis
        self.friend_del_buttons = []
        self.y_friends_start = 150 + (len(self.incoming_requests) * 40) + 60
        for i, f in enumerate(self.friends):
            y = self.y_friends_start + 40 + (i * 40)
            b_del = Button("X", (self.screen_width - 100, y), lambda r=f[0]: self.delete_relation(r), size=(40, 30), color=(200, 50, 50))
            self.friend_del_buttons.append(b_del)

    def run(self):
        while True:
            # =======================================================
            # NOUVEAU : VÉRIFICATION AUTOMATIQUE TOUTES LES 5 SECONDES
            # =======================================================
            import time
            current_time = time.time()
            if current_time - getattr(self, 'last_refresh_time', 0) > self.refresh_interval:
                self.load_data() # Recharge les amis et recrée les boutons !
                self.last_refresh_time = current_time
            # =======================================================
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None

                # === NOUVEAU : VALIDATION AVEC ENTRÉE ===
                if event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER):
                    # Attention, ici il n'y a pas de "return" car cela n'ouvre pas une nouvelle fenêtre !
                    self.send_request_button.action()
                # ========================================
                
                self.pseudo_input.handle_event(event)
                if self.send_request_button.handle_event(event): self.send_request_button.action()
                if self.back_button.handle_event(event): return self.back_button.action()
                
                # Écoute des petits boutons dynamiques
                for b1, b2 in list(self.inc_buttons):
                    if b1.handle_event(event): b1.action()
                    if b2.handle_event(event): b2.action()
                for b in list(self.out_buttons):
                    if b.handle_event(event): b.action()
                for b in list(self.friend_del_buttons):
                    if b.handle_event(event): b.action()

            self.screen.fill(self.CYBER_GREY)
            self.draw_text("GESTION DES AMIS", self.font_title, self.CYBER_BLUE, (self.screen_width // 2, 50))
            
            # =======================================================
            # NOUVEAU : LES TRAITS DE SÉPARATION (Lignes bleues)
            # =======================================================
            # 1. Trait vertical au centre pour séparer Gauche / Droite
            pygame.draw.line(self.screen, self.CYBER_BLUE, (self.screen_width // 2, 100), (self.screen_width // 2, self.screen_height - 100), 2)
            
            # 2. Trait horizontal à gauche pour séparer l'Ajout et les Demandes envoyées
            pygame.draw.line(self.screen, self.CYBER_BLUE, (50, 280), (self.screen_width // 2 - 50, 280), 2)
            # =======================================================

            # --- COLONNE GAUCHE ---
            self.draw_text("Ajouter un ami", self.font, self.CYBER_BLUE, (self.screen_width // 4, 110))
            self.pseudo_input.draw(self.screen)
            self.send_request_button.draw(self.screen)

            self.draw_text("Demandes envoyées", self.font, self.CYBER_BLUE, (self.screen_width // 4, 310))
            for i, req in enumerate(self.outgoing_requests):
                y = 350 + (i * 40)
                self.draw_text(req[1], self.font, self.LIGHT_GREY, (self.screen_width // 4 - 50, y), align='left')
                self.out_buttons[i].draw(self.screen)

            # --- COLONNE DROITE ---
            right_center_x = self.screen_width * 3 // 4
            self.draw_text("Demandes reçues", self.font, self.CYBER_BLUE, (right_center_x, 110))
            for i, req in enumerate(self.incoming_requests):
                y = 150 + (i * 40)
                self.draw_text(req[1], self.font, self.LIGHT_GREY, (right_center_x - 100, y), align='left')
                self.inc_buttons[i][0].draw(self.screen)
                self.inc_buttons[i][1].draw(self.screen)

            self.draw_text("Mes Amis", self.font, self.CYBER_BLUE, (right_center_x, getattr(self, 'y_friends_start', 300)))
            for i, f in enumerate(self.friends):
                y = getattr(self, 'y_friends_start', 300) + 40 + (i * 40)
                self.draw_text(f[1], self.font, self.LIGHT_GREY, (right_center_x - 100, y), align='left')
                self.friend_del_buttons[i].draw(self.screen)

            self.back_button.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(60)