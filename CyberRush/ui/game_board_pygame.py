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

        self.unit_cost = 10                  
        self.cost_increment = 10              
        self.last_cost_reduction = time.time() 

        self.last_elixir_update = time.time()

        self.last_damage_time = time.time()
        self.damage_interval = 1.0 
        self.tower_damage = 10
        self.visual_attacks = []
        self.player_barriers = [] 

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
        
        self.add_unit_button = Button(f"Poser ({self.unit_cost})", (ui_center_x, ui_center_y), 
                                      self._place_random_unit, size=(200, 50))
        self.return_menu_button = Button("Retourner au menu", (self.screen_width//2, self.screen_height//2 + 80), self.quit_game, size=(250, 60))
        self.surrender_button = Button("Abandon", (self.screen_width - 100, 50), self.surrender, size=(120, 40), color=(200, 50, 50))

        self._load_player_legend()
        self.legend_rect = pygame.Rect(ui_center_x - 170, ui_center_y - 25, 50, 50)

        self.dragging_unit = None    
        self.drag_origin = None       
        self.drag_offset = (0, 0)     

        self.surrender_button = Button("Abandon", (self.screen_width - 80, 30), self.surrender, size=(100, 40), color=(200, 50, 50))

        self.wave_number = 1           
        self.time_between_waves = 30.0  
        self.wave_timer = 10.0 

        self.wave_state = 'TIMER'      
        self.opponent_wave_state = 0  
        self.safety_timer = 0.0
        
        self.enemies_to_spawn = 0      
        self.spawn_interval = 1.5    
        self.last_spawn_time = 0     

        self.last_opponent_sync = time.time()
        self.sync_interval = 0.5

        self.last_hp_sync = time.time()
        self.hp_sync_interval = 1.0

        self.confirm_surrender = False
        self.btn_confirm_yes = Button("Oui, j'abandonne", (self.screen_width // 2 - 110, self.screen_height // 2 + 50), 
                                      self._do_surrender, size=(200, 50), color=(200, 50, 50))
        self.btn_confirm_no = Button("Non, je reste", (self.screen_width // 2 + 110, self.screen_height // 2 + 50), 
                                     self._cancel_surrender, size=(200, 50), color=(50, 200, 50))

        self.last_confirmed_db_grid = [[None for _ in range(8)] for _ in range(4)]
         
    def _init_player_grid(self):
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                check_query = "SELECT ID_Grid FROM player_grids WHERE ID_Game = %s AND ID_Users = %s"
                cursor.execute(check_query, (self.id_game, self.user_id))
            
                if not cursor.fetchone():
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
                
                self.last_confirmed_db_grid = grid_obj
                
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
                        "merge_count": unit.get("merge_count", 0) 
                    }
        
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
                    self.opponent_units_on_board.clear()
                    
                    for r in range(4):
                        for c in range(8):
                            mirrored_r = 3 - r       
                            mirrored_c = 7 - c       
                            py_col = mirrored_c + 1   
                            
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
                                    
                                    if full_unit.get('image'):
                                        full_unit['image'] = pygame.transform.flip(full_unit['image'], True, True)
                                    self.opponent_units_on_board[(mirrored_r, py_col)] = full_unit

            except Exception as e:
                print(f"Erreur de synchronisation avec l'adversaire : {e}")
            finally:
                try: cursor.close()
                except: pass
                db.close()

    def _check_my_grid_from_db(self):
        """Vérifie si une force extérieure (Karthus) a supprimé une de nos tours en BDD"""
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute(
                    "SELECT Grid_State FROM player_grids WHERE ID_Game = %s AND ID_Users = %s", 
                    (self.game_id, self.user_id)
                )
                row = cursor.fetchone()
                
                if row and row[0]:
                    import json
                    my_db_grid = json.loads(row[0])
                    
                    if not hasattr(self, 'last_confirmed_db_grid'):
                        return
                        
                    towers_to_remove = []
                    
                    for r in range(4):
                        for c in range(8):
                            if self.last_confirmed_db_grid[r][c] is not None:
                                if my_db_grid[r][c] is None:
                                    towers_to_remove.append((r + 1, c + 1))
                                    self.last_confirmed_db_grid[r][c] = None
                                    
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
                self.wave_state = 'WAITING'
                self.wave_number += 1
                threading.Thread(target=self._update_db_wave, args=(self.wave_number,), daemon=True).start()

        elif state == 'WAITING':
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
        self.wave_state = 'FIGHTING'
        
        self.elixir += ((self.wave_number - 1) * 1.0)
        self.elixir = min(self.elixir, self.max_elixir)

        base_spawn_interval = 1.5 
        self.spawn_interval = max(0.1, base_spawn_interval * (0.95 ** (self.wave_number - 1)))

        self.kindred_invulnerable = False

        if getattr(self, 'legend_id', -1) == 0:
            if self.wave_number > 0 and self.wave_number % 25 == 0:
                self.player_hp += 1
                
        if hasattr(self, 'legend_passive_name') and self.legend_passive_name == 'King_Realm':
            if self.wave_number >= 5 and self.wave_number % 5 == 0:
                db = Connect()
                if db:
                    try:
                        cursor = db.cursor()
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

        penalty = 0
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT Add_Enemies FROM game_enemies WHERE ID_Game = %s AND ID_Player = %s", (self.game_id, self.user_id))
                row = cursor.fetchone()
                
                if row and row[0] is not None:
                    penalty = int(row[0])
                    
            except Exception as e:
                print(f"Erreur vérification game_enemies : {e}")
            finally:
                try: cursor.close()
                except: pass
                db.close()

        total_enemies = self.wave_number + penalty

        if hasattr(self, 'legend_passive_name') and self.legend_passive_name == 'Shurima_Shuffle':
            if self.available_deck:
                
                towers_to_remove = []
                for pos, unit in self.player_units_on_board.items():
                    if unit and unit.get('is_azir_soldier'):
                        towers_to_remove.append(pos)
                        
                for pos in towers_to_remove:
                    del self.player_units_on_board[pos]

                if getattr(self, 'dragging_unit', None) and self.dragging_unit.get('is_azir_soldier'):
                    self.dragging_unit = None  
                    self.drag_origin = None   

                valid_rows = range(1, self.grid_rows)     
                valid_cols = range(1, self.grid_cols - 1) 
                empty_cells = [(r, c) for r in valid_rows for c in valid_cols if (r, c) not in self.player_units_on_board]
                
                if empty_cells:
                    target_cell = random.choice(empty_cells)
                    unit_to_place = random.choice(self.available_deck).copy()
                    
                    bonus_level = self.wave_number // 20
                    unit_to_place['merge_count'] = min(4, 1 + bonus_level)
                    
                    unit_to_place['is_azir_soldier'] = True 
                    
                    self._update_unit_stats(unit_to_place)
                    unit_to_place['last_attack_time'] = time.time()
                    
                    self.player_units_on_board[target_cell] = unit_to_place
                    self._save_grid_to_db()
        
        self.enemy_spawn_queue = [] 
        
        if self.wave_number % 25 == 0 and self.enemy_types.get(3):
            boss = random.choice(self.enemy_types[3])
            self.enemy_spawn_queue.append(boss)
            total_enemies -= 1
            
        elif self.wave_number % 5 == 0 and self.enemy_types.get(2):
            boss = random.choice(self.enemy_types[2])
            self.enemy_spawn_queue.append(boss)
            total_enemies -= 1
            
        if self.enemy_types.get(1):
            for _ in range(total_enemies):
                self.enemy_spawn_queue.append(random.choice(self.enemy_types[1]))
                
        self.enemies_to_spawn = len(self.enemy_spawn_queue)
        self.last_spawn_time = time.time()

        if hasattr(self, 'legend_current_cd') and self.legend_current_cd > 0:
            self.legend_current_cd -= 1

    def _load_deck(self):
        deck_units = []
        db = Connect()
        if not db: return deck_units
        try:
            cursor = db.cursor(dictionary=True)
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
                    'disabled': False 
                })
            cursor.close()
            db.close()
        except Exception as e:
            print(f"Erreur _load_deck : {e}")
        finally:
            try: cursor.close()
            except: pass
            db.close()
            
        return deck_units
            
        return deck_units

    def _load_enemy_types(self):
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
                        self.legend_image = pygame.transform.scale(img, (50, 50)) 
            except Exception as e:
                print(f"Erreur chargement légende en jeu : {e}")
            finally:
                cursor.close()
                db.close()

    def _update_elixir(self):
        if self.game_over: return
        
        generation_rate = 2.0 / 60.0
        
        for (r, c), unit in list(self.player_units_on_board.items()):
            if unit and unit.get('name') == 'Mineur Crypto':
                bonus_par_seconde = 0.5 + (unit.get('merge_count', 0) * 0.5)
                generation_rate += (bonus_par_seconde / 60.0)
                
        self.elixir += generation_rate
        
        if self.elixir > self.max_elixir:
            self.elixir = self.max_elixir
        
        current_time = time.time()
        if current_time - getattr(self, 'last_cost_reduction', 0) >= 1.0:
            
            if self.unit_cost > 30:
                self.unit_cost -= 1
                
                if hasattr(self, 'add_unit_button'):
                    self.add_unit_button.text = f"Poser ({self.unit_cost})"
                    
            self.last_cost_reduction = current_time

    def _spawn_enemy_action(self):
        if self.game_over: return
        enemy_data = self._create_enemy_data()
        
        if not enemy_data: return 
        
        start_pos = self.player_path[0]
        enemy_data['row'] = start_pos[0]
        enemy_data['col'] = start_pos[1]
        
        enemy_data['path_index'] = 0 
        enemy_data['path_index_float'] = 0.0 

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
                    "speed": enemy_data['speed'],
                    "id": enemy_data['id']
                }
            })

    def _create_enemy_data(self):
        if not hasattr(self, 'enemy_spawn_queue') or not self.enemy_spawn_queue:
            return None
            
        base_enemy = self.enemy_spawn_queue.pop(0)
        passive = base_enemy.get('passive', '')
        
        enemy_dict = base_enemy.copy()
        
        if passive == 'Morpho' and self.enemy_types.get(1):
            choices = [e for e in self.enemy_types[1] if e.get('passive') != 'Morpho']
            if choices:
                target = random.choice(choices)
                enemy_dict['name'] = target['name']
                enemy_dict['image'] = target['image']
                enemy_dict['speed'] = target['speed']
                enemy_dict['hp'] = int(target['hp'] * 1.5)
                
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
                self.available_deck = [u for u in self.player_deck if not u.get('disabled', False)]

        kills = getattr(self, 'total_enemies_killed', 0)
        base_hp = enemy_dict.get('hp', 10) 
        
        enemy_id = enemy_dict.get('id')
        
        enemy_difficulty = enemy_dict.get('difficulty', 1) 
        
        if enemy_id == 3: 
            final_hp = base_hp + kills 
            
        elif enemy_difficulty == 2:
            hp_multiplier = 1.10 ** (self.wave_number - 1)
            final_hp = int(base_hp * hp_multiplier)
            
        else:
            hp_multiplier = 1.10 ** (self.wave_number - 1)
            final_hp = int(base_hp * hp_multiplier)

        return {
            'id': str(time.time()) + str(random.randint(0, 99999)), 
            'enemy_id': enemy_dict['id'],
            'name': enemy_dict['name'],
            'max_hp': final_hp,       
            'current_hp': final_hp,   
            'speed': enemy_dict['speed'],
            'reward': enemy_dict['reward'],
            'passive': passive, 
            'image': enemy_dict['image'],
            'row': 0.0, 
            'col': random.randint(1, self.grid_cols - 2)
        }

    def _handle_opponent_move_unit(self, data):
        self._fetch_opponent_grid()

    def _handle_opponent_spawn(self, data):
        e_data = data.get("enemy_data", {})
        
        img = None
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
            'path_index_float': 0.0, 
            'name': e_data.get('name', 'Ennemi'),
            'max_hp': e_data.get('max_hp', 100),
            'current_hp': e_data.get('current_hp', 100),
            'speed': e_data.get('speed', 1),
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
                return pygame.transform.scale(avatar_img, (60, 60))
        except Exception as e:
            print(f"Erreur lors du chargement de l'avatar en jeu : {e}")
            
        return None

    def _update_combat(self):
        if self.game_over: return
        current_time = time.time()

        active_barrier_ids = [u.get('my_barrier_id') for u in self.player_units_on_board.values() 
                              if u and u.get('name') == 'Firewall' and u.get('my_barrier_id')]
        
        if hasattr(self, 'dragging_unit') and self.dragging_unit and self.dragging_unit.get('name') == 'Firewall':
            if self.dragging_unit.get('my_barrier_id'):
                active_barrier_ids.append(self.dragging_unit['my_barrier_id'])
                              
        self.player_barriers = [b for b in self.player_barriers if b['id'] in active_barrier_ids]

        for (t_row, t_col), unit in list(self.player_units_on_board.items()):
            if unit is None: continue
            
            if unit.get('current_attack', 0) <= 0:
                continue
                
            if current_time - unit.get('last_attack_time', 0) >= unit.get('attack_cooldown', 1.0):
                
                enemies_with_dist = []
                for enemy in self.my_enemies:
                    if enemy.get('current_hp', 0) > 0:
                        dist = math.sqrt((t_row - enemy['row'])**2 + (t_col - enemy['col'])**2)
                        enemies_with_dist.append((dist, enemy))
                
                if not enemies_with_dist:
                    continue 
                
                u_name = unit.get('name', '')
                
                if u_name == 'Antivirus':
                    enemies_with_dist.sort(key=lambda x: x[1].get('current_hp', 0), reverse=True)
                elif u_name == 'Tourelle SQL':
                    enemies_with_dist.sort(key=lambda x: x[1].get('current_hp', 0))
                else:
                    enemies_with_dist.sort(key=lambda x: x[0]) 

                server_bonus = 1.0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0: continue
                        voisin = self.player_units_on_board.get((t_row + dr, t_col + dc))
                        if voisin and voisin.get('name') == 'Serveur':
                            server_bonus += 0.30 

                base_damage = unit.get('current_attack', 10)
                damage = base_damage * server_bonus
                
                attack_executed = False
                targets = []

                u_type = unit.get('type', 'Cible Unique')

                if u_type == 'Cible Unique':
                    targets.append(enemies_with_dist[0][1])

                elif u_type == 'Cible Multiples':
                    for _, enemy in enemies_with_dist[:3]:
                        targets.append(enemy)

                elif u_type == 'AOE' or u_name == 'Générateur de Zone de Quarantaine':
                    splash_radius = 1.5 
                    
                    if u_name == 'Générateur de Zone de Quarantaine':
                        for dr in [-1, 0, 1]:
                            for dc in [-1, 0, 1]:
                                z_rect = self._get_cell_rect(self.player_grid_rect, t_row + dr, t_col + dc)
                                self.visual_attacks.append({
                                    'is_square': True, 
                                    'rect': z_rect, 
                                    'time': current_time
                                })
                        
                        for dist_from_tower, enemy in enemies_with_dist:
                            if dist_from_tower <= splash_radius:
                                enemy['current_hp'] -= damage
                        attack_executed = True
                        
                    else:
                        primary_target = enemies_with_dist[0][1]
                        targets.append(primary_target)
                        for dist_from_tower, enemy in enemies_with_dist[1:]:
                            dist_from_target = math.sqrt((primary_target['row'] - enemy['row'])**2 + (primary_target['col'] - enemy['col'])**2)
                            if dist_from_target <= splash_radius:
                                enemy['current_hp'] -= damage 
                                
                elif u_name == 'Firewall':
                    if not unit.get('barrier_placed'):
                        occupied_pos = [(b['row'], b['col']) for b in self.player_barriers]
                        
                        available_path = [p for p in self.player_path if p not in occupied_pos]
                        
                        if available_path:
                            trap_pos = random.choice(available_path)
                            trap_id = random.randint(1, 9999999) 
                            
                            self.player_barriers.append({
                                'id': trap_id,
                                'row': trap_pos[0],
                                'col': trap_pos[1],
                                'damage': damage 
                            })
                            unit['barrier_placed'] = True 
                            
                            unit['my_barrier_id'] = trap_id 
                            
                            attack_executed = True
                
                for target in targets:
                    target['current_hp'] -= damage
                    
                    start_rect = self._get_cell_rect(self.player_grid_rect, t_row, t_col)
                    end_rect = self._get_cell_rect(self.player_grid_rect, target['row'], target['col'])
                    
                    self.visual_attacks.append({
                        'start': (start_rect.centerx, start_rect.centery),
                        'end': (end_rect.centerx, end_rect.centery),
                        'time': current_time
                    })
                    attack_executed = True
                
                if attack_executed:
                    unit['last_attack_time'] = current_time

        self.visual_attacks = [v for v in self.visual_attacks if current_time - v['time'] < 0.1]


    def _update_enemies(self):
        if self.game_over: return
        
        if not hasattr(self, 'total_enemies_killed'):
            self.total_enemies_killed = 0
            
        current_time = time.time() 
        enemies_to_remove = []
        new_spawns = [] 
        
        for enemy in self.my_enemies:
            
            if enemy.get('current_hp', 1) <= 0:
                self.elixir += enemy.get('reward', 1) 
                
                self.total_enemies_killed += 1 
                
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
                        hp_multiplier = 1.0 + (self.wave_number * 0.03)
                        final_hp = int(virus_template['hp'] * hp_multiplier)
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
                continue
                
            base_speed = enemy.get('speed', 1) 
            current_speed = base_speed
            
            if current_time < enemy.get('slow_until', 0):
                current_speed = base_speed * 0.75 
                
            enemy['path_index_float'] += current_speed / 60.0
            idx = int(enemy['path_index_float'])
            
            if 'hit_barriers' not in enemy:
                enemy['hit_barriers'] = []
            
            for b in self.player_barriers:
                if b['id'] not in enemy['hit_barriers']:
                    if math.sqrt((enemy['row'] - b['row'])**2 + (enemy['col'] - b['col'])**2) < 0.5:
                        enemy['slow_until'] = current_time + 1.0 
                        enemy['current_hp'] -= b.get('damage', 10)
                        enemy['hit_barriers'].append(b['id']) 
            
            if idx >= len(self.player_path) - 1:
                if getattr(self, 'kindred_invulnerable', False):
                    print("Kindred")
                else:
                    self.player_hp -= 1
                    
                    if self.player_hp <= 0 and self.legend_passive_name == 'Imminent_Death' and not getattr(self, 'karthus_used_passive', False):
                        self.player_hp = 1
                        self.karthus_used_passive = True
                        
                enemies_to_remove.append(enemy)
                if self.player_hp <= 0:
                    self._sync_hp_db()

            else:
                enemy['path_index'] = idx
                fraction = enemy['path_index_float'] - idx
                curr_pos = self.player_path[idx]
                next_pos = self.player_path[idx + 1]
                enemy['row'] = curr_pos[0] + (next_pos[0] - curr_pos[0]) * fraction
                enemy['col'] = curr_pos[1] + (next_pos[1] - curr_pos[1]) * fraction

        for e in enemies_to_remove:
            if e in self.my_enemies:
                self.my_enemies.remove(e)
                
        self.my_enemies.extend(new_spawns)

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
        
        self._update_unit_stats(unit_to_place)
        unit_to_place['last_attack_time'] = time.time() 

        self.elixir -= self.unit_cost
        
        self.unit_cost += 10  

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
        self._save_grid_to_db()

    def _update_unit_stats(self, unit):
        """Calcule les stats finales de la tour en fonction de son Level et de ses Fusions"""
        level_bonus = unit.get('level', 1) - 1
        merge_count = unit.get('merge_count', 0)
        
        base_atk = unit.get('base_attack', 0) + (level_bonus * unit.get('attack_growth', 0))
        base_ats = unit.get('base_attack_speed', 0.1) + (level_bonus * unit.get('ats_growth', 0.0))
        
        unit['current_attack'] = base_atk * (1 + (merge_count * 0.50))
        if hasattr(self, 'legend_passive_name') and self.legend_passive_name == 'Blood_Lusted':
            hp_missing = 5 - self.player_hp
            if hp_missing > 0:
                bonus = hp_missing * 0.12 
                unit['current_attack'] *= (1 + bonus)
        unit['current_attack_speed'] = base_ats * (1 + (merge_count * 0.20))
        
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
            
            if image:
                img_rect = image.get_rect(center=cell_rect.center)
                self.screen.blit(image, img_rect)
            else:
                pygame.draw.circle(self.screen, color_fallback, cell_rect.center, self.cell_size // 3)

            fusion_level = unit_data.get('merge_count', 0) + 1 
            card_level = unit_data.get('level', 1)
            
            font_lvl = pygame.font.Font(None, 20) 
            
            lvl_text = font_lvl.render(f"T{fusion_level} (N.{card_level})", True, (255, 255, 255))
            
            text_rect = lvl_text.get_rect(bottomright=(cell_rect.right - 4, cell_rect.bottom - 4))
            
            bg_surface = pygame.Surface((text_rect.width + 6, text_rect.height + 4), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 150))
            
            self.screen.blit(bg_surface, (text_rect.x - 3, text_rect.y - 2))
            self.screen.blit(lvl_text, text_rect)

            return cell_rect

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
                img = pygame.transform.scale(u['image'], (50, 50))
                img_x = (self.SIDEBAR_WIDTH - 50) // 2
                
                if u.get('disabled', False):
                    img = img.copy()
                    img.fill((100, 100, 100), special_flags=pygame.BLEND_RGBA_MULT)
                    self.screen.blit(img, (img_x, y))
                    
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

                cursor.execute(f"UPDATE game_sessions SET {my_hp_col} = %s WHERE ID_Game = %s", (self.player_hp, self.game_id))
                db.commit()

                cursor.execute(f"SELECT {opp_hp_col}, {opp_wave_col}, {opp_ready_col}, Player1_Legend, Player2_Legend FROM game_sessions WHERE ID_Game = %s", (self.game_id,))
                row = cursor.fetchone()

                if row:
                    if row[0] is not None: self.opponent_hp = row[0]
                    if row[1] is not None: self.opponent_wave_db = row[1]
                    
                    opp_ready_state = row[2]
                    if opp_ready_state == 1:
                        opp_legend_id = row[4] if self.is_player1 else row[3]
                                
                        if opp_legend_id == 4: 
                            self.mordekaiser_penalty = getattr(self, 'mordekaiser_penalty', 0) + 5
                        
                        cursor.execute(f"UPDATE game_sessions SET {opp_ready_col} = 0 WHERE ID_Game = %s", (self.game_id,))
                        db.commit()

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
        self._check_my_grid_from_db()

    def surrender(self):
        self.confirm_surrender = True

    def _do_surrender(self):
        """Action déclenchée si le joueur clique sur OUI"""
        self.player_hp = 0
        self.confirm_surrender = False
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
        self.last_sync_time = time.time()
        
        while True:
            current_time = time.time()
            
            if current_time - getattr(self, 'last_sync_time', 0) > 0.5:
                threading.Thread(target=self._background_sync, daemon=True).start()
                self.last_sync_time = current_time

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

                        if hasattr(self, 'legend_rect') and self.legend_rect.collidepoint(event.pos):
                            if self.legend_id > 0 and self.legend_current_cd == 0 and self.legend_active_name and self.legend_active_name != 'None':
                                if self.legend_active_name == 'Upgrade':
                                    towers = list(self.player_units_on_board.keys())
                                    if towers:
                                        target = random.choice(towers)
                                        unit = self.player_units_on_board[target]
                                        if unit.get('merge_count', 0) < 5:
                                            unit['merge_count'] += 1
                                            self._update_unit_stats(unit)
                                            self._save_grid_to_db()
                                            self.legend_current_cd = self.legend_max_cd 
                                            
                                elif self.legend_active_name == 'Peace_Embrace':
                                    self.kindred_invulnerable = True
                                    self.legend_current_cd = self.legend_max_cd 
                                    
                                elif self.legend_active_name == 'Mortal_Requiem':
                                    db = Connect()
                                    if db:
                                        try:
                                            cursor = db.cursor()
                                            
                                            cursor.execute(
                                                "SELECT Grid_State FROM player_grids WHERE ID_Game = %s AND ID_Users = %s", 
                                                (self.game_id, self.opponent_id)
                                            )
                                            row = cursor.fetchone()
                                            
                                            if row and row[0]:
                                                import json
                                                opp_grid = json.loads(row[0])
                                                
                                                towers_coords = []
                                                for r in range(4):
                                                    for c in range(8):
                                                        if opp_grid[r][c] is not None:
                                                            towers_coords.append((r, c))
                                                            
                                                if towers_coords:
                                                    target_r, target_c = random.choice(towers_coords)
                                                    opp_grid[target_r][target_c] = None 
                                                    
                                                    new_grid_json = json.dumps(opp_grid)
                                                    cursor.execute(
                                                        "UPDATE player_grids SET Grid_State = %s WHERE ID_Game = %s AND ID_Users = %s",
                                                        (new_grid_json, self.game_id, self.opponent_id)
                                                    )
                                                    db.commit()
                                            
                                            self.legend_current_cd = self.legend_max_cd 
                                            
                                        except Exception as e:
                                            print(f"Erreur compétence Karthus : {e}")
                                        finally:
                                            cursor.close()
                                            db.close()
                                            
                            continue

                        if self.confirm_surrender:
                            if self.btn_confirm_yes.handle_event(event): self.btn_confirm_yes.action()
                            if self.btn_confirm_no.handle_event(event): self.btn_confirm_no.action()
                            continue 
                        
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
                                
                                is_same_level = target_unit.get('merge_count', 0) == self.dragging_unit.get('merge_count', 0)
                                
                                is_valid_merge = (target_unit['id'] == self.dragging_unit['id']) or (self.dragging_unit.get('name') == 'Onduleur')

                                if target_unit.get('is_azir_soldier') or self.dragging_unit.get('is_azir_soldier'):
                                    is_valid_merge = False
                                
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

                            self._save_grid_to_db()
                    
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

            state = getattr(self, 'wave_state', 'TIMER')
            
            if state == 'FIGHTING':
                wave_txt = f"VAGUE {self.wave_number} EN COURS !"
                color_wave = (255, 50, 50) 
            elif state == 'WAITING':
                wave_txt = "EN ATTENTE DE L'ADVERSAIRE..."
                color_wave = (255, 165, 0)
            elif state == 'SAFETY':
                wave_txt = "VÉRIFICATION DE SYNCHRONISATION..."
                color_wave = (0, 255, 255)
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

            for (r, c), u in list(self.player_units_on_board.items()):
                self._draw_entity_on_grid(self.player_grid_rect, r, c, u)
                
                if u:
                    if u.get('is_azir_soldier'):
                        rect = self._get_cell_rect(self.player_grid_rect, r, c)
                        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                        s.fill((255, 255, 0, 60)) 
                        self.screen.blit(s, rect.topleft)
                        
                    elif u.get('name') != 'Serveur':
                        is_buffed = False
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

            for (r, c), unit in list(self.opponent_units_on_board.items()):
                if unit:
                    self._draw_entity_on_grid(self.opponent_grid_rect, r, c, unit)

            for e in self.my_enemies:
                rect = self._draw_entity_on_grid(self.player_grid_rect, e['row'], e['col'], e['image'], self.ENEMY_COLOR)
                self._draw_hp_bar(rect, e['current_hp'], e['max_hp'])
            for e in self.opponent_enemies:
                rect = self._draw_entity_on_grid(self.opponent_grid_rect, e['row'], e['col'], e['image'], self.ENEMY_COLOR)
                self._draw_hp_bar(rect, e['current_hp'], e['max_hp'])

            for shot in self.visual_attacks:
                if shot.get('is_square'):
                    s = pygame.Surface((shot['rect'].width, shot['rect'].height), pygame.SRCALPHA)
                    s.fill((255, 0, 0, 100)) 
                    self.screen.blit(s, shot['rect'].topleft)
                else:
                    pygame.draw.line(self.screen, self.LASER_COLOR, shot['start'], shot['end'], 3)
            
            for b in self.player_barriers:
                rect = self._get_cell_rect(self.player_grid_rect, b['row'], b['col'])
                pygame.draw.rect(self.screen, (255, 165, 0), rect, 3) 

            if self.dragging_unit and self.dragging_unit['image']:
                mx, my = pygame.mouse.get_pos()
                img = self.dragging_unit['image']
                self.screen.blit(img, (mx - self.drag_offset[0], my - self.drag_offset[1]))
                if self.dragging_unit.get('merge_count', 0) > 0:
                     pygame.draw.circle(self.screen, (255, 215, 0), (mx - self.drag_offset[0] + 50, my - self.drag_offset[1] + 10), 8)

            if not self.game_over:
                if hasattr(self, 'legend_id') and self.legend_id > 0 and self.legend_image:
                    self.screen.blit(self.legend_image, self.legend_rect)
                    
                    if self.legend_current_cd > 0:
                        dark_surface = pygame.Surface((50, 50), pygame.SRCALPHA)
                        dark_surface.fill((0, 0, 0, 180)) # Voile noir
                        self.screen.blit(dark_surface, self.legend_rect)
                        
                        cd_text = self.font.render(str(self.legend_current_cd), True, (255, 255, 255))
                        cd_rect = cd_text.get_rect(center=self.legend_rect.center)
                        self.screen.blit(cd_text, cd_rect)
                self.add_unit_button.draw(self.screen)
                self.surrender_button.draw(self.screen)
            else:
                self._draw_game_over()
            
            if self.confirm_surrender:
                overlay = pygame.Surface((self.screen_width, self.screen_height))
                overlay.set_alpha(180)
                overlay.fill((0, 0, 0))
                self.screen.blit(overlay, (0, 0))
                
                confirm_surf = self.font_ui.render("ÊTES-VOUS SÛR DE VOULOIR ABANDONNER ?", True, (255, 255, 255))
                confirm_rect = confirm_surf.get_rect(center=(self.screen_width // 2, self.screen_height // 2 - 50))
                self.screen.blit(confirm_surf, confirm_rect)
                self.btn_confirm_yes.draw(self.screen)
                self.btn_confirm_no.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(60)
