import customtkinter as ctk
import tkinter as tk
from pynput import keyboard

class TransparencySlider(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("설정")
        self.geometry("250x100")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        
        self.label = ctk.CTkLabel(self, text=f"투명도 조절: {int(parent.current_alpha * 100)}%")
        self.label.pack(pady=(10, 0))

        self.slider = ctk.CTkSlider(self, from_=0.1, to=1.0, command=self.update_alpha)
        self.slider.set(parent.current_alpha)
        self.slider.pack(pady=10, padx=20)

    def update_alpha(self, value):
        self.parent.set_transparency(value)
        self.label.configure(text=f"투명도 조절: {int(value * 100)}%")

class FullKeyboardOverlay(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- [해상도 및 제한 설정] ---
        self.modes = {
            "full": {"w": 1090, "h": 276, "name": "풀 배열 (104키)"},
            "tkl": {"w": 900, "h": 276, "name": "텐키리스 (87키)"}
        }
        self.current_mode = "full"
        
        # 키보드 레이아웃이 깨지지 않는 최소 너비 설정
        self.min_width_limit = 660 
        
        self.current_alpha = 0.85
        self.scale_factor = 1.0
        self.base_key_size = 42
        self.resizing = False
        self.resize_edge = None
        
        # 초기 창 크기 및 종횡비 설정
        mode = self.modes[self.current_mode]
        self.geometry(f"{mode['w']}x{mode['h']}")
        
        self.title("Python Key Overlay")
        self.attributes("-topmost", True)
        self.attributes("-alpha", self.current_alpha) 
        self.overrideredirect(True)                  
        self.configure(fg_color="#1a1a1a")           

        self.context_menu = None
        self.create_context_menu()

        self.bind("<Button-3>", self.show_menu)
        self.bind("<Motion>", self.check_edge)
        self.bind("<ButtonPress-1>", self.on_button_press)
        self.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<B1-Motion>", self.handle_mouse_action)

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both", padx=5, pady=5)

        self.buttons = {}
        self.setup_layout()
        
        # 초기 종횡비 저장
        self.update_idletasks()
        self.aspect_ratio = self.winfo_width() / self.winfo_height()

        # 키보드 리스너
        self.last_is_extended = False 
        self.listener = keyboard.Listener(
            on_press=self.on_press, 
            on_release=self.on_release,
            win32_event_filter=self.win32_filter
        )
        self.listener.daemon = True 
        self.listener.start()

    def create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", borderwidth=0)
        
        layout_menu = tk.Menu(self.context_menu, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d")
        layout_menu.add_command(label="  풀 배열 (Numpad)  ", command=lambda: self.switch_layout("full"))
        layout_menu.add_command(label="  텐키리스 (TKL)  ", command=lambda: self.switch_layout("tkl"))
        
        self.context_menu.add_cascade(label="  레이아웃 변경  ", menu=layout_menu)
        self.context_menu.add_command(label="  투명도 조절  ", command=self.open_slider_window)
        self.context_menu.add_command(label="  최소화  ", command=self.iconify)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  종료  ", command=self.destroy)

    def switch_layout(self, mode_key):
        self.current_mode = mode_key
        mode = self.modes[mode_key]
        self.geometry(f"{mode['w']}x{mode['h']}")
        self.scale_factor = 1.0
        self.update_idletasks()
        self.aspect_ratio = mode['w'] / mode['h']
        
        # 모드에 따른 최소 너비 유동적 조정
        self.min_width_limit = 1200 if mode_key == "full" else 900
        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.buttons = {}
        self.setup_layout()

    def check_edge(self, event):
        if self.resizing: return

        # [수정] 현재 마우스 위치에 있는 위젯 확인
        # 버튼(키) 위에서는 리사이징 모드가 활성화되지 않도록 필터링
        target = self.winfo_containing(event.x_root, event.y_root)
        
        # 마우스 아래에 버튼(또는 버튼 내부 구성요소)이 있다면 리사이징 무시
        if target != self and target != self.main_frame and target is not None:
            self.resize_edge = None
            self.config(cursor="")
            return

        x, y = event.x, event.y
        w, h = self.winfo_width(), self.winfo_height()
        m = 15 
        
        at_top = y < m
        at_bottom = y > h - m
        at_left = x < m
        at_right = x > w - m

        if at_top and at_left: self.resize_edge = "nw"; self.config(cursor="size_nw_se")
        elif at_top and at_right: self.resize_edge = "ne"; self.config(cursor="size_ne_sw")
        elif at_bottom and at_left: self.resize_edge = "sw"; self.config(cursor="size_ne_sw")
        elif at_bottom and at_right: self.resize_edge = "se"; self.config(cursor="size_nw_se")
        elif at_top: self.resize_edge = "n"; self.config(cursor="size_ns")
        elif at_bottom: self.resize_edge = "s"; self.config(cursor="size_ns")
        elif at_left: self.resize_edge = "w"; self.config(cursor="size_we")
        elif at_right: self.resize_edge = "e"; self.config(cursor="size_we")
        else: self.resize_edge = None; self.config(cursor="")

    def on_button_press(self, event):
        if self.resize_edge:
            self.resizing = True
            self.start_x_root = event.x_root
            self.start_y_root = event.y_root
            self.start_geom = (self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())
        else:
            self.start_drag_x = event.x
            self.start_drag_y = event.y

    def on_button_release(self, event):
        if self.resizing:
            self.resizing = False
            base_w = self.modes[self.current_mode]['w']
            self.scale_factor = self.winfo_width() / base_w * 0.99
            self.refresh_ui()

    def handle_mouse_action(self, event):
        if self.resizing:
            orig_x, orig_y, orig_w, orig_h = self.start_geom
            dx = event.x_root - self.start_x_root
            dy = event.y_root - self.start_y_root
            
            # 1. 드래그 방향에 따른 너비 변화량 계산
            if "e" in self.resize_edge: 
                raw_w = orig_w + dx
            elif "w" in self.resize_edge: 
                raw_w = orig_w - dx
            else: # 상하 드래그 기반 너비 유추
                raw_h = orig_h + dy if "s" in self.resize_edge else orig_h - dy
                raw_w = raw_h * self.aspect_ratio

            # 2. [핵심] 최소 너비 제한 적용 (Clamping)
            new_w = max(self.min_width_limit, raw_w)
            new_h = new_w / self.aspect_ratio
            
            # 3. 좌표 보정 (고정점 기준)
            new_x, new_y = orig_x, orig_y
            if "w" in self.resize_edge: new_x = orig_x + (orig_w - new_w)
            if "n" in self.resize_edge: new_y = orig_y + (orig_h - new_h)
            
            self.geometry(f"{int(new_w)}x{int(new_h)}+{int(new_x)}+{int(new_y)}")
        else:
            self.geometry(f"+{self.winfo_x() + (event.x - self.start_drag_x)}+{self.winfo_y() + (event.y - self.start_drag_y)}")

    def create_key(self, parent, text, row, col, width=None, height=None, columnspan=1, rowspan=1, key_code=None):
        k_w = (width if width else self.base_key_size) * self.scale_factor
        k_h = (height if height else self.base_key_size) * self.scale_factor
        btn = ctk.CTkButton(parent, text=text, width=k_w, height=k_h, fg_color="#333333", 
                            text_color="white", corner_radius=int(4*self.scale_factor), 
                            font=("Arial", int(11*self.scale_factor), "bold"), hover=False)
        btn.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan, padx=1, pady=1, sticky="nsew")
        self.buttons[key_code if key_code else text.lower()] = btn

    def setup_layout(self):
        s = self.base_key_size
        f_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        f_frame.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))
        f_keys = [["Esc"], [1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
        for i, group in enumerate(f_keys):
            tmp = ctk.CTkFrame(f_frame, fg_color="transparent")
            if i == 0:  # ESC key
                tmp.pack(side="left", padx=0)
            else:
                tmp.pack(side="left", padx=(int(50 * self.scale_factor), 0))
            for idx, key in enumerate(group):
                k_text = f"F{key}" if isinstance(key, int) else key
                self.create_key(tmp, k_text, 0, idx, key_code=k_text.lower())

        m_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        m_frame.grid(row=1, column=0, sticky="n")
        
        nums = ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="]
        for i, char in enumerate(nums): self.create_key(m_frame, char, 0, i)
        self.create_key(m_frame, "Back", 0, 13, width=s*2, columnspan=2, key_code="backspace")

        self.create_key(m_frame, "Tab", 1, 0, width=s*1.5, columnspan=2, key_code="tab")
        for i, char in enumerate(["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"]):
            self.create_key(m_frame, char.upper(), 1, i+2, key_code=char)

        self.create_key(m_frame, "Caps", 2, 0, width=s*1.8, columnspan=2, key_code="caps_lock")
        for i, char in enumerate(["a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'"]):
            self.create_key(m_frame, char.upper(), 2, i+2, key_code=char)
        self.create_key(m_frame, "Enter", 2, 13, width=s*1.8, columnspan=2, key_code="enter")

        self.create_key(m_frame, "Shift", 3, 0, width=s*2.3, columnspan=3, key_code="shift")
        for i, char in enumerate(["z", "x", "c", "v", "b", "n", "m", ",", ".", "/"]):
            self.create_key(m_frame, char.upper(), 3, i+3, key_code=char)
        self.create_key(m_frame, "Shift ", 3, 13, width=s*2.3, columnspan=2, key_code="shift_r")

        self.create_key(m_frame, "Ctrl", 4, 0, width=s*1.3, key_code="ctrl_l")
        self.create_key(m_frame, "Win", 4, 1, width=s*1.3, key_code="cmd")
        self.create_key(m_frame, "Alt", 4, 2, width=s*1.3, key_code="alt_l")
        self.create_key(m_frame, "SPACE", 4, 3, width=s*6.5, columnspan=9, key_code="space")
        self.create_key(m_frame, "Alt", 4, 12, width=s*1.3, key_code="alt_gr")
        self.create_key(m_frame, "Ctx", 4, 13, width=s*1.3, key_code="menu")
        self.create_key(m_frame, "Ctrl", 4, 14, width=s*1.3, key_code="ctrl_r")

        n_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        n_frame.grid(row=1, column=1, sticky="n", padx=int(10 * self.scale_factor))
        navs = [["insert", "home", "page_up"], ["delete", "end", "page_down"]]
        for r, row in enumerate(navs):
            for c, k in enumerate(row): self.create_key(n_frame, k[:3].upper(), r, c, key_code=k)
        
        a_frame = ctk.CTkFrame(n_frame, fg_color="transparent")
        a_frame.grid(row=2, column=0, columnspan=3, pady=(s, 0))
        self.create_key(a_frame, "↑", 0, 1, key_code="up")
        self.create_key(a_frame, "←", 1, 0, key_code="left")
        self.create_key(a_frame, "↓", 1, 1, key_code="down")
        self.create_key(a_frame, "→", 1, 2, key_code="right")

        if self.current_mode == "full":
            t_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            t_frame.grid(row=1, column=2, sticky="n")
            num_map = [[("NL", "num_lock"), ("/", "numpad_div"), ("*", "numpad_mul"), ("-", "numpad_sub")],
                       [("7", "numpad_7"), ("8", "numpad_8"), ("9", "numpad_9")],
                       [("4", "numpad_4"), ("5", "numpad_5"), ("6", "numpad_6")],
                       [("1", "numpad_1"), ("2", "numpad_2"), ("3", "numpad_3")]]
            for r, row in enumerate(num_map):
                for c, (txt, kid) in enumerate(row): self.create_key(t_frame, txt, r, c, key_code=kid)
            self.create_key(t_frame, "0", 4, 0, width=s*2, columnspan=2, key_code="numpad_0")
            self.create_key(t_frame, ".", 4, 2, key_code="numpad_dot")
            self.create_key(t_frame, "+", 1, 3, height=s*2, rowspan=2, key_code="numpad_add")
            self.create_key(t_frame, "Ent", 3, 3, height=s*2, rowspan=2, key_code="numpad_enter")

    def win32_filter(self, msg, data):
        self.last_is_extended = bool(data.flags & 0x01)
        return True

    def on_press(self, key):
        k = self.parse_key(key)
        if k in self.buttons: self.buttons[k].configure(fg_color="#1f538d")
    def on_release(self, key):
        k = self.parse_key(key)
        if k in self.buttons: self.buttons[k].configure(fg_color="#333333")

    def parse_key(self, key):
        try:
            vk = getattr(key, 'vk', None)
            if key == keyboard.Key.enter: return "numpad_enter" if self.last_is_extended else "enter"
            vk_map = {96:"numpad_0", 97:"numpad_1", 98:"numpad_2", 99:"numpad_3", 100:"numpad_4",
                      101:"numpad_5", 102:"numpad_6", 103:"numpad_7", 104:"numpad_8", 105:"numpad_9",
                      106:"numpad_mul", 107:"numpad_add", 109:"numpad_sub", 111:"numpad_div", 110:"numpad_dot", 144:"num_lock"}
            if vk in vk_map: return vk_map[vk]
            if vk == 21 or key == keyboard.Key.alt_r or (vk == 18 and self.last_is_extended): return "alt_gr"
            if vk == 25 or key == keyboard.Key.ctrl_r or (vk == 17 and self.last_is_extended): return "ctrl_r"
            if hasattr(key, 'char') and key.char: return key.char.lower()
            return str(key).replace('Key.', '').lower()
        except: return None

    def open_slider_window(self): TransparencySlider(self)
    def set_transparency(self, value):
        self.current_alpha = value
        self.attributes("-alpha", value)
    def show_menu(self, event): self.context_menu.post(event.x_root, event.y_root)

if __name__ == "__main__":
    app = FullKeyboardOverlay()
    app.mainloop()