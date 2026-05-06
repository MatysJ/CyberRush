import pygame
import json
import random
import io
import time
import math
import threading
from db import Connect
from ui.button import Button

class GameBoardPygame:
    def __init__(self, game_manager, user, network_client=None, game_data=None, opponent_pseudo="Adversaire", game_id=0):
        self.game_manager = game_manager
        self.user = user
        self.network_client = network_client
        
        if game_data is None:
            self.game_data = {'game_id': game_id, 'opponent_pseudo': opponent_pseudo}
        else:
            self.game_data = game_data

        self.user_id = self.user[0]
        self.game_id = self.game_data.get('game_id')
        self.opponent_pseudo = self.game_data.get('opponent_pseudo', 'Adversaire')

        if self.network_client:
            self.network_client.send_message({
                "action": "join_game",
                "game_id": self.game_id,
                "user_id": self.user_id
            })

        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption(f"Partie #{self.game_id} - {self.user[3]} vs {self.opponent_pseudo}")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.SIDEBAR_BG = (30, 30, 30)
        self.UI_BAR_BG = (20, 20, 20)
        self.GRID_COLOR = (100, 100, 100)
        self.SEPARATOR_COLOR = (255, 165, 0)
        self.ENEMY_COLOR = (255, 50, 50) 
        self.HP_BAR_RED = (200, 0, 0)
        self.HP_BAR_GREEN = (0, 200, 0)
        self.ELIXIR_PURPLE = (180, 0, 255)
        self.LASER_COLOR = (0, 255, 255)
        
        self.font = pygame.font.Font(None, 24)
        self.font_ui = pygame.font.Font(None, 36)
        self.font_big = pygame.font.Font(None, 60)
        
        self.SIDEBAR_WIDTH = 100 
        self.BOTTOM_BAR_HEIGHT = 100
        
        self.grid_rows = 5
        self.grid_cols = 10
        self.cell_size = 55
        
        available_width = self.screen_width - self.SIDEBAR_WIDTH
        grid_total_width = self.grid_cols * self.cell_size
        
        self.grid_margin_x = self.SIDEBAR_WIDTH + (available_width - grid_total_width) // 2
        self.grid_margin_y = 70

        self.opponent_grid_rect = pygame.Rect(self.grid_margin_x, self.grid_margin_y, grid_total_width, self.grid_rows * self.cell_size)
        self.player_grid_y_start = self.opponent_grid_rect.bottom + 20
        self.player_grid_rect = pygame.Rect(self.grid_margin_x, self.player_grid_y_start, grid_total_width, self.grid_rows * self.cell_size)

        self.player_hp = 5
        self.opponent_hp = 5 
        self.game_over = False
        self.winner = None 

        self.elixir = 50.0 
        self.max_elixir = 999
        self.elixir_regen_rate = 2.0 

        # =========================================================
        # NOUVELLE ÉCONOMIE : Gestion dynamique du coût
        self.unit_cost = 10                   # Le coût minimum (Soft Cap)
        self.cost_increment = 10               # Le malus cumulatif (+10, +20, +30...)
        self.last_cost_reduction = time.time() # Chronomètre pour la baisse par seconde
        # =========================================================

        self.last_elixir_update = time.time()

        self.last_damage_time = time.time()
        self.damage_interval = 1.0 
        self.tower_damage = 10
        self.visual_attacks = []
        self.player_barriers = [] # Pièges du Firewall

        self.player_deck = self._load_deck()
        self.available_deck = list(self.player_deck)
        self.player_units_on_board = {}   
        self.opponent_units_on_board = {} 
        self.enemy_types = self._load_enemy_types() 
        self.my_enemies = [] 
        self.opponent_enemies = []

        self._load_grids_from_db()

        self.player_path = []
        for r in range(self.grid_rows - 1, -1, -1): self.player_path.append((r, 0))
        for c in range(1, self.grid_cols): self.player_path.append((0, c))
        for r in range(1, self.grid_rows): self.player_path.append((r, self.grid_cols - 1))

        self.opponent_path = []
        for r in range(0, self.grid_rows): self.opponent_path.append((r, 0))
        for c in range(1, self.grid_cols): self.opponent_path.append((self.grid_rows - 1, c))
        for r in range(self.grid_rows - 1, -1, -1): self.opponent_path.append((r, self.grid_cols - 1))

        self.last_move_time = time.time()
        self.move_interval = 0.5 
        
        self.avatar_image = self._load_avatar()

        ui_center_x = self.SIDEBAR_WIDTH + (self.screen_width - self.SIDEBAR_WIDTH) // 2
        ui_center_y = self.screen_height - (self.BOTTOM_BAR_HEIGHT // 2)
        
        # On retire le "- 120" pour que le bouton utilise le centre exact de la zone de jeu
        self.add_unit_button = Button(f"Poser ({self.unit_cost})", (ui_center_x, ui_center_y), 
                                      self._place_random_unit, size=(200, 50))
        self.return_menu_button = Button("Retourner au menu", (self.screen_width//2, self.screen_height//2 + 80), self.quit_game, size=(250, 60))
        self.surrender_button = Button("Abandon", (self.screen_width - 100, 50), self.surrender, size=(120, 40), color=(200, 50, 50))

        # --- NOUVEAU : INITIALISATION DE LA LÉGENDE ---
        self._load_player_legend()
        # On place l'icône de la légende juste à gauche du bouton "Poser"
        self.legend_rect = pygame.Rect(ui_center_x - 170, ui_center_y - 25, 50, 50)
        # ----------------------------------------------

        self.dragging_unit = None    
        self.drag_origin = None       
        self.drag_offset = (0, 0)     

        self.surrender_button = Button("Abandon", (self.screen_width - 80, 30), self.surrender, size=(100, 40), color=(200, 50, 50))

        self.wave_number = 1           
        self.time_between_waves = 30.0  
        self.wave_timer = 10.0 

        # =========================================================
        # NOUVEAU : États de synchronisation des vagues
        self.wave_state = 'TIMER'      # Commence par le chrono de 10s
        self.opponent_wave_state = 0   # 0 = En cours, 1 = Terminé
        # =========================================================   
        # # =========================================================
        # NOUVEAU : Timer de sécurité
        self.safety_timer = 0.0
        # =========================================================    
        
        self.enemies_to_spawn = 0      
        self.spawn_interval = 1.5    
        self.last_spawn_time = 0     

        # NOUVEAU : Chronomètre pour rafraîchir la grille adverse
        self.last_opponent_sync = time.time()
        self.sync_interval = 0.5 # Vérifie toutes les demi-secondes 

        # NOUVEAU : Chronomètre pour synchroniser les Points de Vie
        self.last_hp_sync = time.time()
        self.hp_sync_interval = 1.0 # Toutes les 1 seconde (c'est largement suffisant !)

        # --- NOUVEAU : GESTION DE L'ABANDON ---
        self.confirm_surrender = False
        self.btn_confirm_yes = Button("Oui, j'abandonne", (self.screen_width // 2 - 110, self.screen_height // 2 + 50), 
                                      self._do_surrender, size=(200, 50), color=(200, 50, 50))
        self.btn_confirm_no = Button("Non, je reste", (self.screen_width // 2 + 110, self.screen_height // 2 + 50), 
                                     self._cancel_surrender, size=(200, 50), color=(50, 200, 50))

        # NOUVEAU : Mémoire de notre dernière sauvegarde réussie en BDD
        self.last_confirmed_db_grid = [[None for _ in range(8)] for _ in range(4)]
         
    def _init_player_grid(self):
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                # On vérifie si une grille existe déjà pour cette partie et cet utilisateur
                check_query = "SELECT ID_Grid FROM player_grids WHERE ID_Game = %s AND ID_Users = %s"
                cursor.execute(check_query, (self.id_game, self.user_id))
            
                if not cursor.fetchone():
                    # Structure par défaut : 4 lignes x 8 colonnes remplies de null
                    empty_grid = [[None for _ in range(8)] for _ in range(4)]
                    grid_json = json.dumps(empty_grid)
                
                    insert_query = """
                        INSERT INTO player_grids (ID_Game, ID_Users, Grid_State) 
                        VALUES (%s, %s, %s)
                    """
                    cursor.execute(insert_query, (self.id_game, self.user_id, grid_json))
                    db.commit()
                    print(f"Grille créée avec succès pour l'ID {self.user_id}")
            
                cursor.close()
            except Exception as e:
                print(f"Erreur lors de l'initialisation de la grille : {e}")
            finally:
                db.close()

    def _load_grids_from_db(self):
        db = Connect()
        self.opponent_id = None
        self.my_grid_state = [[None for _ in range(8)] for _ in range(4)]
        self.opponent_grid_state = [[None for _ in range(8)] for _ in range(4)]
        
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT Player1_ID, Player2_ID FROM game_sessions WHERE ID_Game = %s", (self.game_id,))
                session = cursor.fetchone()
                
                if session:
                    p1, p2 = session[0], session[1]
                    self.opponent_id = p2 if p1 == self.user_id else p1
            except Exception as e:
                print(f"Erreur chargement session : {e}")
            finally:
                # ---> LA GARANTIE ANTI-CRASH <---
                try: cursor.close()
                except: pass
                db.close()

    def _db_save_grid_thread(self, grid_json, grid_obj):
        """Tâche de fond qui écrit dans la BDD sans bloquer le jeu"""
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute(
                    "UPDATE player_grids SET Grid_State = %s WHERE ID_Game = %s AND ID_Users = %s",
                    (grid_json, self.game_id, self.user_id)
                )
                db.commit()
                
                # === LA CORRECTION EST ICI ===
                # On met à jour la mémoire du radar SEULEMENT quand la BDD a bien reçu l'information !
                self.last_confirmed_db_grid = grid_obj
                # =============================
                
            except Exception as e:
                print(f"Erreur sauvegarde grille : {e}")
            finally:
                try: cursor.close()
                except: pass
                db.close()

    def _save_grid_to_db(self):
        """Prépare la grille instantanément et lance le Thread"""
        grid_to_save = [[None for _ in range(8)] for _ in range(4)]
        
        for db_row in range(4):
            for db_col in range(8):
                py_row = db_row + 1
                py_col = db_col + 1
                
                unit = self.player_units_on_board.get((py_row, py_col))
                if unit:
                    grid_to_save[db_row][db_col] = {
                        "id": unit.get("id"),
                        "level": unit.get("level", 1),
                        "merge_count": unit.get("merge_count", 0) # Sécurité supplémentaire pour garder le niveau
                    }
        
        # On lance l'envoi à MySQL en secret, en lui passant aussi l'objet Python !
        grid_json = json.dumps(grid_to_save)
        threading.Thread(target=self._db_save_grid_thread, args=(grid_json, grid_to_save), daemon=True).start()

    def _get_unit_template(self, unit_id):
        if not hasattr(self, 'unit_templates_cache'):
            self.unit_templates_cache = {}
            
        if unit_id in self.unit_templates_cache:
            return dict(self.unit_templates_cache[unit_id])
            
        db = Connect()
        if db:
            try:
                cursor = db.cursor(dictionary=True)
                query = """SELECT ID_Unit, Name, Type, Attack, Attack_Speed, Price, 
                                  Attack_Growth, ATS_Growth, SpecialEffect, Image_Data 
                           FROM units WHERE ID_Unit = %s"""
                cursor.execute(query, (unit_id,))
                row = cursor.fetchone()
                
                if row:
                    unit_image = None
                    if row.get('Image_Data'):
                        try:
                            image_stream = io.BytesIO(row['Image_Data'])
                            loaded_img = pygame.image.load(image_stream).convert_alpha()
                            unit_image = pygame.transform.scale(loaded_img, (self.cell_size, self.cell_size))
                        except: pass
                            
                    template = {
                        'id': row['ID_Unit'], 'name': row['Name'], 'image': unit_image,
                        'type': row['Type'], 'base_attack': row['Attack'],
                        'base_attack_speed': row['Attack_Speed'], 'price': row['Price'],
                        'attack_growth': row['Attack_Growth'], 'ats_growth': row['ATS_Growth'],
                        'special_effect': row['SpecialEffect'], 'merge_count': 0, 'disabled': False
                    }
                    self.unit_templates_cache[unit_id] = template
                    return dict(template)
            except Exception as e:
                print(f"Erreur BDD fetch template: {e}")
            finally:
                # --- NOUVEAU : GARANTIE DE FERMETURE ---
                try: cursor.close()
                except: pass
                db.close()
        return None

    def _fetch_opponent_grid(self):
        opp_id = getattr(self, 'opponent_id', None)
        if not opp_id: return

        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute(
                    "SELECT Grid_State FROM player_grids WHERE ID_Game = %s AND ID_Users = %s", 
                    (self.game_id, opp_id)
                )
                row = cursor.fetchone()
                
                if row and row[0]:
                    opp_grid = json.loads(row[0])

                    # === LA CORRECTION EST ICI : LE NETTOYEUR ===
                    # On vide la mémoire des anciennes positions avant de redessiner !
                    self.opponent_units_on_board.clear()
                    # ============================================
                    
                    for r in range(4):
                        for c in range(8):
                            # ===================================================
                            # 1. LE MIROIR MATHÉMATIQUE (Inversion des axes)
                            # ===================================================
                            mirrored_r = 3 - r        # Inverse le Haut et le Bas
                            mirrored_c = 7 - c        # Inverse la Gauche et la Droite
                            py_col = mirrored_c + 1   # Le décalage de +1 pour votre grille
                            # ===================================================
                            
                            raw_data = opp_grid[r][c]
                            
                            if isinstance(raw_data, str):
                                try: raw_data = json.loads(raw_data) 
                                except: pass

                            if raw_data and isinstance(raw_data, dict):
                                unit_id = raw_data.get("id")
                                unit_level = raw_data.get("level", 1)

                                full_unit = self._get_unit_template(unit_id)
                                if full_unit:
                                    full_unit['level'] = unit_level
                                    full_unit['merge_count'] = raw_data.get('merge_count', 0) 
                                    self._update_unit_stats(full_unit) 
                                    
                                    # ===================================================
                                    # 2. LE MIROIR VISUEL (L'image à l'envers)
                                    # ===================================================
                                    if full_unit.get('image'):
                                        # flip(image, flip_x, flip_y) -> True, True fait un 180° !
                                        full_unit['image'] = pygame.transform.flip(full_unit['image'], True, True)
                                    # ===================================================
                                    
                                    # On place l'unité avec les NOUVELLES coordonnées miroir !
                                    self.opponent_units_on_board[(mirrored_r, py_col)] = full_unit

            except Exception as e:
                print(f"Erreur de synchronisation avec l'adversaire : {e}")
            finally:
                # --- NOUVEAU : GARANTIE DE FERMETURE ---
                try: cursor.close()
                except: pass
                db.close()

    def _check_my_grid_from_db(self):
        """Vérifie si une force extérieure (Karthus) a supprimé une de nos tours en BDD"""
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                # On lit NOTRE propre grille
                cursor.execute(
                    "SELECT Grid_State FROM player_grids WHERE ID_Game = %s AND ID_Users = %s", 
                    (self.game_id, self.user_id)
                )
                row = cursor.fetchone()
                
                if row and row[0]:
                    import json
                    my_db_grid = json.loads(row[0])
                    
                    # Sécurité si la mémoire n'est pas prête
                    if not hasattr(self, 'last_confirmed_db_grid'):
                        return
                        
                    towers_to_remove = []
                    
                    # On compare la BDD actuelle avec NOTRE DERNIÈRE SAUVEGARDE RÉUSSIE
                    for r in range(4):
                        for c in range(8):
                            # Si on SAIT qu'on avait réussi à sauvegarder une tour ici...
                            if self.last_confirmed_db_grid[r][c] is not None:
                                # ...Mais que la base de données dit soudainement qu'elle a disparu...
                                if my_db_grid[r][c] is None:
                                    towers_to_remove.append((r + 1, c + 1))
                                    # On met à jour notre mémoire pour ne pas déclencher ça en boucle
                                    self.last_confirmed_db_grid[r][c] = None
                                    
                    # On détruit visuellement les tours foudroyées !
                    for cell in towers_to_remove:
                        if cell in self.player_units_on_board:
                            del self.player_units_on_board[cell]
                            
            except Exception as e:
                print(f"Erreur vérification de notre grille : {e}")
            finally:
                try: cursor.close()
                except: pass
                db.close()

    def _get_grid_pos_from_mouse(self, mouse_pos, grid_rect):
        """Convertit la position de la souris en index (row, col) par rapport à une grille"""
        if not grid_rect.collidepoint(mouse_pos):
            return None
        
        rel_x = mouse_pos[0] - grid_rect.left
        rel_y = mouse_pos[1] - grid_rect.top
        
        col = int(rel_x // self.cell_size)
        row = int(rel_y // self.cell_size)
        
        if 0 <= row < self.grid_rows and 0 <= col < self.grid_cols:
            return (row, col)
        return None
    
    def _update_waves(self):
        if self.game_over: return
        current_time = time.time()
        state = getattr(self, 'wave_state', 'TIMER')
        
        if state == 'FIGHTING':
            if self.enemies_to_spawn > 0:
                if current_time - self.last_spawn_time > self.spawn_interval:
                    self._spawn_enemy_action()
                    self.enemies_to_spawn -= 1
                    self.last_spawn_time = current_time
            elif len(self.my_enemies) == 0:
                # ÉTAPE 1 : On a fini la vague actuelle (ex: 1)
                self.wave_state = 'WAITING'
                # ÉTAPE 2 : On s'annonce prêt pour la suivante (ex: 2)
                self.wave_number += 1
                threading.Thread(target=self._update_db_wave, args=(self.wave_number,), daemon=True).start()

        elif state == 'WAITING':
            # ÉTAPE 3 : On attend que l'adversaire s'annonce aussi prêt pour la même vague
            opp_wave = getattr(self, 'opponent_wave_db', 1)
            if opp_wave >= self.wave_number:
                self.wave_state = 'TIMER'
                self.wave_timer = 10.0 

        elif state == 'TIMER':
            self.wave_timer -= 1/60
            if self.wave_timer <= 0:
                self.wave_state = 'SAFETY'
                self.safety_timer = 5.0

        elif state == 'SAFETY':
            self.safety_timer -= 1/60
            if self.safety_timer <= 0:
                self.start_next_wave()

    def _update_db_wave(self, wave_val):
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                wave_col = "Player1_Wave" if self.is_player1 else "Player2_Wave"
                cursor.execute(f"UPDATE game_sessions SET {wave_col} = %s WHERE ID_Game = %s", (wave_val, self.game_id))
                db.commit()
                cursor.close()
            except Exception as e:
                print(f"Erreur update vague : {e}")
            finally:
                db.close()

    def start_next_wave(self):
        # On passe en combat immédiatement
        self.wave_state = 'FIGHTING'
        
        # Récompense (Basée sur la vague qu'on vient de terminer, donc wave_number - 1)
        self.elixir += ((self.wave_number - 1) * 1.0)
        self.elixir = min(self.elixir, self.max_elixir)

        # Calcul des spawn
        base_spawn_interval = 1.5 
        self.spawn_interval = max(0.1, base_spawn_interval * (0.95 ** (self.wave_number - 1)))

        # Fin de l'invulnérabilité de Kindred
        self.kindred_invulnerable = False

        # =========================================================
        # NOUVEAU : PASSIF DE GAREN (Soin de +1 PV)
        # =========================================================
        # Garen est la légende par défaut (ID 0)
        if getattr(self, 'legend_id', -1) == 0:
            if self.wave_number > 0 and self.wave_number % 25 == 0:
                self.player_hp += 1
                # Pas besoin de faire d'UPDATE SQL manuel ici ! 
                # Le thread _sync_hp_db va automatiquement détecter ce changement 
                # et l'envoyer dans game_sessions au prochain battement.

        # =========================================================
        # 1. PASSIF MORDEKAISER (Envoi de la malédiction à l'adversaire)
        # =========================================================
        if hasattr(self, 'legend_passive_name') and self.legend_passive_name == 'King_Realm':
            # S'active à partir de la vague 5, et tous les multiples de 5 (5, 10, 15...)
            if self.wave_number >= 5 and self.wave_number % 5 == 0:
                db = Connect()
                if db:
                    try:
                        cursor = db.cursor()
                        # On ajoute 3 ennemis de façon PERMANENTE (on cumule)
                        cursor.execute("""
                            UPDATE game_enemies 
                            SET Add_Enemies = COALESCE(Add_Enemies, 0) + 3 
                            WHERE ID_Game = %s AND ID_Player = %s
                        """, (self.game_id, self.opponent_id))
                        db.commit()
                    except Exception as e:
                        print(f"Erreur passif Mordekaiser : {e}")
                    finally:
                        try: cursor.close()
                        except: pass
                        db.close()

        # =========================================================
        # 2. LECTURE DES MALÉDICTIONS SUBIES (On ne nettoie plus la BDD !)
        # =========================================================
        penalty = 0
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT Add_Enemies FROM game_enemies WHERE ID_Game = %s AND ID_Player = %s", (self.game_id, self.user_id))
                row = cursor.fetchone()
                
                if row and row[0] is not None:
                    penalty = int(row[0])
                    # ATTENTION : On a SUPPRIMÉ le UPDATE qui remettait à NULL ici. La malédiction reste !
                    
            except Exception as e:
                print(f"Erreur vérification game_enemies : {e}")
            finally:
                try: cursor.close()
                except: pass
                db.close()

        # Le nombre total d'ennemis prend en compte la pénalité permanente
        total_enemies = self.wave_number + penalty

        # =========================================================
        # PASSIF D'AZIR (Shurima Shuffle)
        # =========================================================
        if hasattr(self, 'legend_passive_name') and self.legend_passive_name == 'Shurima_Shuffle':
            if self.available_deck:
                
                # ÉTAPE 1 : On détruit l'ancien soldat d'Azir pour libérer la place
                towers_to_remove = []
                for pos, unit in self.player_units_on_board.items():
                    if unit and unit.get('is_azir_soldier'):
                        towers_to_remove.append(pos)
                        
                for pos in towers_to_remove:
                    del self.player_units_on_board[pos]

                # === NOUVEAU : SÉCURITÉ ANTI-DUPLICATION (LE BUG DE LA MAIN) ===
                # Si le joueur a soulevé le soldat et est en train de le tenir avec sa souris !
                if getattr(self, 'dragging_unit', None) and self.dragging_unit.get('is_azir_soldier'):
                    self.dragging_unit = None  # On vide la main du joueur
                    self.drag_origin = None    # On oublie d'où elle venait
                # ===============================================================

                # ÉTAPE 2 : On cherche les cases vides (il y en a forcément au moins une maintenant !)
                valid_rows = range(1, self.grid_rows)     
                valid_cols = range(1, self.grid_cols - 1) 
                empty_cells = [(r, c) for r in valid_rows for c in valid_cols if (r, c) not in self.player_units_on_board]
                
                if empty_cells:
                    target_cell = random.choice(empty_cells)
                    unit_to_place = random.choice(self.available_deck).copy()
                    
                    # ÉTAPE 3 : Calcul du niveau
                    # Base : Niveau 2 (merge_count = 1)
                    # +1 Niveau toutes les 20 vagues (wave_number // 20)
                    # Maximum : Niveau 5 (merge_count = 4)
                    bonus_level = self.wave_number // 20
                    unit_to_place['merge_count'] = min(4, 1 + bonus_level)
                    
                    # Le marqueur crucial pour l'identifier
                    unit_to_place['is_azir_soldier'] = True 
                    
                    self._update_unit_stats(unit_to_place)
                    unit_to_place['last_attack_time'] = time.time()
                    
                    self.player_units_on_board[target_cell] = unit_to_place
                    self._save_grid_to_db()
        # =========================================================
        
        self.enemy_spawn_queue = [] 
        
        # Vérification des Boss (Modulos)
        if self.wave_number % 25 == 0 and self.enemy_types.get(3):
            boss = random.choice(self.enemy_types[3])
            self.enemy_spawn_queue.append(boss)
            total_enemies -= 1
            
        elif self.wave_number % 5 == 0 and self.enemy_types.get(2):
            boss = random.choice(self.enemy_types[2])
            self.enemy_spawn_queue.append(boss)
            total_enemies -= 1
            
        # Remplissage avec les "Minions" (Difficulté 1)
        if self.enemy_types.get(1):
            for _ in range(total_enemies):
                self.enemy_spawn_queue.append(random.choice(self.enemy_types[1]))
                
        self.enemies_to_spawn = len(self.enemy_spawn_queue)
        self.last_spawn_time = time.time()

        # Réduction du Cooldown de la légende
        if hasattr(self, 'legend_current_cd') and self.legend_current_cd > 0:
            self.legend_current_cd -= 1

    def _load_deck(self):
        deck_units = []
        db = Connect()
        if not db: return deck_units
        try:
            cursor = db.cursor(dictionary=True)
            # NOUVEAU : On récupère absolument toutes les stats importantes de la BDD !
            query = """
                SELECT u.ID_Unit, u.Name, u.Type, u.Attack, u.Attack_Speed, u.Price, 
                       u.Attack_Growth, u.ATS_Growth, u.SpecialEffect, u.Image_Data, 
                       COALESCE(pu.Level, 1) as Level
                FROM user_deck ud
                JOIN units u ON ud.ID_Unit = u.ID_Unit
                LEFT JOIN player_units pu ON u.ID_Unit = pu.ID_Unit AND pu.ID_Users = ud.ID_Users
                WHERE ud.ID_Users = %s AND ud.Deck_Slot > 0
                ORDER BY ud.Deck_Slot ASC
            """
            cursor.execute(query, (self.user_id,))
            
            for row in cursor.fetchall():
                unit_image = None
                if row.get('Image_Data'):
                    try:
                        image_stream = io.BytesIO(row['Image_Data'])
                        loaded_img = pygame.image.load(image_stream).convert_alpha()
                        unit_image = pygame.transform.scale(loaded_img, (self.cell_size, self.cell_size))
                    except: pass
                
                deck_units.append({
                    'id': row['ID_Unit'], 
                    'name': row['Name'], 
                    'image': unit_image,
                    'level': row['Level'],
                    'type': row['Type'],
                    'base_attack': row['Attack'],
                    'base_attack_speed': row['Attack_Speed'],
                    'price': row['Price'],
                    'attack_growth': row['Attack_Growth'],
                    'ats_growth': row['ATS_Growth'],
                    'special_effect': row['SpecialEffect'],
                    'disabled': False # Pour le passif de Jimbo !
                })
            cursor.close()
            db.close()
        except Exception as e:
            print(f"Erreur _load_deck : {e}")
        finally:
            # ---> LA GARANTIE ANTI-CRASH <---
            try: cursor.close()
            except: pass
            db.close()
            
        return deck_units # Le return doit se faire tout à la fin, APRÈS le finally !
            
        return deck_units

    def _load_enemy_types(self):
        # On prépare 3 listes pour les 3 difficultés
        types = {1: [], 2: [], 3: []}
        db = Connect()
        if not db: return types
        
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM enemies")
            
            for row in cursor.fetchall():
                enemy_image = None
                if row.get('Image_Data'):
                    try:
                        image_stream = io.BytesIO(row['Image_Data'])
                        loaded_img = pygame.image.load(image_stream).convert_alpha()
                        loaded_img.set_colorkey((255, 255, 255))
                        enemy_image = pygame.transform.scale(loaded_img, (self.cell_size, self.cell_size))
                    except: pass
                
                # Récupération des statistiques complètes depuis la BDD
                diff = row.get('Difficulty', 1)
                enemy_data = {
                    'id': row['ID_Enemy'],
                    'name': row['Name'],
                    'hp': row['Base_HP'],
                    'speed': row['Movement_Speed'],
                    'reward': row['Reward_Elixir'],
                    'passive': row.get('Passive', ''),
                    'image': enemy_image
                }
                
                # On le range dans la bonne difficulté
                if diff in types:
                    types[diff].append(enemy_data)
                else:
                    types[1].append(enemy_data)
            cursor.close()
        except Exception as e:
            print(f"Erreur chargement ennemis: {e}")
        finally:
            db.close()
            
        return types
    
    def _load_player_legend(self):
        self.legend_id = 0
        self.legend_image = None
        self.legend_max_cd = 0
        self.legend_current_cd = 0
        self.legend_active_name = None
        self.legend_passive_name = None
        
        db = Connect()
        if db:
            try:
                cursor = db.cursor(dictionary=True)
                # On récupère les infos de la légende équipée par ce joueur
                cursor.execute("""
                    SELECT l.* FROM legend l 
                    JOIN users u ON u.Legend = l.ID_Legend 
                    WHERE u.ID_Users = %s
                """, (self.user_id,))
                legend_data = cursor.fetchone()
                
                if legend_data and legend_data['ID_Legend'] > 0:
                    self.legend_id = legend_data['ID_Legend']
                    self.legend_max_cd = legend_data['cooldown']
                    self.legend_active_name = legend_data['actif']
                    self.legend_passive_name = legend_data['passive']
                    
                    if legend_data['Image_Data']:
                        import io
                        img_stream = io.BytesIO(legend_data['Image_Data'])
                        img = pygame.image.load(img_stream).convert_alpha()
                        # La taille parfaite pour aller à côté de votre bouton "Poser"
                        self.legend_image = pygame.transform.scale(img, (50, 50)) 
            except Exception as e:
                print(f"Erreur chargement légende en jeu : {e}")
            finally:
                cursor.close()
                db.close()

    def _update_elixir(self):
        if self.game_over: return
        
        # 1. Régénération de base (2 par seconde à 60 FPS comme prévu !)
        generation_rate = 2.0 / 60.0
        
        # 2. PASSIF : Le Mineur Crypto
        for (r, c), unit in list(self.player_units_on_board.items()):
            if unit and unit.get('name') == 'Mineur Crypto':
                # +0.5 d'élixir de base, et +0.5 par niveau de fusion
                bonus_par_seconde = 0.5 + (unit.get('merge_count', 0) * 0.5)
                generation_rate += (bonus_par_seconde / 60.0)
                
        self.elixir += generation_rate
        
        if self.elixir > self.max_elixir:
            self.elixir = self.max_elixir
        
        # =========================================================
        # NOUVEAU : RÉDUCTION DU PRIX AVEC LE TEMPS
        # =========================================================
        current_time = time.time()
        # Si une seconde s'est écoulée depuis la dernière baisse
        if current_time - getattr(self, 'last_cost_reduction', 0) >= 1.0:
            
            # On vérifie le Soft Cap (Le prix ne descend pas sous 30)
            if self.unit_cost > 30:
                self.unit_cost -= 1
                
                # On met à jour l'affichage du bouton en temps réel !
                if hasattr(self, 'add_unit_button'):
                    self.add_unit_button.text = f"Poser ({self.unit_cost})"
                    
            # On réinitialise le chrono pour la prochaine seconde
            self.last_cost_reduction = current_time

    def _spawn_enemy_action(self):
        if self.game_over: return
        enemy_data = self._create_enemy_data()
        
        # Sécurité : si la file est vide, on arrête là
        if not enemy_data: return 
        
        start_pos = self.player_path[0]
        enemy_data['row'] = start_pos[0]
        enemy_data['col'] = start_pos[1]
        
        enemy_data['path_index'] = 0 
        enemy_data['path_index_float'] = 0.0 # <--- TRÈS IMPORTANT : Variable pour le mouvement fluide

        self.my_enemies.append(enemy_data)

        if self.network_client:
            self.network_client.send_message({
                "action": "spawn_enemy",
                "game_id": self.game_id,
                "enemy_data": {
                    "row": enemy_data['row'],
                    "col": enemy_data['col'],
                    "name": enemy_data['name'],
                    "max_hp": enemy_data['max_hp'],
                    "current_hp": enemy_data['current_hp'],
                    "speed": enemy_data['speed'], # <--- TRÈS IMPORTANT : On envoie la vitesse !
                    "id": enemy_data['id']
                }
            })

    def _create_enemy_data(self):
        if not hasattr(self, 'enemy_spawn_queue') or not self.enemy_spawn_queue:
            return None
            
        base_enemy = self.enemy_spawn_queue.pop(0)
        passive = base_enemy.get('passive', '')
        
        # On copie le dictionnaire pour ne pas modifier le modèle de la base de données !
        enemy_dict = base_enemy.copy()
        
        # --- PASSIFS D'APPARITION (VOTRE LOGIQUE D'ORIGINE) ---
        if passive == 'Morpho' and self.enemy_types.get(1):
            # Choisir un ennemi niveau 1 (qui n'est pas un Morpho lui-même)
            choices = [e for e in self.enemy_types[1] if e.get('passive') != 'Morpho']
            if choices:
                target = random.choice(choices)
                enemy_dict['name'] = target['name']
                enemy_dict['image'] = target['image']
                enemy_dict['speed'] = target['speed']
                enemy_dict['hp'] = int(target['hp'] * 1.5) # +50% HP
                
        elif passive == 'MorphoA' and self.enemy_types.get(2):
            choices = [e for e in self.enemy_types[2] if e.get('passive') != 'MorphoA']
            if choices:
                target = random.choice(choices)
                enemy_dict['name'] = target['name']
                enemy_dict['image'] = target['image']
                enemy_dict['speed'] = target['speed']
                enemy_dict['hp'] = int(target['hp'] * 1.5)

        elif passive == 'JokerLaugh':
            active_cards = [u for u in self.player_deck if not u.get('disabled', False)]
            if active_cards:
                card_to_disable = random.choice(active_cards)
                card_to_disable['disabled'] = True 
                # On retire la carte de la pioche disponible !
                self.available_deck = [u for u in self.player_deck if not u.get('disabled', False)]
        # ======================================================

        kills = getattr(self, 'total_enemies_killed', 0)
        base_hp = enemy_dict.get('hp', 10) 
        
        # ====================================
        # NOUVEAU SCALING : ÉQUILIBRAGE PAR DIFFICULTÉ
        # ====================================
        enemy_id = enemy_dict.get('id')
        
        # CORRECTION : On pointe vers la colonne "Difficulty" de votre BDD
        # (Mettez 'Difficulty' avec une majuscule si votre dictionnaire respecte la casse SQL)
        enemy_difficulty = enemy_dict.get('difficulty', 1) 
        
        # 1. JIMBO (Le Boss - Scaling Flat)
        if enemy_id == 3: # Remplacez 3 par l'ID de Jimbo !
            # Scaling Boss : +1 HP max par ennemi tué dans toute la partie
            final_hp = base_hp + kills 
            
        # 2. ENNEMIS DIFFICULTÉ 2 (Scaling Lent)
        elif enemy_difficulty == 2:
            # Scaling Tank : +10% cumulatif par numéro de vague
            hp_multiplier = 1.10 ** (self.wave_number - 1)
            final_hp = int(base_hp * hp_multiplier)
            
        # 3. ENNEMIS DIFFICULTÉ 1 (Scaling Rapide)
        else:
            # Scaling Normal : +30% cumulatif par numéro de vague
            hp_multiplier = 1.10 ** (self.wave_number - 1)
            final_hp = int(base_hp * hp_multiplier)
        # ====================================

        return {
            'id': str(time.time()) + str(random.randint(0, 99999)), 
            'enemy_id': enemy_dict['id'],
            'name': enemy_dict['name'],
            'max_hp': final_hp,        # <-- On utilise les HP Scaled !
            'current_hp': final_hp,    # <-- On utilise les HP Scaled !
            'speed': enemy_dict['speed'],
            'reward': enemy_dict['reward'],
            'passive': passive, # On garde le passif en mémoire pour sa mort !
            'image': enemy_dict['image'],
            'row': 0.0, 
            'col': random.randint(1, self.grid_cols - 2)
        }

    def _handle_opponent_move_unit(self, data):
        # Au lieu de bricoler les coordonnées à la main,
        # on force le radar à s'actualiser INSTANTANÉMENT !
        self._fetch_opponent_grid()

    def _handle_opponent_spawn(self, data):
        e_data = data.get("enemy_data", {})
        
        img = None
        # NOUVEAU : On fouille dans le dictionnaire des 3 difficultés
        for diff_level, enemies_list in self.enemy_types.items():
            for t in enemies_list:
                if t['name'] == e_data.get('name'):
                    img = t['image']
                    break
            if img: break
        
        new_opp_enemy = {
            'row': e_data.get('row', 0),
            'col': e_data.get('col', 0),
            'path_index': 0, 
            'path_index_float': 0.0, # Variable pour un mouvement fluide
            'name': e_data.get('name', 'Ennemi'),
            'max_hp': e_data.get('max_hp', 100),
            'current_hp': e_data.get('current_hp', 100),
            'speed': e_data.get('speed', 1), # On applique la vitesse reçue !
            'image': img,
            'id': e_data.get('id', 0)
        }
        self.opponent_enemies.append(new_opp_enemy)

    def _load_avatar(self):
        db = Connect()
        if not db: 
            return None
        
        try:
            cursor = db.cursor()
            query = """
                SELECT a.Image_Data 
                FROM avatars a
                JOIN users u ON u.Avatar = a.ID_Avatar
                WHERE u.ID_Users = %s
            """
            cursor.execute(query, (self.user_id,))
            result = cursor.fetchone()
            cursor.close()
            db.close()
            
            if result and result[0]:
                image_stream = io.BytesIO(result[0])
                avatar_img = pygame.image.load(image_stream).convert_alpha()
                # On le redimensionne pour qu'il tienne bien dans la barre latérale du jeu
                return pygame.transform.scale(avatar_img, (60, 60))
        except Exception as e:
            print(f"Erreur lors du chargement de l'avatar en jeu : {e}")
            
        return None

    def _update_combat(self):
        if self.game_over: return
        current_time = time.time()

        # === NOUVEAU : NETTOYAGE DES PIÈGES ORPHELINS ===
        # 1. On récupère les IDs des barrières des Firewalls sur le plateau
        active_barrier_ids = [u.get('my_barrier_id') for u in self.player_units_on_board.values() 
                              if u and u.get('name') == 'Firewall' and u.get('my_barrier_id')]
        
        # 2. CORRECTION : On ajoute la barrière du Firewall qu'on est en train de soulever (drag & drop) !
        if hasattr(self, 'dragging_unit') and self.dragging_unit and self.dragging_unit.get('name') == 'Firewall':
            if self.dragging_unit.get('my_barrier_id'):
                active_barrier_ids.append(self.dragging_unit['my_barrier_id'])
                              
        # 3. On détruit instantanément toutes les barrières qui n'ont vraiment plus de maître
        self.player_barriers = [b for b in self.player_barriers if b['id'] in active_barrier_ids]
        # ===============================================
        
        # On passe en revue chaque tour présente sur votre plateau
        for (t_row, t_col), unit in list(self.player_units_on_board.items()):
            if unit is None: continue
            
            # On ignore les tours de soutien pour le moment (Onduleur, Serveur, Mineur...)
            # Elles ont 0 d'attaque, on gère leurs effets ailleurs ou via des passifs !
            if unit.get('current_attack', 0) <= 0:
                continue
                
            # Vérification du chronomètre individuel de cette tour
            if current_time - unit.get('last_attack_time', 0) >= unit.get('attack_cooldown', 1.0):
                
                # 1. Trouver et trier tous les ennemis par distance
                enemies_with_dist = []
                for enemy in self.my_enemies:
                    if enemy.get('current_hp', 0) > 0:
                        dist = math.sqrt((t_row - enemy['row'])**2 + (t_col - enemy['col'])**2)
                        enemies_with_dist.append((dist, enemy))
                
                if not enemies_with_dist:
                    continue # Personne à l'horizon, on ne tire pas !
                
                u_name = unit.get('name', '')
                
                # === GESTION DU CIBLAGE (PASSIFS) ===
                if u_name == 'Antivirus':
                    # Trie par PV actuel (du plus grand au plus petit)
                    enemies_with_dist.sort(key=lambda x: x[1].get('current_hp', 0), reverse=True)
                elif u_name == 'Tourelle SQL':
                    # Trie par PV actuel (du plus petit au plus grand) pour achever les faibles
                    enemies_with_dist.sort(key=lambda x: x[1].get('current_hp', 0))
                else:
                    # Trie par défaut : Distance la plus courte
                    enemies_with_dist.sort(key=lambda x: x[0]) 
                # ====================================
                
                # === GESTION DU BUFF SERVEUR ===
                # On vérifie les 8 cases autour de la tour qui va tirer
                server_bonus = 1.0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0: continue
                        voisin = self.player_units_on_board.get((t_row + dr, t_col + dc))
                        if voisin and voisin.get('name') == 'Serveur':
                            server_bonus += 0.30 # +30% de dégâts par serveur adjacent !

                base_damage = unit.get('current_attack', 10)
                damage = base_damage * server_bonus
                # ===============================
                
                attack_executed = False
                targets = []

                # CORRECTION : On définit bien le type de la tour ici avant la logique de ciblage !
                u_type = unit.get('type', 'Cible Unique')

                # === LOGIQUE DE CIBLAGE ET D'EFFETS ===
                if u_type == 'Cible Unique':
                    targets.append(enemies_with_dist[0][1])

                elif u_type == 'Cible Multiples':
                    for _, enemy in enemies_with_dist[:3]:
                        targets.append(enemy)

                elif u_type == 'AOE' or u_name == 'Générateur de Zone de Quarantaine':
                    # PASSIF : La Zone de Quarantaine (Frappe TOUT le monde dans un rayon de 1.5)
                    splash_radius = 1.5 
                    
                    # Effet visuel des cases rouges pour la Quarantaine
                    if u_name == 'Générateur de Zone de Quarantaine':
                        for dr in [-1, 0, 1]:
                            for dc in [-1, 0, 1]:
                                z_rect = self._get_cell_rect(self.player_grid_rect, t_row + dr, t_col + dc)
                                # On crée un faux tir visuel carré rouge au sol
                                self.visual_attacks.append({
                                    'is_square': True, 
                                    'rect': z_rect, 
                                    'time': current_time
                                })
                        
                        # Inflige des dégâts à TOUS les ennemis dans la zone
                        for dist_from_tower, enemy in enemies_with_dist:
                            if dist_from_tower <= splash_radius:
                                enemy['current_hp'] -= damage
                        attack_executed = True
                        
                    else:
                        # AOE Classique (Cible principale + Splash autour)
                        primary_target = enemies_with_dist[0][1]
                        targets.append(primary_target)
                        for dist_from_tower, enemy in enemies_with_dist[1:]:
                            dist_from_target = math.sqrt((primary_target['row'] - enemy['row'])**2 + (primary_target['col'] - enemy['col'])**2)
                            if dist_from_target <= splash_radius:
                                enemy['current_hp'] -= damage 
                                
                elif u_name == 'Firewall':
                    # PASSIF : Pose une SEULE barrière permanente sur une case libre du chemin
                    if not unit.get('barrier_placed'):
                        # On liste les positions qui ont DÉJÀ une barrière
                        occupied_pos = [(b['row'], b['col']) for b in self.player_barriers]
                        
                        # On filtre le chemin pour ne garder que les cases vides
                        available_path = [p for p in self.player_path if p not in occupied_pos]
                        
                        if available_path:
                            trap_pos = random.choice(available_path)
                            trap_id = random.randint(1, 9999999) # CORRECTION : On crée l'ID ici
                            
                            self.player_barriers.append({
                                'id': trap_id, # On donne l'ID à la barrière
                                'row': trap_pos[0],
                                'col': trap_pos[1],
                                'damage': damage 
                            })
                            unit['barrier_placed'] = True 
                            
                            # CORRECTION VITALE : La tour garde le ticket de sa barrière !
                            unit['my_barrier_id'] = trap_id 
                            
                            attack_executed = True
                
                # === APPLICATION DES DÉGÂTS ET LASERS ===
                for target in targets:
                    target['current_hp'] -= damage
                    
                    # Création du laser visuel pour chaque cible
                    start_rect = self._get_cell_rect(self.player_grid_rect, t_row, t_col)
                    end_rect = self._get_cell_rect(self.player_grid_rect, target['row'], target['col'])
                    
                    self.visual_attacks.append({
                        'start': (start_rect.centerx, start_rect.centery),
                        'end': (end_rect.centerx, end_rect.centery),
                        'time': current_time
                    })
                    attack_executed = True
                
                # On remet le chrono de CETTE tour à zéro !
                if attack_executed:
                    unit['last_attack_time'] = current_time

        # Nettoyage des tirs visuels après 0.1s d'affichage
        self.visual_attacks = [v for v in self.visual_attacks if current_time - v['time'] < 0.1]


    def _update_enemies(self):
        if self.game_over: return
        
        # On initialise le compteur de kills s'il n'existe pas encore
        if not hasattr(self, 'total_enemies_killed'):
            self.total_enemies_killed = 0
            
        current_time = time.time() 
        enemies_to_remove = []
        new_spawns = [] # On stocke les apparitions ici pour ne pas faire planter la boucle
        
        # --- ENNEMIS DU JOUEUR ---
        for enemy in self.my_enemies:
            
            # --- Vérification de la mort et déclenchement des Passifs ---
            if enemy.get('current_hp', 1) <= 0:
                self.elixir += enemy.get('reward', 1) 
                
                # On incrémente le compteur d'ennemis tués !
                self.total_enemies_killed += 1 
                
                # On sécurise la lecture (retire les espaces accidentels de la BDD)
                passive = enemy.get('passive', '').strip()
                
                if passive == 'Explosion':
                    towers = [pos for pos, unit in self.player_units_on_board.items() if unit is not None]
                    if towers:
                        target_cell = random.choice(towers)
                        del self.player_units_on_board[target_cell] 
                        
                elif passive == 'Spawn':
                    virus_template = None
                    if self.enemy_types.get(1):
                        for e in self.enemy_types[1]:
                            if 'Virus' in e['name']: 
                                virus_template = e
                                break
                        if not virus_template: 
                            virus_template = self.enemy_types[1][0] 
                            
                    if virus_template:
                        # Le Virus qui spawn profite aussi du scaling des vagues !
                        hp_multiplier = 1.0 + (self.wave_number * 0.03)
                        final_hp = int(virus_template['hp'] * hp_multiplier)

                        # On fait spawner UN SEUL virus pour l'équilibrage
                        new_virus = {
                            'id': str(time.time()) + str(random.randint(0, 99999)),
                            'enemy_id': virus_template['id'],
                            'name': virus_template['name'],
                            'max_hp': final_hp,
                            'current_hp': final_hp,
                            'speed': virus_template['speed'],
                            'reward': 0, 
                            'passive': '', 
                            'image': virus_template['image'],
                            'row': enemy['row'], 
                            'col': enemy['col'],
                            'path_index': enemy['path_index'],
                            'path_index_float': enemy['path_index_float']
                        }
                        new_spawns.append(new_virus)

                        # On prévient l'adversaire en multijoueur !
                        if self.network_client:
                            self.network_client.send_message({
                                "action": "spawn_enemy",
                                "game_id": self.game_id,
                                "enemy_data": {
                                    "row": new_virus['row'],
                                    "col": new_virus['col'],
                                    "name": new_virus['name'],
                                    "max_hp": new_virus['max_hp'],
                                    "current_hp": new_virus['current_hp'],
                                    "speed": new_virus['speed'],
                                    "id": new_virus['id']
                                }
                            })

                enemies_to_remove.append(enemy)
                continue # On passe à l'ennemi suivant
                
            # --- GESTION DE LA VITESSE ET DU FIREWALL ---
            base_speed = enemy.get('speed', 1) 
            current_speed = base_speed
            
            # Est-ce que l'ennemi est sous l'effet d'un ralentissement ?
            if current_time < enemy.get('slow_until', 0):
                current_speed = base_speed * 0.75 # Réduction de 25% de la vitesse !
                
            # Avancée par image (avec la vitesse modifiée)
            enemy['path_index_float'] += current_speed / 60.0
            idx = int(enemy['path_index_float'])
            
            # NOUVEAU : On crée une mémoire pour l'ennemi s'il n'en a pas
            if 'hit_barriers' not in enemy:
                enemy['hit_barriers'] = []
            
            # Vérification : L'ennemi marche-t-il sur une barrière du Firewall ?
            for b in self.player_barriers:
                # S'il n'a PAS encore été touché par CETTE barrière spécifique
                if b['id'] not in enemy['hit_barriers']:
                    # S'il est à moins de 0.5 case de la barrière
                    if math.sqrt((enemy['row'] - b['row'])**2 + (enemy['col'] - b['col'])**2) < 0.5:
                        enemy['slow_until'] = current_time + 1.0 # Ralenti pendant 1 seconde
                        enemy['current_hp'] -= b.get('damage', 10) # Subit les dégâts du piège
                        enemy['hit_barriers'].append(b['id']) # Mémorise la barrière !
            
            if idx >= len(self.player_path) - 1:
                # NOUVEAU : Invulnérabilité de Kindred
                if getattr(self, 'kindred_invulnerable', False):
                    print("Kindred")
                else:
                    self.player_hp -= 1
                    
                    # NOUVEAU : Passif de Survie de Karthus
                    if self.player_hp <= 0 and self.legend_passive_name == 'Imminent_Death' and not getattr(self, 'karthus_used_passive', False):
                        self.player_hp = 1
                        self.karthus_used_passive = True
                        
                enemies_to_remove.append(enemy)
                # === LA CORRECTION EST ICI ===
                if self.player_hp <= 0:
                    # On force le radar à envoyer notre mort IMMÉDIATEMENT !
                    # C'est la méthode _sync_hp_db qui se chargera d'appeler end_game 
                    # une fois que la base de données aura bien reçu le 0.
                    self._sync_hp_db()
                # =============================
            else:
                enemy['path_index'] = idx
                fraction = enemy['path_index_float'] - idx
                curr_pos = self.player_path[idx]
                next_pos = self.player_path[idx + 1]
                enemy['row'] = curr_pos[0] + (next_pos[0] - curr_pos[0]) * fraction
                enemy['col'] = curr_pos[1] + (next_pos[1] - curr_pos[1]) * fraction
            # ---------------------------------------------

        # On nettoie les morts
        for e in enemies_to_remove:
            if e in self.my_enemies:
                self.my_enemies.remove(e)
                
        # On ajoute les nouveaux virus sur le plateau une fois la boucle terminée
        self.my_enemies.extend(new_spawns)

        # --- ENNEMIS DE L'ADVERSAIRE ---
        opp_enemies_to_remove = []
        for enemy in self.opponent_enemies:
            if enemy.get('current_hp', 1) <= 0:
                opp_enemies_to_remove.append(enemy)
                continue
                
            speed = enemy.get('speed', 1)
            enemy['path_index_float'] += speed / 60.0
            idx = int(enemy['path_index_float'])
            
            if idx >= len(self.opponent_path) - 1:
                opp_enemies_to_remove.append(enemy)
            else:
                enemy['path_index'] = idx
                fraction = enemy['path_index_float'] - idx
                curr_pos = self.opponent_path[idx]
                next_pos = self.opponent_path[idx + 1]
                enemy['row'] = curr_pos[0] + (next_pos[0] - curr_pos[0]) * fraction
                enemy['col'] = curr_pos[1] + (next_pos[1] - curr_pos[1]) * fraction
        
        for e in opp_enemies_to_remove:
            if e in self.opponent_enemies:
                self.opponent_enemies.remove(e)

    def _place_random_unit(self):
        if self.game_over: return
        if self.elixir < self.unit_cost: return
        if not self.available_deck: return
        
        valid_rows = range(1, self.grid_rows)     
        valid_cols = range(1, self.grid_cols - 1) 

        empty_cells = []
        for r in valid_rows:
            for c in valid_cols:
                if (r, c) not in self.player_units_on_board:
                    empty_cells.append((r, c))

        if not empty_cells: return

        target_cell = random.choice(empty_cells)
        unit_to_place = random.choice(self.available_deck).copy()
        
        unit_to_place['merge_count'] = 0 
        
        # NOUVEAU : On calcule ses stats et on lui donne son chrono !
        self._update_unit_stats(unit_to_place)
        unit_to_place['last_attack_time'] = time.time() # Chrono individuel

        # On paye la tour
        self.elixir -= self.unit_cost
        
        # --- LOGIQUE D'AUGMENTATION FIXE ---
        self.unit_cost += 10  # On ajoute toujours +10, tout simplement !
        # -----------------------------------

        # === MISE À JOUR VISUELLE DU BOUTON ===
        if hasattr(self, 'add_unit_button'):
            self.add_unit_button.text = f"Poser ({self.unit_cost})"
        
        self.player_units_on_board[target_cell] = unit_to_place
        
        if self.network_client:
            self.network_client.send_message({
                "action": "place_unit",
                "game_id": self.game_id,
                "unit_id": unit_to_place['id'],
                "unit_name": unit_to_place['name'],
                "row": target_cell[0],
                "col": target_cell[1]
            })

        # ===================================================
        # AJOUTEZ LA SAUVEGARDE ICI :
        self._save_grid_to_db()
        # ===================================================

    def _update_unit_stats(self, unit):
        """Calcule les stats finales de la tour en fonction de son Level et de ses Fusions"""
        level_bonus = unit.get('level', 1) - 1
        merge_count = unit.get('merge_count', 0)
        
        # 1. Stats de base améliorées par le niveau de la carte (hors partie)
        base_atk = unit.get('base_attack', 0) + (level_bonus * unit.get('attack_growth', 0))
        base_ats = unit.get('base_attack_speed', 0.1) + (level_bonus * unit.get('ats_growth', 0.0))
        
        # 2. Bonus de Fusion en cours de partie (ex: +50% de dégâts et +20% de vitesse par étoile)
        unit['current_attack'] = base_atk * (1 + (merge_count * 0.50))
        # NOUVEAU : Passif de Briar (Blood Lusted)
        if hasattr(self, 'legend_passive_name') and self.legend_passive_name == 'Blood_Lusted':
            hp_missing = 5 - self.player_hp
            if hp_missing > 0:
                bonus = hp_missing * 0.12 # +12% par PV manquant
                unit['current_attack'] *= (1 + bonus)
        unit['current_attack_speed'] = base_ats * (1 + (merge_count * 0.20))
        
        # 3. Calcul du Chronomètre individuel (Cooldown) : 1 / Vitesse
        # Ex: Si ATS = 2.0, la tour tire toutes les 0.5 secondes. (max(0.1) évite de diviser par zéro)
        final_ats = max(0.1, unit['current_attack_speed'])
        unit['attack_cooldown'] = 1.0 / final_ats

    def quit_game(self):
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, self.user)

    def _draw_entity_on_grid(self, grid_rect, row, col, unit_data, color_fallback=(255,0,0)):
        cell_rect = pygame.Rect(grid_rect.left + col*self.cell_size, grid_rect.top + row*self.cell_size, self.cell_size, self.cell_size)
        
        image = None
        
        if isinstance(unit_data, dict):
            image = unit_data.get('image')
            
            # 1. On dessine l'image de la tour
            if image:
                img_rect = image.get_rect(center=cell_rect.center)
                self.screen.blit(image, img_rect)
            else:
                pygame.draw.circle(self.screen, color_fallback, cell_rect.center, self.cell_size // 3)

            # =========================================================
            # NOUVEAU : AFFICHAGE DU NIVEAU DE FUSION ET DE LA CARTE
            # =========================================================
            # fusion_level = le rang sur le plateau (les fusions)
            fusion_level = unit_data.get('merge_count', 0) + 1 
            # card_level = le vrai niveau d'amélioration de la boutique
            card_level = unit_data.get('level', 1)
            
            font_lvl = pygame.font.Font(None, 20) 
            
            # Affichage clair => T (Tier de fusion) et N (Niveau de la carte)
            # Exemple : T2 (N.5) pour une tour fusionnée une fois et niveau 5.
            # Si vous préférez n'afficher QUE le niveau de la carte, mettez : f"Lv.{card_level}"
            lvl_text = font_lvl.render(f"T{fusion_level} (N.{card_level})", True, (255, 255, 255))
            
            text_rect = lvl_text.get_rect(bottomright=(cell_rect.right - 4, cell_rect.bottom - 4))
            
            bg_surface = pygame.Surface((text_rect.width + 6, text_rect.height + 4), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 150))
            
            self.screen.blit(bg_surface, (text_rect.x - 3, text_rect.y - 2))
            self.screen.blit(lvl_text, text_rect)
            # =========================================================

            return cell_rect

        # =========================================================
        # (Cas exceptionnel où unit_data serait juste une image)
        # =========================================================
        else:
            image = unit_data

        if image:
            img_rect = image.get_rect(center=cell_rect.center)
            self.screen.blit(image, img_rect)
        else:
            pygame.draw.circle(self.screen, color_fallback, cell_rect.center, self.cell_size // 3)
            
        return cell_rect

    def _draw_hp_bar(self, rect, current, max_val):
        if max_val <= 0: return
        pct = current / max_val
        bar_w, bar_h = self.cell_size - 10, 4
        x, y = rect.left + 5, rect.top + 5
        pygame.draw.rect(self.screen, self.HP_BAR_RED, (x, y, bar_w, bar_h))
        pygame.draw.rect(self.screen, self.HP_BAR_GREEN, (x, y, bar_w * pct, bar_h))

    def _draw_sidebar(self):
        pygame.draw.rect(self.screen, self.SIDEBAR_BG, (0, 0, self.SIDEBAR_WIDTH, self.screen_height))
        y = 60
        for u in self.player_deck:
            if u.get('image'): 
                # On prépare l'image à la bonne taille
                img = pygame.transform.scale(u['image'], (50, 50))
                img_x = (self.SIDEBAR_WIDTH - 50) // 2
                
                # NOUVEAU : Si la carte est désactivée par Jimbo
                if u.get('disabled', False):
                    img = img.copy() # On copie pour ne pas détruire l'image d'origine
                    # Assombrit fortement l'image
                    img.fill((100, 100, 100), special_flags=pygame.BLEND_RGBA_MULT)
                    self.screen.blit(img, (img_x, y))
                    
                    # Dessine une grosse croix rouge par dessus
                    pygame.draw.line(self.screen, (255, 0, 0), (img_x, y), (img_x + 50, y + 50), 3)
                    pygame.draw.line(self.screen, (255, 0, 0), (img_x + 50, y), (img_x, y + 50), 3)
                else:
                    self.screen.blit(img, (img_x, y))
                    
            y += 65
            
        if hasattr(self, 'avatar_image') and self.avatar_image: 
            self.screen.blit(self.avatar_image, ((self.SIDEBAR_WIDTH - 60) // 2, self.screen_height - 100))

    def _draw_grid_lines(self, rect, is_opponent=False):
        start_row = 0
        end_row = self.grid_rows
        
        if is_opponent:
            draw_rows = range(0, 4) 
        else:
            draw_rows = range(1, 5) 

        for r in range(self.grid_rows + 1):
            should_draw = False
            if is_opponent:
                if r <= 4: should_draw = True 
            else:
                if r >= 1: should_draw = True 
            
            if should_draw:
                y = rect.top + r * self.cell_size
                start_x = rect.left + 1 * self.cell_size
                end_x = rect.left + (self.grid_cols - 1) * self.cell_size
                pygame.draw.line(self.screen, self.GRID_COLOR, (start_x, y), (end_x, y))
            
        for c in range(1, self.grid_cols): 
            x = rect.left + c * self.cell_size
            if is_opponent:
                start_y = rect.top
                end_y = rect.top + 4 * self.cell_size
            else:
                start_y = rect.top + 1 * self.cell_size
                end_y = rect.bottom
            pygame.draw.line(self.screen, self.GRID_COLOR, (x, start_y), (x, end_y))

    def _get_cell_rect(self, grid_rect, row, col):
        return pygame.Rect(grid_rect.left + col*self.cell_size, grid_rect.top + row*self.cell_size, self.cell_size, self.cell_size)

    def _sync_hp_db(self):
        if getattr(self, 'game_over', False): return
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                if not hasattr(self, 'is_player1'):
                    cursor.execute("SELECT Player1_ID FROM game_sessions WHERE ID_Game = %s", (self.game_id,))
                    session = cursor.fetchone()
                    if session: self.is_player1 = (self.user_id == session[0])
                    else: return

                my_hp_col = "Player1_HP" if self.is_player1 else "Player2_HP"
                opp_hp_col = "Player2_HP" if self.is_player1 else "Player1_HP"
                opp_wave_col = "Player2_Wave" if self.is_player1 else "Player1_Wave"
                opp_ready_col = "Player2_Ready" if self.is_player1 else "Player1_Ready"

                # Mise à jour de nos PV
                cursor.execute(f"UPDATE game_sessions SET {my_hp_col} = %s WHERE ID_Game = %s", (self.player_hp, self.game_id))
                db.commit()

                # Lecture des données adverses (PV + Vague + Sort + Légendes)
                cursor.execute(f"SELECT {opp_hp_col}, {opp_wave_col}, {opp_ready_col}, Player1_Legend, Player2_Legend FROM game_sessions WHERE ID_Game = %s", (self.game_id,))
                row = cursor.fetchone()

                if row:
                    if row[0] is not None: self.opponent_hp = row[0]
                    if row[1] is not None: self.opponent_wave_db = row[1]
                    
                    # === L'ADVERSAIRE A LANCÉ UNE COMPÉTENCE ! ===
                    opp_ready_state = row[2]
                    if opp_ready_state == 1:
                        # row[3] = Player1_Legend, row[4] = Player2_Legend
                        opp_legend_id = row[4] if self.is_player1 else row[3]
                                
                        # ID 4 = Mordekaiser
                        if opp_legend_id == 4: 
                            self.mordekaiser_penalty = getattr(self, 'mordekaiser_penalty', 0) + 5
                        
                        # On remet le Ready de l'adversaire à 0 pour dire qu'on a bien reçu l'attaque
                        cursor.execute(f"UPDATE game_sessions SET {opp_ready_col} = 0 WHERE ID_Game = %s", (self.game_id,))
                        db.commit()
                    # =============================================

                    ## 5. LE JUGEMENT FINAL (Victoire ou Défaite)
                    if self.player_hp <= 0:
                        cursor.execute("UPDATE game_sessions SET Status = 'Finished', Winner_ID = %s WHERE ID_Game = %s", (self.opponent_id, self.game_id))
                        db.commit()
                        self.end_game("Opponent") 

                    elif self.opponent_hp <= 0:
                        cursor.execute("UPDATE game_sessions SET Status = 'Finished', Winner_ID = %s WHERE ID_Game = %s", (self.user_id, self.game_id))
                        db.commit()
                        self.end_game("Player")

            except Exception as e:
                print(f"Erreur de synchronisation HP : {e}")
            finally:
                try: cursor.close()
                except: pass
                db.close()

    def _background_sync(self):
        """Cette fonction tourne en tâche de fond pour ne pas geler l'écran !"""
        self._fetch_opponent_grid()
        self._sync_hp_db()
        # NOUVEAU : La petite ligne manquante pour allumer le radar !
        self._check_my_grid_from_db()

    def surrender(self):
        # Au lieu de quitter, on affiche la demande de confirmation
        self.confirm_surrender = True

    def _do_surrender(self):
        """Action déclenchée si le joueur clique sur OUI"""
        self.player_hp = 0
        # On ferme la confirmation
        self.confirm_surrender = False
        # On force une synchronisation immédiate pour mettre la BDD à 0
        # Cela déclenchera end_game("Opponent") dans la foulée
        self._sync_hp_db()

    def _cancel_surrender(self):
        """Action déclenchée si le joueur clique sur NON"""
        self.confirm_surrender = False
    
    def end_game(self, winner):
        if self.game_over: 
            return 
            
        self.game_over = True
        self.winner = winner

        is_winner = (self.winner == "Player") 
        
        self.gained_gold = 100 if is_winner else 30
        self.gained_xp = 35 if is_winner else 10

        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                query = """
                    UPDATE users 
                    SET Gold = Gold + %s, Experience = Experience + %s 
                    WHERE ID_Users = %s
                """
                cursor.execute(query, (self.gained_gold, self.gained_xp, self.user_id))
                db.commit()
                cursor.close()
            except Exception as e:
                print(f"Erreur attribution récompense : {e}")
            finally:
                db.close()

    def _draw_game_over(self):
        s = pygame.Surface((self.screen_width, self.screen_height))
        s.set_alpha(200)
        s.fill((0,0,0))
        self.screen.blit(s, (0,0))
        
        is_winner = (self.winner == "Player")
        msg = "VICTOIRE !" if is_winner else "DÉFAITE..."
        color = (0, 255, 0) if is_winner else (255, 0, 0)
        
        txt_surf = self.font_big.render(msg, True, color)
        txt_rect = txt_surf.get_rect(center=(self.screen_width//2, self.screen_height//2 - 120))
        self.screen.blit(txt_surf, txt_rect)
        
        gold = getattr(self, 'gained_gold', 0)
        xp = getattr(self, 'gained_xp', 0)
        
        gold_text = f"Or gagné : +{gold}"
        xp_text = f"Expérience : +{xp}"
        
        gold_surf = self.font.render(gold_text, True, (255, 215, 0)) 
        xp_surf = self.font.render(xp_text, True, (0, 150, 255)) 
        
        self.screen.blit(gold_surf, gold_surf.get_rect(center=(self.screen_width//2, self.screen_height//2 - 40)))
        self.screen.blit(xp_surf, xp_surf.get_rect(center=(self.screen_width//2, self.screen_height//2 + 10)))

        self.return_menu_button.draw(self.screen)

    def run(self):
        # On regroupe les deux chronomètres en un seul
        self.last_sync_time = time.time()
        
        while True:
            current_time = time.time()
            
            # =========================================================
            # NOUVEAU : Synchronisation en TÂCHE DE FOND (Zéro Lag !)
            if current_time - getattr(self, 'last_sync_time', 0) > 0.5:
                # On lance nos radars via un assistant externe
                threading.Thread(target=self._background_sync, daemon=True).start()
                self.last_sync_time = current_time
            # =========================================================
            
            # (Le reste de votre code ne change pas)
            self._update_elixir()
            self._update_enemies()
            self._update_combat()
            self._update_waves()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return self.quit_game()

                if event.type == pygame.USEREVENT and hasattr(event, 'action'):
                    if event.action == "opponent_place_unit":
                        self._handle_opponent_move_unit(event.data)
                    elif event.action == "opponent_spawn_enemy":
                        self._handle_opponent_spawn(event.data)

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: 
                        mouse_pos = event.pos

                        # Clic sur l'icône de la Légende
                        if hasattr(self, 'legend_rect') and self.legend_rect.collidepoint(event.pos):
                            if self.legend_id > 0 and self.legend_current_cd == 0 and self.legend_active_name and self.legend_active_name != 'None':
                                # 1. ORNN - UPGRADE (Effet Local Immédiat)
                                if self.legend_active_name == 'Upgrade':
                                    towers = list(self.player_units_on_board.keys())
                                    if towers:
                                        target = random.choice(towers)
                                        unit = self.player_units_on_board[target]
                                        if unit.get('merge_count', 0) < 5:
                                            unit['merge_count'] += 1
                                            self._update_unit_stats(unit)
                                            self._save_grid_to_db()
                                            self.legend_current_cd = self.legend_max_cd # On lance le CD
                                            
                                # 2. KINDRED - PEACE EMBRACE (Effet Local Immédiat)
                                elif self.legend_active_name == 'Peace_Embrace':
                                    self.kindred_invulnerable = True
                                    self.legend_current_cd = self.legend_max_cd # On lance le CD
                                    
                                # 3. KARTHUS - MORTAL REQUIEM (Effet Direct BDD)
                                elif self.legend_active_name == 'Mortal_Requiem':
                                    db = Connect()
                                    if db:
                                        try:
                                            cursor = db.cursor()
                                            
                                            # 1. On récupère la grille de l'adversaire
                                            cursor.execute(
                                                "SELECT Grid_State FROM player_grids WHERE ID_Game = %s AND ID_Users = %s", 
                                                (self.game_id, self.opponent_id)
                                            )
                                            row = cursor.fetchone()
                                            
                                            if row and row[0]:
                                                import json
                                                opp_grid = json.loads(row[0])
                                                
                                                # 2. On cherche toutes les coordonnées des tours existantes
                                                towers_coords = []
                                                for r in range(4):
                                                    for c in range(8):
                                                        if opp_grid[r][c] is not None:
                                                            towers_coords.append((r, c))
                                                            
                                                # 3. S'il a des tours, on en détruit une au hasard
                                                if towers_coords:
                                                    target_r, target_c = random.choice(towers_coords)
                                                    opp_grid[target_r][target_c] = None # On met la case à null
                                                    
                                                    # 4. On sauvegarde la nouvelle grille mutilée en BDD
                                                    new_grid_json = json.dumps(opp_grid)
                                                    cursor.execute(
                                                        "UPDATE player_grids SET Grid_State = %s WHERE ID_Game = %s AND ID_Users = %s",
                                                        (new_grid_json, self.game_id, self.opponent_id)
                                                    )
                                                    db.commit()
                                            
                                            # On lance le Cooldown dans tous les cas
                                            self.legend_current_cd = self.legend_max_cd 
                                            
                                        except Exception as e:
                                            print(f"Erreur compétence Karthus : {e}")
                                        finally:
                                            cursor.close()
                                            db.close()
                                            
                            continue

                        # PRIORITÉ : Si on est en train de confirmer l'abandon
                        if self.confirm_surrender:
                            if self.btn_confirm_yes.handle_event(event): self.btn_confirm_yes.action()
                            if self.btn_confirm_no.handle_event(event): self.btn_confirm_no.action()
                            continue # On ignore le reste du jeu tant qu'on n'a pas répondu
                        
                        if self.game_over:
                            if self.return_menu_button.handle_event(event): return self.return_menu_button.action()
                        else:
                            grid_pos = self._get_grid_pos_from_mouse(mouse_pos, self.player_grid_rect)
                            
                            if grid_pos and grid_pos in self.player_units_on_board:
                                unit_data = self.player_units_on_board.pop(grid_pos)
                                self.dragging_unit = unit_data
                                self.drag_origin = grid_pos
                                cell_rect = self._get_cell_rect(self.player_grid_rect, grid_pos[0], grid_pos[1])
                                self.drag_offset = (mouse_pos[0] - cell_rect.x, mouse_pos[1] - cell_rect.y)
                            
                            else:
                                if self.add_unit_button.handle_event(event): self.add_unit_button.action()
                                if self.surrender_button.handle_event(event): self.surrender_button.action()

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.dragging_unit:
                            mouse_pos = event.pos
                            new_grid_pos = self._get_grid_pos_from_mouse(mouse_pos, self.player_grid_rect)
                            
                            if new_grid_pos and new_grid_pos not in self.player_units_on_board and new_grid_pos not in self.player_path:
                                self.player_units_on_board[new_grid_pos] = self.dragging_unit
                            
                            elif new_grid_pos and new_grid_pos in self.player_units_on_board:
                                target_unit = self.player_units_on_board[new_grid_pos]
                                
                                # LA CORRECTION DES FUSIONS + LE PASSIF DE L'ONDULEUR
                                is_same_level = target_unit.get('merge_count', 0) == self.dragging_unit.get('merge_count', 0)
                                
                                # C'est la même unité, OU BIEN la carte qu'on glisse est un Onduleur !
                                is_valid_merge = (target_unit['id'] == self.dragging_unit['id']) or (self.dragging_unit.get('name') == 'Onduleur')

                                # === NOUVEAU : INTERDICTION DE FUSION POUR AZIR ===
                                if target_unit.get('is_azir_soldier') or self.dragging_unit.get('is_azir_soldier'):
                                    is_valid_merge = False
                                # ==================================================
                                
                                if is_valid_merge and is_same_level:
                                    current_merges = target_unit.get('merge_count', 0)
                                    if current_merges < 5:
                                        new_count = min(5, current_merges + 1)
                                        target_unit['merge_count'] = new_count
                                        self._update_unit_stats(target_unit)
                                        self.dragging_unit = None 
                                    else:
                                        self.player_units_on_board[self.drag_origin] = self.dragging_unit
                                else:
                                    self.player_units_on_board[self.drag_origin] = self.dragging_unit
                            
                            else:
                                self.player_units_on_board[self.drag_origin] = self.dragging_unit
                            
                            self.dragging_unit = None
                            self.drag_origin = None

                            # =========================================================
                            # NOUVEAU : On sauvegarde la grille en BDD après le mouvement !
                            self._save_grid_to_db()
                            # =========================================================
                    
                    self.add_unit_button.handle_event(event)
                    self.surrender_button.handle_event(event)
                    
                    if self.game_over:
                        if self.return_menu_button.handle_event(event):
                            return self.return_menu_button.action()

            self.screen.fill(self.CYBER_GREY)
            pygame.draw.rect(self.screen, self.UI_BAR_BG, (0, self.screen_height - self.BOTTOM_BAR_HEIGHT, self.screen_width, self.BOTTOM_BAR_HEIGHT))
            
            self._draw_sidebar()
            self._draw_grid_lines(self.opponent_grid_rect, is_opponent=True)
            self._draw_grid_lines(self.player_grid_rect, is_opponent=False)
            
            sep_x_start = self.opponent_grid_rect.left + self.cell_size
            sep_x_end = self.opponent_grid_rect.right - self.cell_size
            sep_y = (self.opponent_grid_rect.bottom + self.player_grid_rect.top) // 2
            pygame.draw.line(self.screen, self.SEPARATOR_COLOR, (sep_x_start, sep_y), (sep_x_end, sep_y), 3)

            # --- AFFICHAGE TEXTE VAGUE ---
            state = getattr(self, 'wave_state', 'TIMER')
            
            if state == 'FIGHTING':
                wave_txt = f"VAGUE {self.wave_number} EN COURS !"
                color_wave = (255, 50, 50) 
            elif state == 'WAITING':
                wave_txt = "EN ATTENTE DE L'ADVERSAIRE..."
                color_wave = (255, 165, 0)
            elif state == 'SAFETY':
                # Texte spécifique pour le Safe Check
                wave_txt = "VÉRIFICATION DE SYNCHRONISATION..."
                color_wave = (0, 255, 255) # Cyan pour rassurer
            else:
                next_w = self.wave_number if self.wave_number > 1 else 1
                wave_txt = f"Prochaine vague ({next_w}): {int(self.wave_timer)}s"
                color_wave = (255, 255, 255)
            
            wave_surf = self.font_ui.render(wave_txt, True, color_wave)
            center_x_zone = self.SIDEBAR_WIDTH + (self.screen_width - self.SIDEBAR_WIDTH) // 2
            wave_rect = wave_surf.get_rect(center=(center_x_zone, 30))
            self.screen.blit(wave_surf, wave_rect)

            elixir_txt = f"Elixir: {int(self.elixir)}/{self.max_elixir}"
            elixir_surf = self.font_ui.render(elixir_txt, True, self.ELIXIR_PURPLE)
            self.screen.blit(elixir_surf, (self.SIDEBAR_WIDTH + 20, self.screen_height - 60))

            hp_txt = f"PV: {self.player_hp}"
            hp_surf = self.font_ui.render(hp_txt, True, (255, 50, 50)) 
            self.screen.blit(hp_surf, (self.screen_width - 120, self.screen_height - 60))

            # --- DESSIN DES UNITÉS DU JOUEUR ---
            for (r, c), u in list(self.player_units_on_board.items()):
                # 1. Dessin normal de l'unité
                self._draw_entity_on_grid(self.player_grid_rect, r, c, u)
                
                if u:
                    # === NOUVEAU : EFFET VISUEL AZIR (Jaune) ===
                    if u.get('is_azir_soldier'):
                        rect = self._get_cell_rect(self.player_grid_rect, r, c)
                        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                        s.fill((255, 255, 0, 60)) # Jaune avec 60 d'opacité
                        self.screen.blit(s, rect.topleft)
                        
                    # === EFFET VISUEL SERVEUR (Cyan) ===
                    elif u.get('name') != 'Serveur':
                        is_buffed = False
                        # Vérification des 8 cases adjacentes
                        for dr in [-1, 0, 1]:
                            for dc in [-1, 0, 1]:
                                if dr == 0 and dc == 0: continue
                                voisin = self.player_units_on_board.get((r + dr, c + dc))
                                if voisin and voisin.get('name') == 'Serveur':
                                    is_buffed = True
                                    break
                            if is_buffed: break
                        
                        if is_buffed:
                            rect = self._get_cell_rect(self.player_grid_rect, r, c)
                            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                            s.fill((0, 255, 255, 60)) # Cyan
                            self.screen.blit(s, rect.topleft)
            # -----------------------------------
            
            # =========================================================
            # Dessin de la grille adverse (en haut)
            
            # LA CORRECTION EST ICI : On ajoute list() pour "figer" le dictionnaire
            # pendant le temps du dessin et éviter que le Thread ne le casse !
            for (r, c), unit in list(self.opponent_units_on_board.items()):
                if unit:
                    # On utilise directement votre méthode _draw_entity_on_grid !
                    # Elle se charge de tout placer dans self.opponent_grid_rect
                    self._draw_entity_on_grid(self.opponent_grid_rect, r, c, unit)
            # =========================================================

            for e in self.my_enemies:
                rect = self._draw_entity_on_grid(self.player_grid_rect, e['row'], e['col'], e['image'], self.ENEMY_COLOR)
                self._draw_hp_bar(rect, e['current_hp'], e['max_hp'])
            for e in self.opponent_enemies:
                rect = self._draw_entity_on_grid(self.opponent_grid_rect, e['row'], e['col'], e['image'], self.ENEMY_COLOR)
                self._draw_hp_bar(rect, e['current_hp'], e['max_hp'])

            for shot in self.visual_attacks:
                if shot.get('is_square'):
                    # Dessine un carré rouge semi-transparent au sol pour la Quarantaine
                    s = pygame.Surface((shot['rect'].width, shot['rect'].height), pygame.SRCALPHA)
                    s.fill((255, 0, 0, 100)) # Rouge transparent
                    self.screen.blit(s, shot['rect'].topleft)
                else:
                    # Laser classique
                    pygame.draw.line(self.screen, self.LASER_COLOR, shot['start'], shot['end'], 3)
            
            for b in self.player_barriers:
                rect = self._get_cell_rect(self.player_grid_rect, b['row'], b['col'])
                pygame.draw.rect(self.screen, (255, 165, 0), rect, 3) # Un beau carré Orange !

            if self.dragging_unit and self.dragging_unit['image']:
                mx, my = pygame.mouse.get_pos()
                img = self.dragging_unit['image']
                self.screen.blit(img, (mx - self.drag_offset[0], my - self.drag_offset[1]))
                if self.dragging_unit.get('merge_count', 0) > 0:
                     pygame.draw.circle(self.screen, (255, 215, 0), (mx - self.drag_offset[0] + 50, my - self.drag_offset[1] + 10), 8)

            if not self.game_over:
                # --- NOUVEAU : DESSIN DE LA LÉGENDE ---
                if hasattr(self, 'legend_id') and self.legend_id > 0 and self.legend_image:
                    self.screen.blit(self.legend_image, self.legend_rect)
                    
                    # Si c'est en Cooldown, on grise et on affiche le chiffre
                    if self.legend_current_cd > 0:
                        dark_surface = pygame.Surface((50, 50), pygame.SRCALPHA)
                        dark_surface.fill((0, 0, 0, 180)) # Voile noir
                        self.screen.blit(dark_surface, self.legend_rect)
                        
                        cd_text = self.font.render(str(self.legend_current_cd), True, (255, 255, 255))
                        cd_rect = cd_text.get_rect(center=self.legend_rect.center)
                        self.screen.blit(cd_text, cd_rect)
                # --------------------------------------
                self.add_unit_button.draw(self.screen)
                self.surrender_button.draw(self.screen)
            else:
                self._draw_game_over()
            
            # --- DESSIN DE LA CONFIRMATION D'ABANDON ---
            if self.confirm_surrender:
                # 1. On dessine un voile noir semi-transparent sur tout l'écran
                overlay = pygame.Surface((self.screen_width, self.screen_height))
                overlay.set_alpha(180)
                overlay.fill((0, 0, 0))
                self.screen.blit(overlay, (0, 0))
                
                # 2. On affiche le message et les boutons
                confirm_surf = self.font_ui.render("ÊTES-VOUS SÛR DE VOULOIR ABANDONNER ?", True, (255, 255, 255))
                confirm_rect = confirm_surf.get_rect(center=(self.screen_width // 2, self.screen_height // 2 - 50))
                self.screen.blit(confirm_surf, confirm_rect)
                self.btn_confirm_yes.draw(self.screen)
                self.btn_confirm_no.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(60)