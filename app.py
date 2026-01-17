import customtkinter as ctk
import tkinter as tk  # 우클릭 메뉴(Menu)는 표준 tkinter 사용이 안정적입니다.
from pynput import keyboard
import threading

class TransparencySlider(ctk.CTkToplevel):
    """투명도 조절을 위한 별도의 팝업 창"""
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

        # --- 초기 설정 ---
        self.current_alpha = 0.85
        self.scale_factor = 0.8
        self.base_key_size = 50       
        # ----------------

        self.title("Python Key Overlay")
        self.attributes("-topmost", True)
        self.attributes("-alpha", self.current_alpha) 
        self.overrideredirect(True)                  
        self.configure(fg_color="#1a1a1a")           

        self.bind("<Button-1>", self.start_drag)
        self.bind("<B1-Motion>", self.do_drag)
        
        self.create_context_menu()
        self.bind("<Button-3>", self.show_menu)

        self.buttons = {}
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(padx=10, pady=10)

        self.setup_layout()

        # __init__ 메서드 내 리스너 부분 수정
        self.last_is_extended = False # 확장 키 여부를 저장할 변수

        self.listener = keyboard.Listener(
            on_press=self.on_press, 
            on_release=self.on_release,
            win32_event_filter=self.win32_filter # 윈도우 전용 필터 추가
        )
        self.listener.daemon = True 
        self.listener.start()
    def win32_filter(self, msg, data):
        """
        data.flags의 첫 번째 비트(0x01)가 1이면 확장 키(Extended Key)입니다.
        텐키 엔터, 오른쪽 Alt, 오른쪽 Ctrl 등이 여기에 해당합니다.
        """
        self.last_is_extended = bool(data.flags & 0x01)
        return True # 이벤트가 on_press로 전달되도록 허용

    def create_key(self, parent, text, row, col, width=None, height=None, columnspan=1, rowspan=1, key_code=None):
        k_width = (width if width else self.base_key_size) * self.scale_factor
        k_height = (height if height else self.base_key_size) * self.scale_factor
        
        btn = ctk.CTkButton(
            parent, text=text, width=k_width, height=k_height,
            fg_color="#333333", text_color="white",
            corner_radius=int(6 * self.scale_factor),
            border_width=1, border_color="#444444",
            hover=False, font=("Arial", int(11 * self.scale_factor), "bold")
        )
        btn.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan, padx=2, pady=2, sticky="nsew")
        
        target_key = key_code if key_code else text.lower()
        self.buttons[target_key] = btn
        return btn

    def setup_layout(self):
        """풀 키보드 레이아웃 (스케일 적용)"""
        s = self.base_key_size # 기준 사이즈

        # 1. 펑션 키 영역
        f_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        f_frame.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        # self.create_key(f_frame, "Esc", 0, 0, key_code="esc")
        function_keys = [["Esc"], [1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
        for i in range(len(function_keys)):
            tmp_frame = ctk.CTkFrame(f_frame, fg_color="transparent")
            tmp_frame.grid(row=0, column=1+i, padx=11)
            for key in function_keys[i]:
                if isinstance(key, int):
                    self.create_key(tmp_frame, f"F{key}", 0, key, key_code=f"f{key}")
                else:
                    self.create_key(tmp_frame, "Esc", 0, 0, key_code="esc")

        # 2. 메인 키보드 영역
        m_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        m_frame.grid(row=1, column=0, sticky="n")

        # Row 0: 숫자열
        nums = ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="]
        for i, char in enumerate(nums): self.create_key(m_frame, char, 0, i)
        self.create_key(m_frame, "Back", 0, 13, columnspan=2, key_code="backspace")

        # Row 1: Tab
        self.create_key(m_frame, "Tab", 1, 0, columnspan=2, key_code="tab")
        for i, char in enumerate(["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"]):
            self.create_key(m_frame, char.upper(), 1, i+2, key_code=char)

        # Row 2: Caps
        # self.create_key(m_frame, "Caps", 2, 0, width=s*1.75, columnspan=2, key_code="caps_lock")
        self.create_key(m_frame, "Caps", 2, 0, columnspan=2, key_code="caps_lock")
        for i, char in enumerate(["a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'"]):
            self.create_key(m_frame, char.upper(), 2, i+2, key_code=char)
        self.create_key(m_frame, "Enter", 2, 13, columnspan=2, key_code="enter")

        # Row 3: Shift 줄 (총합 14.5s)
        self.create_key(m_frame, "Shift", 3, 0, columnspan=3, key_code="shift")
        for i, char in enumerate(["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"]):
            self.create_key(m_frame, char, 3, i+3)
        self.create_key(m_frame, "Shift ", 3, 13, columnspan=2, key_code="shift_r")

        # Row 4: 하단 바 (총합 14.5s로 맞춤)
        self.create_key(m_frame, "Ctrl", 4, 0, key_code="ctrl_l")
        self.create_key(m_frame, "Win", 4, 1, key_code="cmd")
        self.create_key(m_frame, "Alt", 4, 2, key_code="alt_l")
        self.create_key(m_frame, "SPACE", 4, 3, columnspan=9, key_code="space") # Space를 7.0으로 확장
        self.create_key(m_frame, "Alt", 4, 12, key_code="alt_gr")
        self.create_key(m_frame, "Ctx", 4, 13, key_code="menu")
        self.create_key(m_frame, "Ctrl", 4, 14, key_code="ctrl_r")

        # 3. 중앙 특수키 및 화살표
        n_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        n_frame.grid(row=1, column=1, sticky="n", padx=10)
        navs = [["insert", "home", "page_up"], ["delete", "end", "page_down"]]
        for r, row in enumerate(navs):
            for c, k in enumerate(row): 
                # k 자체가 pynput 이름과 일치하도록 설정 (예: pu -> page_up)
                self.create_key(n_frame, k[:3].upper(), r, c, key_code=k)
        
        # --- 방향키 영역 (위치 조정) ---
        n_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        n_frame.grid(row=1, column=1, sticky="s", pady=(0, 2)) # 하단 정렬
        # ↑ 키는 한 줄 위(Row 3 위치), ← ↓ → 는 맨 아래(Row 4 위치)
        self.create_key(n_frame, "↑", 0, 1, key_code="up")
        self.create_key(n_frame, "←", 1, 0, key_code="left")
        self.create_key(n_frame, "↓", 1, 1, key_code="down")
        self.create_key(n_frame, "→", 1, 2, key_code="right")

        # 4. 텐키 영역 (Numpad 고유 ID 강제 지정)
        t_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        t_frame.grid(row=1, column=2, sticky="n")

        # 텐키 구조 정의: (표시 텍스트, 매핑될 고유 ID)
        num_keys_config = [
            [("NL", "num_lock"), ("/", "numpad_div"), ("*", "numpad_mul"), ("-", "numpad_sub")],
            [("7", "numpad_7"), ("8", "numpad_8"), ("9", "numpad_9")],
            [("4", "numpad_4"), ("5", "numpad_5"), ("6", "numpad_6")],
            [("1", "numpad_1"), ("2", "numpad_2"), ("3", "numpad_3")]
        ]

        for r, row in enumerate(num_keys_config):
            for c, (text, kid) in enumerate(row):
                self.create_key(t_frame, text, r, c, key_code=kid)

        # 0, ., +, Ent 별도 배치 (ID 확인 필수)
        self.create_key(t_frame, "0", 4, 0, width=self.base_key_size*2, columnspan=2, key_code="numpad_0")
        self.create_key(t_frame, ".", 4, 2, key_code="numpad_dot")
        self.create_key(t_frame, "+", 1, 3, height=self.base_key_size*2, rowspan=2, key_code="numpad_add")
        self.create_key(t_frame, "Ent", 3, 3, height=self.base_key_size*2, rowspan=2, key_code="numpad_enter")

    # --- 우클릭 메뉴 및 기능 ---
    def create_context_menu(self):
        self.menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", borderwidth=0)
        self.menu.add_command(label="  투명도 조절 슬라이더  ", command=self.open_slider_window)
        self.menu.add_command(label="  최소화  ", command=self.iconify)
        self.menu.add_separator()
        self.menu.add_command(label="  종료  ", command=self.destroy)

    def open_slider_window(self):
        TransparencySlider(self)

    def set_transparency(self, value):
        self.current_alpha = value
        self.attributes("-alpha", self.current_alpha)

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def start_drag(self, event):
        self.x = event.x
        self.y = event.y

    def do_drag(self, event):
        self.geometry(f"+{self.winfo_x() + (event.x - self.x)}+{self.winfo_y() + (event.y - self.y)}")

    def on_press(self, key):
        k = self.parse_key(key)
        if k in self.buttons: self.buttons[k].configure(fg_color="#1f538d")

    def on_release(self, key):
        k = self.parse_key(key)
        if k in self.buttons: self.buttons[k].configure(fg_color="#333333")

    def parse_key(self, key):
        try:
            # 1. pynput의 Key Enum 객체인지 확인 (Enter, Shift 등)
            is_special = isinstance(key, keyboard.Key)
            vk = getattr(key, 'vk', None)

            # [핵심 수정] 엔터키 정밀 판별
            # pynput.keyboard.Key.enter 객체와 직접 비교합니다.
            if key == keyboard.Key.enter:
                # win32_filter에서 저장한 확장 플래그(Extended Bit) 확인
                return "numpad_enter" if self.last_is_extended else "enter"

            # 2. 텐키 숫자 및 연산자 (VK 코드 활용)
            # 텐키 숫자는 보통 KeyCode 객체로 들어오며 vk값이 존재합니다.
            vk_numpad_map = {
                96: "numpad_0", 97: "numpad_1", 98: "numpad_2", 99: "numpad_3",
                100: "numpad_4", 101: "numpad_5", 102: "numpad_6", 103: "numpad_7",
                104: "numpad_8", 105: "numpad_9",
                106: "numpad_mul", 107: "numpad_add", 109: "numpad_sub", 
                111: "numpad_div", 110: "numpad_dot",
                144: "num_lock"
            }
            if vk in vk_numpad_map:
                return vk_numpad_map[vk]

            # 3. 오른쪽 특수키 (한/영, 한자 및 확장 Alt/Ctrl)
            if vk == 21 or (key == keyboard.Key.alt_r) or (vk == 18 and self.last_is_extended):
                return "alt_gr"
            if vk == 25 or (key == keyboard.Key.ctrl_r) or (vk == 17 and self.last_is_extended):
                return "ctrl_r"

            # 4. 일반 문자키 (a, s, d, f...)
            if hasattr(key, 'char') and key.char is not None:
                return key.char.lower()

            # 5. 기타 특수키 이름 정리
            key_name = str(key).replace('Key.', '')
            special_map = {
                "page_up": "page_up", "page_down": "page_down",
                "insert": "insert", "home": "home", "delete": "delete",
                "cmd": "cmd", "menu": "menu", "backspace": "backspace",
                "tab": "tab", "caps_lock": "caps_lock", "shift_r": "shift_r"
            }
            return special_map.get(key_name, key_name)

        except Exception:
            return None

if __name__ == "__main__":
    app = FullKeyboardOverlay()
    app.mainloop()