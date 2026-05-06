import pygame
import sys
from db import Connect
from ui.button import Button
import time

class MessagingPygame:
    def __init__(self, game_manager, user):
        self.game_manager = game_manager
        self.user = user
        self.user_id = user[0]

        self.screen_width = self.game_manager.screen_width
        self.screen_height = self.game_manager.screen_height
        self.screen = pygame.display.get_surface() or pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Cyber Rush - Messagerie")
        self.clock = pygame.time.Clock()

        self.CYBER_BLUE = (0, 150, 255)
        self.CYBER_GREY = (50, 50, 50)
        self.BG_COLOR = (30, 30, 30)
        self.TEXT_COLOR = (255, 255, 255)
        self.MY_MSG_COLOR = (100, 255, 100) 
        self.OTHER_MSG_COLOR = (200, 200, 200) 
        self.INPUT_BG = (20, 20, 20)
        self.INPUT_ACTIVE = (60, 60, 80)

        self.font = pygame.font.Font(None, 28)
        self.font_title = pygame.font.Font(None, 50)

        self.friends = self.load_friends()
        self.selected_friend = None 
        self.chat_history = []
        
        self.input_text = ""
        self.input_active = False
        self.cursor_pos = 0 
        self.input_rect = pygame.Rect(self.screen_width // 3 + 20, self.screen_height - 80, self.screen_width * 2 // 3 - 160, 50)

        self.back_button = Button("Retour Menu", (120, 40), self.go_back, size=(180, 40), color=(200, 50, 50))
        self.send_button = Button("Envoyer", (self.screen_width - 70, self.screen_height - 55), self.send_message, size=(100, 40))

        self.sidebar_width = self.screen_width // 3

    def go_back(self):
        from ui.main_menu_pygame import MainMenuPygame
        return MainMenuPygame(self.game_manager, self.user)

    def load_friends(self):
        friends_list = []
        db = Connect()
        if db:
            try:
                cursor = db.cursor(dictionary=True)
                query = """
                    SELECT u.ID_Users, u.Pseudo 
                    FROM friends f
                    JOIN users u ON (f.Sender_ID = u.ID_Users OR f.Receiver_ID = u.ID_Users)
                    WHERE (f.Sender_ID = %s OR f.Receiver_ID = %s) 
                    AND u.ID_Users != %s 
                    AND f.Status = 'Accepted'
                """
                cursor.execute(query, (self.user_id, self.user_id, self.user_id))
                friends_list = cursor.fetchall()
                cursor.close()
                db.close()
            except Exception as e:
                print(f"Erreur chargement amis messagerie: {e}") 
        return friends_list

    def load_chat_history(self, friend_id):
        history = []
        db = Connect()
        if db:
            try:
                cursor = db.cursor(dictionary=True)
                query = """
                    SELECT Sender_ID, Message_Text 
                    FROM messages 
                    WHERE (Sender_ID = %s AND Receiver_ID = %s) 
                       OR (Sender_ID = %s AND Receiver_ID = %s)
                    ORDER BY Created_At DESC
                    LIMIT 15
                """
                cursor.execute(query, (self.user_id, friend_id, friend_id, self.user_id))
                rows = cursor.fetchall()
                history = list(reversed(rows))
                
                update_read = "UPDATE messages SET Is_Read = 1 WHERE Receiver_ID = %s AND Sender_ID = %s"
                cursor.execute(update_read, (self.user_id, friend_id))
                db.commit()
                
                cursor.close()
                db.close()
            except Exception as e:
                print(f"Erreur chargement historique: {e}")
        return history

    def select_friend(self, friend_id, friend_pseudo):
        self.selected_friend = {'id': friend_id, 'pseudo': friend_pseudo}
        self.chat_history = self.load_chat_history(friend_id)
        self.input_text = ""
        self.cursor_pos = 0 

    def send_message(self):
        if not self.selected_friend or not self.input_text.strip():
            return

        db = Connect()
        if db:
            try:
                cursor = db.cursor()
                query = "INSERT INTO messages (Sender_ID, Receiver_ID, Message_Text) VALUES (%s, %s, %s)"
                cursor.execute(query, (self.user_id, self.selected_friend['id'], self.input_text.strip()))
                db.commit()
                cursor.close()
                db.close()
                
                self.chat_history = self.load_chat_history(self.selected_friend['id'])
                self.input_text = ""
                self.cursor_pos = 0
            except Exception as e:
                print(f"Erreur envoi message: {e}")

    def run(self):
        friend_buttons = []
    
        y_offset = 140 
        for f in self.friends:
            btn = Button(f["Pseudo"], (self.sidebar_width // 2, y_offset), 
                         lambda fid=f["ID_Users"], fpseudo=f["Pseudo"]: self.select_friend(fid, fpseudo), 
                         size=(self.sidebar_width - 40, 40))
            friend_buttons.append(btn)
            y_offset += 50

        pygame.time.set_timer(pygame.USEREVENT + 1, 3000)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                
                if event.type == pygame.USEREVENT + 1:
                    if self.selected_friend:
                        self.chat_history = self.load_chat_history(self.selected_friend['id'])

                if self.back_button.handle_event(event): return self.back_button.action()
                
                if self.selected_friend:
                    if self.send_button.handle_event(event): self.send_button.action()

                for btn in friend_buttons:
                    if btn.handle_event(event): btn.action()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.input_rect.collidepoint(event.pos):
                            self.input_active = True
                            rel_x = event.pos[0] - (self.input_rect.x + 10)
                            best_pos = 0
                            
                            for i in range(len(self.input_text) + 1):
                                text_width = self.font.size(self.input_text[:i])[0]
                                if text_width > rel_x:
                                    prev_width = self.font.size(self.input_text[:i-1])[0] if i > 0 else 0
                                    if abs(text_width - rel_x) < abs(prev_width - rel_x):
                                        best_pos = i
                                    else:
                                        best_pos = max(0, i - 1)
                                    break
                                best_pos = i
                            self.cursor_pos = best_pos
                            
                        else:
                            self.input_active = False

                if event.type == pygame.KEYDOWN and self.input_active:
                    if event.key == pygame.K_RETURN:
                        self.send_message()
                    elif event.key == pygame.K_BACKSPACE:
                        if self.cursor_pos > 0:
                            self.input_text = self.input_text[:self.cursor_pos-1] + self.input_text[self.cursor_pos:]
                            self.cursor_pos -= 1
                    elif event.key == pygame.K_LEFT:
                        self.cursor_pos = max(0, self.cursor_pos - 1)
                    elif event.key == pygame.K_RIGHT:
                        self.cursor_pos = min(len(self.input_text), self.cursor_pos + 1)
                    else:
                        if len(self.input_text) < 60 and event.unicode:
                            self.input_text = self.input_text[:self.cursor_pos] + event.unicode + self.input_text[self.cursor_pos:]
                            self.cursor_pos += 1

            self.screen.fill(self.BG_COLOR)

            pygame.draw.rect(self.screen, self.CYBER_GREY, (0, 0, self.sidebar_width, self.screen_height))
            pygame.draw.line(self.screen, self.CYBER_BLUE, (self.sidebar_width, 0), (self.sidebar_width, self.screen_height), 3)
            
            self.back_button.draw(self.screen)
            
            title_friends = self.font.render("Vos Amis", True, self.CYBER_BLUE)
            self.screen.blit(title_friends, title_friends.get_rect(center=(self.sidebar_width // 2, 80)))

            for btn in friend_buttons:
                btn.draw(self.screen)

            if self.selected_friend:
                chat_title = self.font_title.render(f"Conversation avec {self.selected_friend['pseudo']}", True, self.CYBER_BLUE)
                self.screen.blit(chat_title, (self.sidebar_width + 30, 30))

                msg_y = 100
                for msg in self.chat_history:
                    is_me = (msg['Sender_ID'] == self.user_id)
                    text_color = self.MY_MSG_COLOR if is_me else self.OTHER_MSG_COLOR
                    prefix = "Moi : " if is_me else f"{self.selected_friend['pseudo']} : "
                    
                    msg_surf = self.font.render(prefix + msg['Message_Text'], True, text_color)
                    self.screen.blit(msg_surf, (self.sidebar_width + 30, msg_y))
                    msg_y += 35

                color_bg = self.INPUT_ACTIVE if self.input_active else self.INPUT_BG
                pygame.draw.rect(self.screen, color_bg, self.input_rect, border_radius=5)
                pygame.draw.rect(self.screen, self.CYBER_BLUE, self.input_rect, 2, border_radius=5)

                text_surface = self.font.render(self.input_text, True, self.TEXT_COLOR)
                self.screen.blit(text_surface, (self.input_rect.x + 10, self.input_rect.y + 15))

                if self.input_active and time.time() % 1 > 0.5:
                    text_before_cursor = self.input_text[:self.cursor_pos]
                    cursor_offset_x = self.font.size(text_before_cursor)[0]
                    cursor_x = self.input_rect.x + 10 + cursor_offset_x
                    
                    pygame.draw.line(self.screen, self.TEXT_COLOR, (cursor_x, self.input_rect.y + 10), (cursor_x, self.input_rect.y + 40), 2)

                self.send_button.draw(self.screen)
            else:
                empty_msg = self.font.render("Sélectionnez un ami pour afficher la conversation.", True, (150, 150, 150))
                self.screen.blit(empty_msg, empty_msg.get_rect(center=(self.sidebar_width + (self.screen_width - self.sidebar_width) // 2, self.screen_height // 2)))

            pygame.display.flip()
            self.clock.tick(60)