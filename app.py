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

        # --- [해상도 설정 프리셋] ---
        self.modes = {
            "full": {"w": 1031, "h": 276, "name": "풀 배열 (104키)"},
            "tkl": {"w": 853, "h": 276, "name": "텐키리스 (87키)"}
        }
        self.current_mode = "full"
        
        # --- 초기 상태 설정 ---
        self.current_alpha = 0.85
        self.scale_factor = 1.0  # 오리지널 사이즈 기준 1.0
        self.base_key_size = 42  # 276px 높이에 최적화된 키 사이즈
        self.resizing = False
        self.resize_edge = None
        
        # 초기 창 크기 설정 (풀 배열 기준)
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
        self.set_initial_aspect_ratio()

        # 키보드 리스너
        self.last_is_extended = False 
        self.listener = keyboard.Listener(
            on_press=self.on_press, 
            on_release=self.on_release,
            win32_event_filter=self.win32_filter
        )
        self.listener.daemon = True 
        self.listener.start()

    def set_initial_aspect_ratio(self):
        self.update_idletasks()
        self.aspect_ratio = self.winfo_width() / self.winfo_height()

    def create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", borderwidth=0)
        
        # 레이아웃 선택 메뉴 추가
        layout_menu = tk.Menu(self.context_menu, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d")
        layout_menu.add_command(label="  풀 배열 (Numpad)  ", command=lambda: self.switch_layout("full"))
        layout_menu.add_command(label="  텐키리스 (TKL)  ", command=lambda: self.switch_layout("tkl"))
        
        self.context_menu.add_cascade(label="  레이아웃 변경  ", menu=layout_menu)
        self.context_menu.add_command(label="  투명도 조절  ", command=self.open_slider_window)
        self.context_menu.add_command(label="  최소화  ", command=self.iconify)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  종료  ", command=self.destroy)

    def switch_layout(self, mode_key):
        """풀 배열 <-> 텐키리스 전환 로직"""
        self.current_mode = mode_key
        mode = self.modes[mode_key]
        
        # 1. 창 크기 및 배율 초기화
        self.geometry(f"{mode['w']}x{mode['h']}")
        self.scale_factor = 1.0
        self.update_idletasks()
        
        # 2. 종횡비 재설정
        self.aspect_ratio = mode['w'] / mode['h']
        
        # 3. UI 재그리기
        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.buttons = {}
        self.setup_layout()

    # --- 리사이즈 로직 (종횡비 고정) ---
    def check_edge(self, event):
        if self.resizing: return
        x, y = event.x, event.y
        w, h = self.winfo_width(), self.winfo_height()
        m = 15 
        edge = None
        if (y < m or y > h - m) and (x < m or x > w - m): edge = "corner"
        elif y < m or y > h - m: edge = "ns"
        elif x < m or x > w - m: edge = "we"
        
        self.resize_edge = edge
        if edge == "corner": self.config(cursor="size_nw_se")
        elif edge == "ns": self.config(cursor="size_ns")
        elif edge == "we": self.config(cursor="size_we")
        else: self.config(cursor="")

    def on_button_press(self, event):
        if self.resize_edge:
            self.resizing = True
            self.start_x, self.start_y = event.x_root, event.y_root
            self.start_geom = (self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())
        else:
            self.start_drag_x, self.start_drag_y = event.x, event.y

    def on_button_release(self, event):
        if self.resizing:
            self.resizing = False
            # 리사이즈 후의 너비를 기준으로 새로운 scale_factor 계산
            base_w = self.modes[self.current_mode]['w']
            self.scale_factor = self.winfo_width() / base_w
            self.refresh_ui()

    def handle_mouse_action(self, event):
        if self.resizing:
            orig_x, orig_y, orig_w, orig_h = self.start_geom
            dx = event.x_root - self.start_x
            dy = event.y_root - self.start_y
            
            # 주축 결정 및 종횡비 적용
            if abs(dx) > abs(dy * self.aspect_ratio):
                new_w = max(400, orig_w + dx if event.x_root > self.start_x else orig_w - dx)
                new_h = new_w / self.aspect_ratio
            else:
                new_h = max(150, orig_h + dy if event.y_root > self.start_y else orig_h - dy)
                new_w = new_h * self.aspect_ratio

            # 방향 보정
            new_x, new_y = orig_x, orig_y
            if event.x_root < self.start_x and self.resize_edge in ["corner", "we"]:
                new_x = orig_x - (new_w - orig_w)
            if event.y_root < self.start_y and self.resize_edge in ["corner", "ns"]:
                new_y = orig_y - (new_h - orig_h)
            
            self.geometry(f"{int(new_w)}x{int(new_h)}+{int(new_x)}+{int(new_y)}")
        else:
            self.geometry(f"+{self.winfo_x() + (event.x - self.start_drag_x)}+{self.winfo_y() + (event.y - self.start_drag_y)}")

    # --- 레이아웃 생성 ---
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
        # 1. 펑션 키 (F1~F12)
        f_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        f_frame.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))
        f_keys = [["Esc"], [1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
        for i, group in enumerate(f_keys):
            tmp = ctk.CTkFrame(f_frame, fg_color="transparent")
            tmp.pack(side="left", padx=int(8 * self.scale_factor))
            for idx, key in enumerate(group):
                k_text = f"F{key}" if isinstance(key, int) else key
                self.create_key(tmp, k_text, 0, idx, key_code=k_text.lower())

        # 2. 메인 쿼티 영역
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
        self.create_key(m_frame, "SPACE", 4, 3, width=s*6.5, columnspan=7, key_code="space")
        self.create_key(m_frame, "Alt", 4, 10, width=s*1.3, key_code="alt_gr")
        self.create_key(m_frame, "Ctx", 4, 11, width=s*1.3, key_code="menu")
        self.create_key(m_frame, "Ctrl", 4, 12, width=s*1.3, key_code="ctrl_r")

        # 3. 특수키 및 방향키 (TKL 및 풀배열 공통)
        n_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        n_frame.grid(row=1, column=1, sticky="n", padx=int(10 * self.scale_factor))
        navs = [["insert", "home", "page_up"], ["delete", "end", "page_down"]]
        for r, row in enumerate(navs):
            for c, k in enumerate(row): self.create_key(n_frame, k[:3].upper(), r, c, key_code=k)
        
        a_frame = ctk.CTkFrame(n_frame, fg_color="transparent")
        a_frame.grid(row=2, column=0, columnspan=3, pady=(s*0.5, 0))
        self.create_key(a_frame, "↑", 0, 1, key_code="up")
        self.create_key(a_frame, "←", 1, 0, key_code="left")
        self.create_key(a_frame, "↓", 1, 1, key_code="down")
        self.create_key(a_frame, "→", 1, 2, key_code="right")

        # 4. 텐키 영역 (풀배열 모드에서만 생성)
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

    # --- 키보드 이벤트 로직 ---
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