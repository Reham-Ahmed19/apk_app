import time
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.graphics import Color, Ellipse, Line
from kivy.clock import Clock
from kivy.core.window import Window

JUMPS = {
    (1,3): 2, (3,1): 2, (4,6): 5, (6,4): 5,
    (7,9): 8, (9,7): 8, (1,7): 4, (7,1): 4,
    (2,8): 5, (8,2): 5, (3,9): 6, (9,3): 6,
    (1,9): 5, (9,1): 5, (3,7): 5, (7,3): 5
}

def generate_patterns():
    visited = set()
    def dfs(current, path):
        if len(path) >= 4:
            yield list(path)
        if len(path) == 9:
            return
        for nxt in range(1, 10):
            if nxt not in visited:
                jump_node = JUMPS.get((current, nxt))
                if not jump_node or jump_node in visited:
                    visited.add(nxt)
                    path.append(nxt)
                    yield from dfs(nxt, path)
                    path.pop()
                    visited.remove(nxt)
    for start in range(1, 10):
        visited.add(start)
        yield from dfs(start, [start])
        visited.remove(start)

class PatternLockCanvas(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.dot_coords = {}
        self.current_sequence = []
        self.drawn_lines = []
        self.is_drawing = False
        self.active_line_points = []
        self.cracking_state = 'IDLE' 
        self.target_sequence = []
        
        self.dot_color = (0.06, 0.2, 0.38, 1) # #0f3460
        self.active_color = (0, 0.8, 0.79, 1) # #00cec9
        self.success_color = (0.3, 0.69, 0.31, 1) # #4caf50
        
    def update_canvas(self, *args):
        self.draw_grid()
        self.draw_sequence_visuals(self.current_sequence)
        
    def draw_grid(self):
        self.dot_coords.clear()
        w, h = self.size
        min_dim = min(w, h)
        padding = min_dim * 0.1
        spacing = (min_dim - 2 * padding) / 2
        
        offset_x = self.x + (w - min_dim) / 2 + padding
        offset_y = self.y + (h - min_dim) / 2 + padding
        
        self.canvas.clear()
        with self.canvas:
            Color(*self.dot_color)
            dot_radius = min_dim * 0.05
            idx = 1
            for row in range(2, -1, -1):
                for col in range(3):
                    cx = offset_x + col * spacing
                    cy = offset_y + row * spacing
                    self.dot_coords[idx] = (cx, cy)
                    Ellipse(pos=(cx - dot_radius, cy - dot_radius), size=(dot_radius*2, dot_radius*2))
                    idx += 1
                    
    def get_dot_at(self, x, y):
        w, h = self.size
        padding = min(w, h) * 0.1
        for idx, (cx, cy) in self.dot_coords.items():
            if abs(x - cx) <= padding and abs(y - cy) <= padding:
                return idx
        return None
        
    def draw_sequence_visuals(self, sequence, is_success=False, is_error=False):
        self.draw_grid()
        color = self.success_color if is_success else self.active_color
        
        with self.canvas:
            Color(*color)
            if len(sequence) > 1:
                points = []
                for idx in sequence:
                    points.extend(self.dot_coords[idx])
                Line(points=points, width=4)
            if self.active_line_points:
                Line(points=self.active_line_points, width=3)
            w, h = self.size
            dot_radius = min(w, h) * 0.05
            for idx in sequence:
                cx, cy = self.dot_coords[idx]
                Ellipse(pos=(cx - dot_radius, cy - dot_radius), size=(dot_radius*2, dot_radius*2))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): return False
        if self.cracking_state in ['CRACKING', 'CRACKED']: return True
        
        idx = self.get_dot_at(*touch.pos)
        if idx is not None:
            self.is_drawing = True
            self.cracking_state = 'SETTING'
            self.current_sequence = []
            self.add_dot_to_sequence(idx)
            cx, cy = self.dot_coords[idx]
            self.active_line_points = [cx, cy, touch.x, touch.y]
            self.draw_sequence_visuals(self.current_sequence)
            App.get_running_app().update_status()
        return True

    def add_dot_to_sequence(self, idx):
        if idx in self.current_sequence: return
        if self.current_sequence:
            last = self.current_sequence[-1]
            jump_node = JUMPS.get((last, idx))
            if jump_node and jump_node not in self.current_sequence:
                self.current_sequence.append(jump_node)
        self.current_sequence.append(idx)

    def on_touch_move(self, touch):
        if not self.is_drawing: return super().on_touch_move(touch)
        if not self.collide_point(*touch.pos): return True
        
        if self.current_sequence:
            last = self.current_sequence[-1]
            cx, cy = self.dot_coords[last]
            self.active_line_points = [cx, cy, touch.x, touch.y]
            
        idx = self.get_dot_at(*touch.pos)
        if idx is not None:
            self.add_dot_to_sequence(idx)
        self.draw_sequence_visuals(self.current_sequence)
        App.get_running_app().update_status()
        return True

    def on_touch_up(self, touch):
        if not self.is_drawing: return super().on_touch_up(touch)
        self.is_drawing = False
        self.active_line_points = []
        
        app = App.get_running_app()
        if len(self.current_sequence) < 4:
            self.cracking_state = 'IDLE'
            Clock.schedule_once(self.clear_board, 1.0)
            app.sequence_var.text = "Target must be >= 4 dots"
        else:
            self.target_sequence = list(self.current_sequence)
            self.cracking_state = 'READY'
            app.sequence_var.text = f"Target Saved! (Length: {len(self.target_sequence)})"
            app.status_var.text = "Pattern saved. Click Start Cracking."
            app.crack_btn.disabled = False
            Clock.schedule_once(self.clear_board, 1.0)
            
        self.draw_sequence_visuals(self.current_sequence)
        return True

    def clear_board(self, dt):
        if self.cracking_state != 'SETTING':
            self.current_sequence = []
            self.draw_sequence_visuals([])

