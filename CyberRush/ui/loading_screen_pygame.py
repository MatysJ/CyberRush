import pygame
import time
import json
from db import Connect
from ui.game_board_pygame import GameBoardPygame
from ui.button import Button # NOUVEAU : Pour le bouton de secours

class LoadingScreenPygame:
    def __init__(self, game_manager, user, opponent_pseudo, id_game, is_host=False):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]
        self.network_client = game_manager.network_client
        self.opponent_pseudo = opponent_pseudo
        self.id_game = id_game
        self.is_host = is_host

        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Chargement...")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.LIGHT_GREY = (200, 200, 200)
        self.font_large = pygame.font.Font(None, 60)
        self.font_small = pygame.font.Font(None, 36)

        self.last_db_check = 0
        self.check_interval = 0.5
        
        # --- NOUVEAUX DRAPEAUX DE PRÉCHARGEMENT ---
        self.game_preloaded = False    # Est-ce que les assets sont chargés ?
        self.handshake_started = False # Est-ce qu'on a commencé à parler à la BDD ?
        self.preloaded_board = None    # Stockera l'instance du jeu
        # ------------------------------------------

        # NOUVEAU : Bouton de secours anti-softlock
        self.abort_button = Button("Quitter", (self.screen_width - 80, 40), self.abort_loading, size=(120, 40), color=(200, 50, 50))

    def _set_player_ready(self):
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT * FROM game_loading_ready WHERE game_id = %s AND user_id = %s", (self.id_game, self.user_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO game_loading_ready (game_id, user_id) VALUES (%s, %s)", (self.id_game, self.user_id))
                    db.commit()
                cursor.close()
                db.close()
            except Exception as e:
                print(f"Erreur DB loading_ready: {e}")

    def _init_player_grid(self):
        print("\n=== [DEBUG HANDSHAKE] DÉBUT INIT BDD JOUEUR ===")
        print(f"Données envoyées -> GameID: {self.id_game} | UserID: {self.user_id}")
        
        db = Connect()
        if not db:
            print("❌ ERREUR : Connexion à la BDD échouée dans l'écran de chargement !")
            return
            
        try:
            cursor = db.cursor()
            
            # ==========================================
            # 1. INITIALISATION DE LA GRILLE (player_grids)
            # ==========================================
            print("Étape 1 : Vérification de la grille...")
            cursor.execute("SELECT ID_Grid FROM player_grids WHERE ID_Game = %s AND ID_Users = %s", (self.id_game, self.user_id))
            if cursor.fetchone():
                print("⚠️ ATTENTION : La grille existe DÉJÀ en BDD.")
            else:
                print("Étape 2 : Création de la grille JSON...")
                default_grid = [[None for _ in range(8)] for _ in range(4)]
                grid_json = json.dumps(default_grid)
                cursor.execute(
                    "INSERT INTO player_grids (ID_Game, ID_Users, Grid_State) VALUES (%s, %s, %s)", 
                    (self.id_game, self.user_id, grid_json)
                )
                print("✅ SUCCÈS : Grille insérée !")

            # ==========================================
            # 2. INITIALISATION DES ENNEMIS (game_enemies)
            # ==========================================
            print("Étape 3 : Vérification de la table game_enemies...")
            cursor.execute("SELECT ID FROM game_enemies WHERE ID_Game = %s AND ID_Player = %s", (self.id_game, self.user_id))
            if cursor.fetchone():
                print("⚠️ ATTENTION : La ligne game_enemies existe DÉJÀ en BDD.")
            else:
                print("Étape 4 : Création de la ligne game_enemies...")
                cursor.execute(
                    "INSERT INTO game_enemies (ID_Game, ID_Player, Add_Enemies) VALUES (%s, %s, NULL)", 
                    (self.id_game, self.user_id)
                )
                print("✅ SUCCÈS : Ligne game_enemies insérée !")

            # On valide toutes les insertions d'un coup
            db.commit()
                
        except Exception as e:
            print(f"❌ ERREUR SQL CRITIQUE : {e}")
        finally:
            try: cursor.close()
            except: pass
            db.close()
            print("=== [DEBUG HANDSHAKE] FIN INIT BDD JOUEUR ===\n")

    def _check_opponent_ready(self):
        db = Connect()
        opponent_ready = False
        if db:
            try:
                cursor = db.cursor()
                cursor.execute("SELECT user_id FROM game_loading_ready WHERE game_id = %s AND user_id != %s", (self.id_game, self.user_id))
                if cursor.fetchone():
                    opponent_ready = True
                cursor.close()
                db.close()
            except Exception as e:
                print(f"Erreur check adversaire: {e}")
        return opponent_ready

    def draw_text(self, text, font, text_col, pos, align="center"):
        img = font.render(text, True, text_col)
        rect = img.get_rect()
        if align == "center":
            rect.center = pos
        self.screen.blit(img, rect)

    def abort_loading(self):
        """Action du bouton Quitter : Force la défaite et libère l'adversaire"""
        print("Annulation du chargement, retour au lobby...")
        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                # 1. Déterminer notre colonne de PV
                cursor.execute("SELECT Player1_ID FROM game_sessions WHERE ID_Game = %s", (self.id_game,))
                session = cursor.fetchone()
                if session:
                    is_player1 = (self.user_id == session[0])
                    my_hp_col = "Player1_HP" if is_player1 else "Player2_HP"
                    
                    # 2. Mettre nos PV à 0
                    cursor.execute(f"UPDATE game_sessions SET {my_hp_col} = 0 WHERE ID_Game = %s", (self.id_game,))
                
                # 3. L'ASTUCE : On s'annonce "Prêt" pour débloquer l'adversaire !
                # Il va lancer la partie, voir nos 0 PV et gagner instantanément.
                cursor.execute("SELECT * FROM game_loading_ready WHERE game_id = %s AND user_id = %s", (self.id_game, self.user_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO game_loading_ready (game_id, user_id) VALUES (%s, %s)", (self.id_game, self.user_id))

                db.commit()
            except Exception as e:
                print(f"Erreur lors de l'annulation : {e}")
            finally:
                try: cursor.close()
                except: pass
                db.close()
        
        # Retour sécurisé au Lobby
        # (Adaptez l'import si le nom de votre fichier lobby est différent)
        from ui.lobby_pygame import LobbyPygame
        return LobbyPygame(self.game_manager, self.user)

    def run(self):
        grid_initialized = False 
        
        while True:
            current_time = time.time()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys
                    sys.exit()

                # NOUVEAU : Écoute du bouton d'annulation
                if self.abort_button.handle_event(event):
                    return self.abort_button.action()

            self.screen.fill(self.CYBER_GREY)

            # =========================================================
            # ÉTAPE 1 (NOUVEL ORDRE) : CRÉATION DE LA GRILLE BDD D'ABORD !
            # =========================================================
            if not grid_initialized:
                print(">> PASSAGE ÉTAPE 1 : Création de la grille...")
                self._init_player_grid()
                grid_initialized = True

            # =========================================================
            # ÉTAPE 2 : LE PRÉCHARGEMENT LOCAL DU PLATEAU
            # =========================================================
            if not self.game_preloaded:
                self.draw_text("CHARGEMENT DES FICHIERS...", self.font_large, self.CYBER_BLUE, (self.screen_width // 2, self.screen_height // 2 - 50))
                pygame.display.flip()
                
                print(">> PASSAGE ÉTAPE 2 : Chargement du plateau de jeu...")
                game_data = {'game_id': self.id_game, 'opponent_pseudo': self.opponent_pseudo}
                # Le plateau est créé ICI, il va donc trouver la grille qu'on vient de créer à l'étape 1 !
                self.preloaded_board = GameBoardPygame(self.game_manager, self.user, self.network_client, game_data)
                
                self.game_preloaded = True
                continue 

            # =========================================================
            # ÉTAPE 3 : DÉBUT DU HANDSHAKE
            # =========================================================
            if not self.handshake_started:
                print(">> PASSAGE ÉTAPE 3 : Envoi du signal 'Prêt'...")
                if self.is_host:
                    self._set_player_ready() 
                self.handshake_started = True

            # =========================================================
            # ÉTAPE 4 : ATTENTE ET LANCEMENT
            # =========================================================
            self.draw_text("PRÊT !", self.font_large, (50, 255, 50), (self.screen_width // 2, self.screen_height // 2 - 50))
            
            if current_time - self.last_db_check > self.check_interval:
                self.last_db_check = current_time
                if self._check_opponent_ready():
                    if not self.is_host:
                        self._set_player_ready()
                        pygame.time.wait(500) 
                    print(">> PASSAGE ÉTAPE 4 : Adversaire prêt, lancement !")
                    return self.preloaded_board
                
            # NOUVEAU : Dessin du bouton d'annulation par-dessus tout
            self.abort_button.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)