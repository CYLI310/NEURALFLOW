import pygame
import requests
import random
import json
import math

# --- CONFIGURATION ---
WIDTH, HEIGHT = 800, 600
FPS = 60

class LevelArchitect:
    def __init__(self):
        self.url = "http://localhost:11434/api/generate"
        self.available_models = []
        self.model = "mistral"
        self.online = True
        self.check_connection()
        self.refresh_available_models()

    def check_connection(self):
        try:
            requests.get("http://localhost:11434/api/tags", timeout=1)
            self.online = True
        except:
            self.online = False

    def refresh_available_models(self):
        if not self.online:
            return
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [m['name'] for m in data.get('models', [])]
                if self.available_models and self.model not in self.available_models:
                    self.model = self.available_models[0]
        except:
            self.available_models = ["mistral", "gemma3"] # Fallbacks

    def generate_level(self, theme, mode):
        default_level = {
            "palette": {"bg": [20, 20, 30], "lane": [50, 50, 50], "note": [0, 255, 255], "hit": [255, 255, 255]},
            "speed": 8,
            "bpm": 120,
            "name": "Offline Protocol",
            "introtext": "CRITICAL ERROR: Connection to the main neural network has been severed. Defaulting to local rhythm protocols.",
            "flavor_text": "Local simulation active."
        }

        if not self.online:
            return default_level

        mode_desc = {
            "2K": "2 vertical lanes (Left, Right)",
            "4K": "4 vertical lanes (D, F, J, K)",
            "OSU": "Random circle positions on screen (x: 0-800, y: 0-600)"
        }

        prompt = f"""
        You are a music engine. Create a JSON config for a rhythm game level.
        Theme: '{theme}'
        Game Mode: '{mode}' ({mode_desc.get(mode)})

        Rules:
        1. 'speed': integer 6-12. (For OSU, this is circle shrink speed)
        2. 'bpm': integer 80-160.
        3. 'palette': RGB colors for bg, lane, note, hit.
        4. 'introtext': A long-form cinematic introduction to this specific world (2-3 sentences).
        5. 'flavor_text': A short atmospheric description.

        Output ONLY raw JSON:
        {{
            "palette": {{ "bg": [r,g,b], "lane": [r,g,b], "note": [r,g,b], "hit": [r,g,b] }},
            "speed": 8,
            "bpm": 128,
            "name": "World Name",
            "introtext": "The great servers once hummed with life...",
            "flavor_text": "Cryptic flavor here."
        }}
        """
        try:
            print(f"Requesting '{theme}' universe from Ollama ({self.model})...")
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            
            response = requests.post(self.url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            raw_text = result.get("response", "")
            
            # JSON cleaning
            start = raw_text.find('{')
            end = raw_text.rfind('}') + 1
            if start != -1 and end != -1:
                raw_text = raw_text[start:end]
            
            level_data = json.loads(raw_text)
            print(f"Universe synchronized: {level_data.get('name', 'Untitled')}")
            return level_data
        except Exception as e:
            print(f"Ollama generation failed: {e}")
            return default_level

# --- GAME ENGINE ---
class RhythmGame:
    def __init__(self):
        pygame.init()
        global WIDTH, HEIGHT
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("NEURALFLOW: AI Rhythm")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 24)
        self.big_font = pygame.font.SysFont("Consolas", 72, bold=True)
        self.title_font = pygame.font.SysFont("Consolas", 100, bold=True)
        
        self.architect = LevelArchitect()
        
        self.notes = [] 
        self.particles = []
        self.menu_particles = [] # Background ambiance
        for _ in range(50):
            self.menu_particles.append([random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(0.5, 2)])

        self.score = 0
        self.combo = 0
        self.hp = 100
        self.max_hp = 100
        self.running = True
        self.state = "EPILEPSY" # EPILEPSY, TITLE, MENU, INPUT, LOADING, INTRO, COUNTDOWN, GAME, SETTINGS, DEATH
        
        # Timers & Vfx
        self.intro_timer = 0
        self.countdown_val = 3
        self.shake_timer = 0
        self.shake_intensity = 0
        
        # Menu Navigation
        self.menu_options = ["NEW FLOW", "SETTINGS", "EXIT"]
        self.selected_option = 0
        
        self.modes = ["2K", "4K", "OSU"]
        self.mode_index = 0
        self.active_mode = "2K"
        
        # New: Model selection index
        self.model_index = 0
        
        # OSU logic
        self.osu_cursor = pygame.Vector2(WIDTH//2, HEIGHT//2)
        
        # Keys for 4K
        self.lane_keys = [pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k]
        self.lane_pressed = [False] * 4

        # Gameplay Settings
        self.user_speed = 8 # Default scroll speed

        # Judgments
        self.judgment = ""
        self.judgment_timer = 0
        self.judgment_color = (255, 255, 255)
        
        # Input State
        self.left_pressed = False
        self.right_pressed = False
        
        # Level & Rhythmic State
        self.current_theme = ""
        self.level_data = None
        self.input_text = ""
        self.start_time = 0
        self.last_beat_spawned = -1
        self.bpm = 120
        self.beat_interval = 60 / self.bpm

    def trigger_shake(self, intensity=5, duration=10):
        self.shake_intensity = intensity
        self.shake_timer = duration

    def spawn_note(self, current_time):
        elapsed = current_time - self.start_time
        target_beat = int(elapsed / self.beat_interval) + 2 
        
        if target_beat > self.last_beat_spawned:
            target_time = self.start_time + (target_beat * self.beat_interval)
            
            if self.active_mode == "2K":
                lane = random.choice([0, 1])
                x = WIDTH * 0.35 if lane == 0 else WIDTH * 0.65
                self.notes.append({"x": x, "y": 0, "lane": lane, "active": True, "target_time": target_time})
            elif self.active_mode == "4K":
                lane = random.choice([0, 1, 2, 3])
                x = WIDTH * (0.2 + lane * 0.2)
                self.notes.append({"x": x, "y": 0, "lane": lane, "active": True, "target_time": target_time})
            elif self.active_mode == "OSU":
                x = random.randint(100, WIDTH - 100)
                y = random.randint(150, HEIGHT - 150)
                self.notes.append({"x": x, "y": y, "active": True, "target_time": target_time})
                
            self.last_beat_spawned = target_beat

    def create_particles(self, x, y, color):
        for _ in range(10):
            self.particles.append({
                "x": x, "y": y,
                "vx": random.uniform(-5, 5), "vy": random.uniform(-5, 5),
                "life": 20, "color": color
            })

    def check_hit(self, lane=None, is_osu=False):
        current_time = pygame.time.get_ticks() / 1000.0
        hit_tolerance = 0.2
        hit_made = False
        
        for note in self.notes:
            if not note['active']: continue
            
            valid_input = False
            if is_osu:
                mouse_pos = pygame.mouse.get_pos()
                dist_px = math.sqrt((mouse_pos[0]-note['x'])**2 + (mouse_pos[1]-note['y'])**2)
                if dist_px < 50: valid_input = True
            else:
                if note['lane'] == lane: valid_input = True
                
            if valid_input:
                dist = abs(current_time - note['target_time'])
                if dist < hit_tolerance:
                    note['active'] = False
                    
                    if dist < 0.05: self.judgment, self.judgment_color, self.score = "PERFECT", (0, 255, 255), self.score + 200 + (self.combo * 20)
                    elif dist < 0.10: self.judgment, self.judgment_color, self.score = "GREAT", (0, 255, 100), self.score + 100 + (self.combo * 10)
                    else: self.judgment, self.judgment_color, self.score = "GOOD", (255, 255, 100), self.score + 50 + (self.combo * 5)
                        
                    self.combo += 1
                    self.judgment_timer = 30
                    self.create_particles(note['x'], note.get('y', HEIGHT - 120), self.level_data['palette']['hit'])
                    hit_made = True
                    break
        
        if not hit_made and not is_osu: # Osu misses are handled in update
            self.combo = 0
            self.hp -= 2
            self.judgment, self.judgment_color, self.judgment_timer = "MISS", (255, 50, 50), 20

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            
            # --- SHAKE TIMER UPDATE (Global) ---
            if self.shake_timer > 0:
                self.shake_timer -= 1
            else:
                self.shake_intensity = 0

            # --- INPUT HANDLING ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if event.type == pygame.VIDEORESIZE:
                    global WIDTH, HEIGHT
                    WIDTH, HEIGHT = event.w, event.h
                    self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                    self.menu_particles = []
                    for _ in range(50):
                        self.menu_particles.append([random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(0.5, 2)])
                    self.state = "MENU"
                    self.trigger_shake(5, 30)

                elif self.state == "EPILEPSY":
                    if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                        self.state = "TITLE"
                        self.trigger_shake(8, 15) # 0.25s

                elif self.state == "TITLE":
                    if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                        self.state = "MENU"
                        self.trigger_shake(5, 15)

                elif self.state == "MENU":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_UP:
                            self.selected_option = (self.selected_option - 1) % len(self.menu_options)
                            self.trigger_shake(2, 15)
                        elif event.key == pygame.K_DOWN:
                            self.selected_option = (self.selected_option + 1) % len(self.menu_options)
                            self.trigger_shake(2, 15)
                        elif event.key == pygame.K_RETURN:
                            self.trigger_shake(8, 15)
                            if self.selected_option == 0: self.state = "INPUT"
                            elif self.selected_option == 1: self.state = "SETTINGS"
                            elif self.selected_option == 2: self.running = False

                elif self.state == "INPUT":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN and self.input_text:
                            self.trigger_shake(10, 15)
                            self.current_theme = self.input_text
                            self.state = "LOADING"
                        elif event.key == pygame.K_ESCAPE:
                            self.trigger_shake(3, 15)
                            self.state = "MENU"
                        elif event.key == pygame.K_BACKSPACE:
                            self.input_text = self.input_text[:-1]
                        else:
                            self.input_text += event.unicode

                elif self.state == "SETTINGS":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE: 
                            self.trigger_shake(3, 8)
                            self.state = "MENU"
                        if event.key == pygame.K_1: 
                            self.trigger_shake(4, 10)
                            if self.architect.available_models:
                                self.model_index = (self.model_index + 1) % len(self.architect.available_models)
                                self.architect.model = self.architect.available_models[self.model_index]
                        if event.key == pygame.K_m: 
                            self.trigger_shake(4, 10)
                            self.mode_index = (self.mode_index + 1) % len(self.modes)
                            self.active_mode = self.modes[self.mode_index]
                        if event.key == pygame.K_s:
                            self.trigger_shake(4, 10)
                            self.user_speed = (self.user_speed % 12) + 1 # Cycle 1-12

                elif self.state == "DEATH":
                    if event.type == pygame.KEYDOWN:
                        self.trigger_shake(12, 15)
                        self.state = "MENU"
                        self.score = 0
                        self.combo = 0
                        self.hp = 100

                elif self.state == "GAME":
                    if event.type == pygame.KEYDOWN:
                        if self.active_mode == "2K":
                            if event.key in [pygame.K_LEFT, pygame.K_a]: self.left_pressed = True; self.check_hit(0)
                            if event.key in [pygame.K_RIGHT, pygame.K_d]: self.right_pressed = True; self.check_hit(1)
                        elif self.active_mode == "4K":
                            for i, k in enumerate(self.lane_keys):
                                if event.key == k: self.lane_pressed[i] = True; self.check_hit(i)
                        elif self.active_mode == "OSU":
                            if event.key in [pygame.K_z, pygame.K_x]: self.check_hit(is_osu=True)
                    
                    if event.type == pygame.MOUSEBUTTONDOWN and self.active_mode == "OSU":
                        self.check_hit(is_osu=True)

                    if event.type == pygame.KEYUP:
                        if self.active_mode == "2K":
                            if event.key in [pygame.K_LEFT, pygame.K_a]: self.left_pressed = False
                            if event.key in [pygame.K_RIGHT, pygame.K_d]: self.right_pressed = False
                        elif self.active_mode == "4K":
                            for i, k in enumerate(self.lane_keys):
                                if event.key == k: self.lane_pressed[i] = False

            # --- LOGIC UPDATES ---
            if self.state == "EPILEPSY":
                self.draw_epilepsy_warning()
            elif self.state == "TITLE":
                self.draw_title()
            elif self.state == "MENU":
                self.draw_menu()
            elif self.state == "SETTINGS":
                self.draw_settings()
            elif self.state == "INPUT":
                self.draw_input()
            elif self.state == "LOADING":
                self.draw_loading()
                self.level_data = self.architect.generate_level(self.current_theme, self.active_mode)
                self.bpm = self.level_data.get('bpm', 120)
                self.beat_interval = 60 / self.bpm
                self.intro_timer = pygame.time.get_ticks()
                self.state = "INTRO"
            
            elif self.state == "INTRO":
                self.draw_intro()
                if pygame.time.get_ticks() - self.intro_timer > 4000: # 4 seconds of intro
                    self.intro_timer = pygame.time.get_ticks()
                    self.state = "COUNTDOWN"

            elif self.state == "COUNTDOWN":
                self.draw_countdown()
                elapsed = pygame.time.get_ticks() - self.intro_timer
                self.countdown_val = 3 - int(elapsed / 1000)
                if self.countdown_val <= 0:
                    self.start_time = pygame.time.get_ticks() / 1000.0
                    self.last_beat_spawned = -1
                    self.state = "GAME"

            elif self.state == "GAME":
                self.update_game()
                self.draw_game()
                
            elif self.state == "DEATH":
                self.draw_death()

            # Final composition with shake
            if self.shake_timer > 0:
                shake_x = random.randint(-self.shake_intensity, self.shake_intensity)
                shake_y = random.randint(-self.shake_intensity, self.shake_intensity)
                temp_surface = self.screen.copy()
                self.screen.fill((0, 0, 0))
                self.screen.blit(temp_surface, (shake_x, shake_y))

            pygame.display.flip()
        pygame.quit()

    def update_game(self):
        current_time = pygame.time.get_ticks() / 1000.0
        self.spawn_note(current_time)
        
        # Use user_speed for 2K/4K, or level speed for OSU (shrink speed)
        speed_val = self.user_speed if self.active_mode != "OSU" else self.level_data['speed']
        speed_multiplier = speed_val * 100
        hit_y = HEIGHT - 120
        
        # Update Notes
        for note in self.notes:
            if not note['active']: continue
            
            if self.active_mode != "OSU":
                note['y'] = hit_y + (current_time - note['target_time']) * speed_multiplier
            
            # Miss detection
            if current_time > note['target_time'] + (0.1 if self.active_mode == "OSU" else 0.2):
                note['active'] = False
                self.hp -= 10
                self.combo = 0
                self.judgment, self.judgment_color, self.judgment_timer = "MISS", (255, 50, 50), 20
        
        # Cleanup
        self.notes = [n for n in self.notes if (n.get('y', 0) < HEIGHT + 50) or (current_time < n['target_time'] + 1)]

        for p in self.particles:
            p['x'] += p['vx']; p['y'] += p['vy']; p['life'] -= 1
        self.particles = [p for p in self.particles if p['life'] > 0]

        if self.judgment_timer > 0: self.judgment_timer -= 1
        
        if self.hp <= 0:
            self.state = "DEATH"
            self.notes = []
            self.particles = []

    # --- DRAWING ---
    def draw_epilepsy_warning(self):
        self.screen.fill((0, 0, 0))
        t1 = self.big_font.render("EPILEPSY WARNING", True, (255, 50, 50))
        
        warning_lines = [
            "This game contains flashing lights, rapid patterns,",
            "and high-contrast visuals that may trigger hardware",
            "or photosensitive seizures for some individuals.",
            "",
            "Player discretion is advised.",
            "",
            "PRESS ANY KEY TO PROCEED"
        ]
        
        self.screen.blit(t1, (WIDTH//2 - t1.get_width()//2, HEIGHT//4))
        
        for i, line in enumerate(warning_lines):
            color = (200, 200, 200) if "PROCEED" not in line else (0, 255, 255)
            lt = self.font.render(line, True, color)
            self.screen.blit(lt, (WIDTH//2 - lt.get_width()//2, HEIGHT//2 - 20 + i*30))

    def draw_background_ambiance(self):
        self.screen.fill((5, 5, 10))
        for p in self.menu_particles:
            p[1] += p[2]
            if p[1] > HEIGHT: p[1] = 0
            pygame.draw.circle(self.screen, (30, 30, 60), (int(p[0]), int(p[1])), 2)
        
        # Scanlines (Global)
        for y in range(0, HEIGHT, 4):
            pygame.draw.line(self.screen, (0, 0, 0, 30), (0, y), (WIDTH, y))

    def draw_title(self):
        self.draw_background_ambiance()
        t = pygame.time.get_ticks() * 0.002
        glow_val = abs(math.sin(t)) * 100 + 155
        
        title = self.title_font.render("NEURALFLOW", True, (0, glow_val, glow_val))
        sub = self.font.render("PRESS ANY KEY TO START", True, (150, 150, 150))
        
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 50))
        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 80))

    def draw_menu(self):
        self.draw_background_ambiance()
        title = self.big_font.render("[[LAUNCH]]", True, (255, 255, 255))
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))

        for i, option in enumerate(self.menu_options):
            is_selected = (i == self.selected_option)
            color = (0, 255, 255) if is_selected else (100, 100, 100)
            
            # Draw the option text centered
            txt = self.font.render(option, True, color)
            x_pos = WIDTH//2 - txt.get_width()//2
            y_pos = 300 + i * 70
            
            if is_selected:
                # Highlight Box
                box_w = 350
                pygame.draw.rect(self.screen, (10, 30, 30), (WIDTH//2 - box_w//2, y_pos - 10, box_w, 45))
                pygame.draw.rect(self.screen, (0, 255, 255), (WIDTH//2 - box_w//2, y_pos - 10, box_w, 45), 1)
                # Centered prefix that doesn't shift text
                prefix = self.font.render(">>", True, (0, 255, 255))
                self.screen.blit(prefix, (WIDTH//2 - box_w//2 + 20, y_pos))

            self.screen.blit(txt, (x_pos, y_pos))

    def draw_settings(self):
        self.draw_background_ambiance()
        title = self.big_font.render("SYSTEM CONFIG", True, (200, 200, 200))
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
        
        y_start = 200
        # AI Model
        model_title = self.font.render("[AI MODEL - PRESS 1 TO CYCLE]", True, (150, 150, 150))
        self.screen.blit(model_title, (WIDTH//2 - model_title.get_width()//2, y_start))
        
        models = self.architect.available_models if self.architect.available_models else ["Searching..."]
        for i, mid in enumerate(models):
            is_active = (self.architect.model == mid)
            color = (0, 255, 150) if is_active else (80, 80, 80)
            prefix_str = ">> " if is_active else "   "
            txt = self.font.render(prefix_str + mid, True, color)
            self.screen.blit(txt, (WIDTH//2 - 150, y_start + 50 + i*35))

        # Game Mode
        mode_y = HEIGHT - 200
        mode_title = self.font.render("[GAME MODE - PRESS M]", True, (150, 150, 150))
        self.screen.blit(mode_title, (WIDTH//2 - mode_title.get_width()//2, mode_y))
        
        for i, m in enumerate(self.modes):
            is_active = (self.active_mode == m)
            color = (255, 100, 255) if is_active else (80, 80, 80)
            txt = self.font.render(m, True, color)
            spacing = 150
            x_pos = WIDTH//2 - (len(self.modes)*spacing)//2 + i*spacing + spacing//4
            if is_active:
                pygame.draw.rect(self.screen, color, (x_pos - 10, mode_y + 45, txt.get_width() + 20, 30), 1)
            self.screen.blit(txt, (x_pos, mode_y + 50))

        # Scroll Speed
        if self.active_mode != "OSU":
            speed_y = mode_y - 80
            speed_title = self.font.render(f"[SCROLL SPEED - PRESS S]: {self.user_speed}", True, (255, 200, 100))
            self.screen.blit(speed_title, (WIDTH//2 - speed_title.get_width()//2, speed_y))
            # Speed bar
            bar_w = 300
            pygame.draw.rect(self.screen, (40, 40, 40), (WIDTH//2 - bar_w//2, speed_y + 35, bar_w, 10))
            pygame.draw.rect(self.screen, (255, 200, 100), (WIDTH//2 - bar_w//2, speed_y + 35, int((self.user_speed/12) * bar_w), 10))

        hint = self.font.render("ESC TO RETURN", True, (100, 100, 100))
        self.screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 60))

    def draw_death(self):
        self.draw_background_ambiance()
        t = self.big_font.render("CONNECTION LOST", True, (255, 50, 50))
        res = self.font.render(f"FINAL SCORE: {self.score}", True, (255, 255, 255))
        hint = self.font.render("PRESS ANY KEY TO REBOOT", True, (100, 100, 100))
        
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 50))
        self.screen.blit(res, (WIDTH//2 - res.get_width()//2, HEIGHT//2 + 50))
        self.screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 100))

    def draw_input(self):
        self.draw_background_ambiance()
        sub = self.font.render("ENTER ATMOSPHERIC VIBE", True, (100, 100, 120))
        inp_box = pygame.Rect(WIDTH//2 - 200, 300, 400, 50)
        pygame.draw.rect(self.screen, (20, 20, 30), inp_box)
        pygame.draw.rect(self.screen, (0, 255, 255), inp_box, 2)
        
        inp = self.font.render(self.input_text + ("_" if pygame.time.get_ticks() // 500 % 2 == 0 else ""), True, (255, 255, 255))
        self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 250))
        self.screen.blit(inp, (WIDTH//2 - inp.get_width()//2, 310))

    def draw_loading(self):
        self.screen.fill((0, 0, 0))
        t = self.font.render("SYNCHRONIZING WITH AI...", True, (0, 255, 150))
        pygame.draw.rect(self.screen, (0, 255, 150), (WIDTH//4, HEIGHT//2 + 40, (pygame.time.get_ticks() % 1000) / 1000 * (WIDTH//2), 5))
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))

    def draw_intro(self):
        p = self.level_data['palette']
        self.draw_background_ambiance()
        self.screen.fill(p['bg'], special_flags=pygame.BLEND_RGB_ADD)
        
        name_t = self.big_font.render(self.level_data.get('name', 'UNKNOWN'), True, p['note'])
        self.screen.blit(name_t, (WIDTH//2 - name_t.get_width()//2, HEIGHT//4))
        
        intro_text = self.level_data.get('introtext', '')
        # Simple word wrap for intro
        words = intro_text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            if self.font.size(current_line + word)[0] < WIDTH - 100:
                current_line += word + " "
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)

        for i, line in enumerate(lines):
            lt = self.font.render(line, True, (200, 200, 200))
            self.screen.blit(lt, (WIDTH//2 - lt.get_width()//2, HEIGHT//2 + i*30))
        
        skip_h = self.font.render("TRANSMISSION IN PROGRESS...", True, (100, 100, 100))
        self.screen.blit(skip_h, (WIDTH//2 - skip_h.get_width()//2, HEIGHT - 80))

    def draw_countdown(self):
        p = self.level_data['palette']
        self.draw_game() # Draw the board underneath
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0,0))
        
        count_t = self.title_font.render(str(self.countdown_val), True, p['hit'])
        self.screen.blit(count_t, (WIDTH//2 - count_t.get_width()//2, HEIGHT//2 - count_t.get_height()//2))

    def draw_game(self):
        p = self.level_data['palette']
        self.screen.fill(p['bg'])
        current_time = pygame.time.get_ticks() / 1000.0

        # Draw Dynamic Background
        time_t = pygame.time.get_ticks() * 0.001
        for i in range(10):
            y_pos = (abs(i * 100 + time_t * 50) % HEIGHT)
            pygame.draw.line(self.screen, [max(0, c-40) for c in p['lane']], (0, y_pos), (WIDTH, y_pos), 1)

        hit_y = HEIGHT - 120

        if self.active_mode in ["2K", "4K"]:
            num_lanes = 2 if self.active_mode == "2K" else 4
            for i in range(num_lanes):
                lane_x = WIDTH * (0.35 if self.active_mode == "2K" else 0.2) + (i * WIDTH * (0.3 if self.active_mode == "2K" else 0.2))
                
                # Lane Glow
                is_pressed = (i == 0 and self.left_pressed) or (i == 1 and self.right_pressed) if self.active_mode == "2K" else self.lane_pressed[i]
                if is_pressed:
                    s = pygame.Surface((100, HEIGHT), pygame.SRCALPHA)
                    pygame.draw.rect(s, (*p['hit'], 40), (0, 0, 100, HEIGHT))
                    self.screen.blit(s, (lane_x - 50, 0))
                
                pygame.draw.line(self.screen, p['lane'], (lane_x, 0), (lane_x, HEIGHT), 2)
                pygame.draw.circle(self.screen, (255, 255, 255, 100), (int(lane_x), hit_y), 45, 2)

        # Notes
        for note in self.notes:
            if not note['active']: continue
            
            if self.active_mode == "OSU":
                # Circle shrinking logic
                time_diff = note['target_time'] - current_time
                if time_diff > 0:
                    radius = 30 + (time_diff * 100)
                    pygame.draw.circle(self.screen, p['note'], (int(note['x']), int(note['y'])), 40, 3)
                    pygame.draw.circle(self.screen, p['hit'], (int(note['x']), int(note['y'])), int(radius), 2)
            else:
                # Vertical notes
                for i in range(1, 4):
                    pygame.draw.circle(self.screen, (*p['note'], 50), (int(note['x']), int(note['y'])), 25 + i*2, 1)
                pygame.draw.circle(self.screen, p['note'], (int(note['x']), int(note['y'])), 25)
                pygame.draw.circle(self.screen, (255, 255, 255), (int(note['x']), int(note['y'])), 10)

        # Particles
        for part in self.particles:
            pygame.draw.circle(self.screen, part['color'], (int(part['x']), int(part['y'])), random.randint(1, 4))

        # Judgment
        if self.judgment_timer > 0:
            j_surf = self.big_font.render(self.judgment, True, self.judgment_color)
            j_surf.set_alpha(min(255, self.judgment_timer * 12))
            self.screen.blit(j_surf, (WIDTH//2 - j_surf.get_width()//2, HEIGHT//2))

        # UI Panel
        pygame.draw.rect(self.screen, (10, 10, 20), (0, 0, WIDTH, 80))
        pygame.draw.line(self.screen, p['lane'], (0, 80), (WIDTH, 80), 2)

        score_t = self.font.render(f"SCORE: {self.score:06}", True, (255, 255, 255))
        combo_t = self.big_font.render(f"{self.combo}", True, (255, 255, 255))
        pygame.draw.rect(self.screen, (40, 40, 60), (20, 45, 200, 15))
        pygame.draw.rect(self.screen, (0, 255, 150) if self.hp > 30 else (255, 50, 50), (20, 45, int(self.hp * 2), 15))
        
        elapsed = current_time - self.start_time
        beat_progress = (elapsed % self.beat_interval) / self.beat_interval
        metro_color = p['note'] if beat_progress < 0.1 else (50, 50, 50)
        pygame.draw.circle(self.screen, metro_color, (WIDTH//2, 60), 10)

        name_t = self.font.render(f"{self.level_data.get('name', 'UNKNOWN')} [{self.active_mode}]", True, p['note'])
        self.screen.blit(score_t, (20, 15)); self.screen.blit(combo_t, (WIDTH - combo_t.get_width() - 20, 5)); self.screen.blit(name_t, (WIDTH//2 - name_t.get_width()//2, 15))

if __name__ == "__main__":
    game = RhythmGame()
    game.run()