class PatternLockApp(App):
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.18, 1) # #1a1a2e
        
        root = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        root.add_widget(Label(text="Pattern Brute-Forcer", font_size=30, bold=True, color=(0.91, 0.27, 0.38, 1), size_hint_y=None, height=50))
        self.status_var = Label(text="Draw a pattern to set as the target password", size_hint_y=None, height=40)
        root.add_widget(self.status_var)
        
        stats = BoxLayout(size_hint_y=None, height=40)
        self.attempts_var = Label(text="Attempts: 0")
        self.time_var = Label(text="Elapsed Time: 0.0s")
        stats.add_widget(self.attempts_var)
        stats.add_widget(self.time_var)
        root.add_widget(stats)
        
        self.canvas_widget = PatternLockCanvas(size_hint=(1, 1))
        root.add_widget(self.canvas_widget)
        
        self.sequence_var = Label(text="Waiting for input...", italic=True, size_hint_y=None, height=40)
        root.add_widget(self.sequence_var)
        
        controls = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.crack_btn = Button(text="Start Cracking", disabled=True, background_color=(0.06, 0.2, 0.38, 1))
        self.crack_btn.bind(on_release=self.start_cracking)
        self.reset_btn = Button(text="Reset Target", background_color=(0.91, 0.27, 0.38, 1))
        self.reset_btn.bind(on_release=self.reset_all)
        controls.add_widget(self.crack_btn)
        controls.add_widget(self.reset_btn)
        root.add_widget(controls)
        
        speed_box = BoxLayout(size_hint_y=None, height=40)
        speed_box.add_widget(Label(text="Speed:", size_hint_x=0.2))
        self.speed_slider = Slider(min=1, max=1000, value=10, size_hint_x=0.8)
        speed_box.add_widget(self.speed_slider)
        root.add_widget(speed_box)
        
        self.attempts = 0
        self.start_time = 0
        self.generator_iterator = None
        self.crack_event = None
        
        return root

    def update_status(self):
        seq = self.canvas_widget.current_sequence
        if seq:
            self.sequence_var.text = " - ".join(map(str, seq))

    def reset_all(self, *args):
        self.canvas_widget.cracking_state = 'IDLE'
        self.canvas_widget.target_sequence = []
        self.canvas_widget.current_sequence = []
        self.attempts = 0
        self.canvas_widget.draw_sequence_visuals([])
        
        if self.crack_event:
            self.crack_event.cancel()
        
        self.crack_btn.disabled = True
        self.crack_btn.text = "Start Cracking"
        self.reset_btn.disabled = False
        
        self.attempts_var.text = "Attempts: 0"
        self.time_var.text = "Elapsed Time: 0.0s"
        self.sequence_var.text = "Waiting for input..."
        self.status_var.text = "Draw a pattern to set as the target password"

    def start_cracking(self, *args):
        self.canvas_widget.cracking_state = 'CRACKING'
        self.crack_btn.disabled = True
        self.reset_btn.disabled = True
        
        self.attempts = 0
        self.attempts_var.text = f"Attempts: {self.attempts}"
        self.status_var.text = "Algorithm is guessing..."
        
        self.generator_iterator = generate_patterns()
        self.start_time = time.time()
        
        self.crack_event = Clock.schedule_interval(self.crack_loop, 1/60.0)

    def crack_loop(self, dt):
        if self.canvas_widget.cracking_state != 'CRACKING': 
            return False
            
        elapsed = time.time() - self.start_time
        self.time_var.text = f"Elapsed Time: {elapsed:.1f}s"
            
        speed = int(self.speed_slider.value)
        passes = 5000 if speed >= 1000 else speed
        
        target_str = "".join(map(str, self.canvas_widget.target_sequence))
        found = False
        last_guess = None
        
        for _ in range(passes):
            try:
                guess = next(self.generator_iterator)
                self.attempts += 1
                last_guess = guess
                
                guess_str = "".join(map(str, guess))
                if guess_str == target_str:
                    found = True
                    break
            except StopIteration:
                self.stop_cracking(False)
                return False

        self.attempts_var.text = f"Attempts: {self.attempts:,}"
        
        if found:
            self.stop_cracking(True, last_guess)
            return False
        else:
            if last_guess:
                self.canvas_widget.draw_sequence_visuals(last_guess)
                self.sequence_var.text = " - ".join(map(str, last_guess))
        return True

    def stop_cracking(self, success, final_guess=None):
        self.canvas_widget.cracking_state = 'CRACKED'
        elapsed = time.time() - self.start_time
        self.time_var.text = f"Elapsed Time: {elapsed:.1f}s"
        
        self.reset_btn.disabled = False
        self.crack_btn.disabled = False
        self.crack_btn.text = "Crack Again"
        
        if success:
            self.status_var.text = "Pattern cracked successfully!"
            self.sequence_var.text = "Cracked! " + " - ".join(map(str, self.canvas_widget.target_sequence))
            if final_guess:
                self.canvas_widget.draw_sequence_visuals(final_guess, is_success=True)
        else:
            self.status_var.text = "Failed to crack target."

if __name__ == "__main__":
    PatternLockApp().run()
