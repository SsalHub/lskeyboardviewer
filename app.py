import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from pynput import keyboard
from PIL import Image
import os
import json

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

class ImageSelectionPopup(ctk.CTkToplevel):
    """파일 이름 대신 이미지 썸네일 버튼을 보여주는 팝업 창"""
    def __init__(self, parent, key_id):
        super().__init__(parent)
        self.parent = parent
        self.key_id = key_id
        self.title(f"이미지 선택 - [{key_id.upper()}]")
        self.geometry("450x550")
        
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set() 
        
        self.resource_path = "./resource/char/"
        self.thumbnail_images = []
        
        if not os.path.exists(self.resource_path):
            os.makedirs(self.resource_path)

        self.label = ctk.CTkLabel(self, text="바인딩할 캐릭터 이미지를 선택하세요", font=("Arial", 14, "bold"))
        self.label.pack(pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=420, height=400)
        self.scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.load_thumbnails()

        self.remove_btn = ctk.CTkButton(self, text="이미지 제거 (텍스트 모드)", fg_color="#A12F2F", 
                                        hover_color="#822525", command=self.remove_binding)
        self.remove_btn.pack(pady=15)

    def _on_mousewheel(self, event):
        speed_multiplier = 2
        scroll_units = int(-1 * (event.delta / 120) * speed_multiplier)
        self.scroll_frame._parent_canvas.yview_scroll(scroll_units, "units")

    def load_thumbnails(self):
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
        files = [f for f in os.listdir(self.resource_path) if f.lower().endswith(valid_extensions)]

        if not files:
            lbl = ctk.CTkLabel(self.scroll_frame, text="이미지가 없습니다.\n./resource/char/ 폴더를 확인하세요.")
            lbl.pack(pady=50)
            return

        cols = 3
        for i, file in enumerate(files):
            file_path = os.path.join(self.resource_path, file)
            try:
                pil_img = Image.open(file_path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(80, 80))
                self.thumbnail_images.append(ctk_img)
                btn = ctk.CTkButton(self.scroll_frame, text="", image=ctk_img, width=100, height=100,
                                    fg_color="#2b2b2b", hover_color="#3d3d3d",
                                    command=lambda p=file_path: self.select_image(p))
                btn.grid(row=i // cols, column=i % cols, padx=10, pady=10)
            except: pass

    def select_image(self, path):
        self.parent.bind_image_to_key(self.key_id, path)
        self.destroy()

    def remove_binding(self):
        self.parent.bind_image_to_key(self.key_id, None)
        self.destroy()

    def destroy(self):
        self.unbind_all("<MouseWheel>")
        super().destroy()

class SaveConfirmDialog(ctk.CTkToplevel):
    """편집 모드 종료 시 4가지 선택지를 제공하는 커스텀 다이얼로그"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("편집 모드 종료")
        self.geometry("400x200")
        self.attributes("-topmost", True)
        self.grab_set()
        self.resizable(False, False)
        self.result = None

        label = ctk.CTkLabel(self, text="변경된 설정을 저장하시겠습니까?", font=("Arial", 14, "bold"))
        label.pack(pady=20)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(btn_frame, text="저장", width=80, command=lambda: self.set_result("save")).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="다른 이름으로 저장", width=120, command=lambda: self.set_result("save_as")).grid(row=0, column=1, padx=5)
        ctk.CTkButton(btn_frame, text="저장 안 함", width=80, fg_color="#A12F2F", hover_color="#822525", command=lambda: self.set_result("no")).grid(row=1, column=0, padx=5, pady=10)
        ctk.CTkButton(btn_frame, text="취소", width=80, fg_color="#555555", hover_color="#444444", command=lambda: self.set_result("cancel")).grid(row=1, column=1, padx=5, pady=10)

        btn_frame.columnconfigure((0,1), weight=1)

    def set_result(self, res):
        self.result = res
        self.destroy()

class FullKeyboardOverlay(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- [해상도 및 제한 설정] ---
        self.modes = {
            "full": {"w": 1090, "h": 276, "name": "풀 배열 (104키)"},
            "tkl": {"w": 900, "h": 276, "name": "텐키리스 (87키)"}
        }
        self.current_mode = "full"
        self.min_width_limit = 720 
        
        self.current_alpha = 0.85
        self.pre_edit_alpha = 0.85 
        self.scale_factor_w = 0.97
        self.scale_factor = 1.0 * self.scale_factor_w
        self.base_key_size = 42
        
        self.edit_mode = False
        self.config_file = "./config.json"
        self.key_bindings = self.load_config(self.config_file)
        self.image_popup = None
        
        self.resizing = False
        self.resize_edge = None
        
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
        
        self.update_idletasks()
        self.aspect_ratio = self.winfo_width() / self.winfo_height()

        self.last_is_extended = False 
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release, win32_event_filter=self.win32_filter)
        self.listener.daemon = True 
        self.listener.start()

    def load_config(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

    def save_config(self, filename=None):
        target = filename if filename else self.config_file
        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(self.key_bindings, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            messagebox.showerror("저장 오류", f"설정을 저장하지 못했습니다: {e}")
            return False

    def save_config_as(self):
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filename:
            return self.save_config(filename)
        return False

    def load_config_dialog(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filename:
            self.key_bindings = self.load_config(filename)
            self.refresh_ui()

    def create_context_menu(self):
        if self.context_menu: self.context_menu.destroy()
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", borderwidth=0)
        
        bmode_full = "> " if self.current_mode == "full" else "   "
        bmode_tkl = "> " if self.current_mode == "tkl" else "   "
        bedit = "종료 (Exit)" if self.edit_mode else "실행 (Enter)"
        
        self.context_menu.add_command(label=f"  {bmode_full}풀 배열 (Full Layout)  ", command=lambda: self.switch_layout("full"))
        self.context_menu.add_command(label=f"  {bmode_tkl}텐키리스 (TKL Layout)  ", command=lambda: self.switch_layout("tkl"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label=f"  편집 모드 {bedit}  ", command=self.toggle_edit_mode)
        self.context_menu.add_command(label="  설정 저장하기  ", command=self.save_config)
        self.context_menu.add_command(label="  다른 이름으로 설정 저장하기...  ", command=self.save_config_as)
        self.context_menu.add_command(label="  설정 불러오기...  ", command=self.load_config_dialog)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  투명도 조절  ", command=self.open_slider_window)
        self.context_menu.add_command(label="  최소화  ", command=self.iconify)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  종료  ", command=self.destroy)

    def toggle_edit_mode(self):
        """편집 모드 전환 및 타이틀 바 표시 로직"""
        if self.edit_mode:
            dialog = SaveConfirmDialog(self)
            self.wait_window(dialog)
            ans = dialog.result
            
            if ans == "save": self.save_config()
            elif ans == "save_as": 
                if not self.save_config_as(): return 
            elif ans == "cancel": return
            
            # 타이틀바 숨기기 및 원래 상태 복구
            self.withdraw()
            self.overrideredirect(True)
            self.set_transparency(self.pre_edit_alpha)
            self.configure(fg_color="#1a1a1a")
            self.deiconify()
        else:
            # 편집 모드 진입: 타이틀바 보이기, 투명도 100%, 배경색 변경
            self.withdraw()
            self.pre_edit_alpha = self.current_alpha
            self.overrideredirect(False)
            self.title("편집 모드 실행 중")
            self.set_transparency(1.0)
            self.configure(fg_color="#2a1a1a")
            self.deiconify()

        self.edit_mode = not self.edit_mode
        self.refresh_ui()

    def bind_image_to_key(self, key_id, path):
        if path: self.key_bindings[key_id] = path
        else: self.key_bindings.pop(key_id, None)
        self.refresh_ui()

    def switch_layout(self, mode_key):
        self.current_mode = mode_key
        mode = self.modes[mode_key]
        self.geometry(f"{mode['w']}x{mode['h']}")
        self.scale_factor = 1.0 * self.scale_factor_w
        self.update_idletasks()
        self.aspect_ratio = self.winfo_width() / self.winfo_height()
        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.buttons = {}
        self.setup_layout()

    def check_edge(self, event):
        if self.resizing: return
        target = self.winfo_containing(event.x_root, event.y_root)
        if target != self and target != self.main_frame and target is not None:
            self.resize_edge = None; self.config(cursor=""); return
        x, y = event.x, event.y
        w, h = self.winfo_width(), self.winfo_height()
        m = 15 
        at_top, at_bottom = y < m, y > h - m
        at_left, at_right = x < m, x > w - m
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
            self.start_x_root, self.start_y_root = event.x_root, event.y_root
            self.start_geom = (self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())
        else:
            self.start_drag_x = event.x
            self.start_drag_y = event.y

    def on_button_release(self, event):
        if self.resizing:
            self.resizing = False
            base_w = self.modes[self.current_mode]['w']
            self.scale_factor = self.winfo_width() / base_w * self.scale_factor_w
            self.refresh_ui()

    def handle_mouse_action(self, event):
        if self.resizing:
            orig_x, orig_y, orig_w, orig_h = self.start_geom
            dx, dy = event.x_root - self.start_x_root, event.y_root - self.start_y_root
            if "e" in self.resize_edge: raw_w = orig_w + dx
            elif "w" in self.resize_edge: raw_w = orig_w - dx
            else:
                raw_h = orig_h + dy if "s" in self.resize_edge else orig_h - dy
                raw_w = raw_h * self.aspect_ratio
            new_w = max(self.min_width_limit, raw_w)
            new_h = new_w / self.aspect_ratio
            new_x, new_y = orig_x, orig_y
            if "w" in self.resize_edge: new_x = orig_x + (orig_w - new_w)
            if "n" in self.resize_edge: new_y = orig_y + (orig_h - new_h)
            self.geometry(f"{int(new_w)}x{int(new_h)}+{int(new_x)}+{int(new_y)}")
        else:
            self.geometry(f"+{self.winfo_x() + (event.x - self.start_drag_x)}+{self.winfo_y() + (event.y - self.start_drag_y)}")

    def create_key(self, parent, text, row, col, width=None, height=None, columnspan=1, rowspan=1, key_code=None):
        k_w = (width if width else self.base_key_size) * self.scale_factor
        k_h = (height if height else self.base_key_size) * self.scale_factor
        target_id = key_code if key_code else text.lower()
        display_text = text
        img_obj = None

        if target_id in self.key_bindings:
            try:
                raw_img = Image.open(self.key_bindings[target_id])
                img_obj = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(k_w * 0.8, k_h * 0.8))
                display_text = ""
            except: pass

        cmd = (lambda tid=target_id: self.open_image_selection(tid)) if self.edit_mode else None
        btn = ctk.CTkButton(parent, text=display_text, image=img_obj, width=k_w, height=k_h, fg_color="#333333", 
                            text_color="white", corner_radius=int(4*self.scale_factor), 
                            font=("Arial", int(11*self.scale_factor), "bold"), hover=self.edit_mode, command=cmd)
        btn.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan, padx=1, pady=1, sticky="nsew")
        self.buttons[target_id] = btn

    def open_image_selection(self, key_id):
        if self.image_popup is not None and self.image_popup.winfo_exists():
            self.image_popup.lift(); return
        self.image_popup = ImageSelectionPopup(self, key_id)

    def setup_layout(self):
        s = self.base_key_size
        content_cols = 3 if self.current_mode == "full" else 2
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(content_cols + 1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        f_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        f_frame.grid(row=1, column=1, columnspan=content_cols, sticky="w", pady=(0, 5))
        f_keys = [["Esc"], [1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
        for i, group in enumerate(f_keys):
            tmp = ctk.CTkFrame(f_frame, fg_color="transparent")
            tmp.pack(side="left", padx=0 if i == 0 else (int(54 * self.scale_factor), 0))
            for idx, key in enumerate(group):
                k_text = f"F{key}" if isinstance(key, int) else key
                self.create_key(tmp, k_text, 0, idx, key_code=k_text.lower())

        m_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        m_frame.grid(row=2, column=1, sticky="n")
        nums = ["`","1","2","3","4","5","6","7","8","9","0","-","="]
        for i, char in enumerate(nums): self.create_key(m_frame, char, 0, i)
        self.create_key(m_frame, "Back", 0, 13, width=s*2, columnspan=2, key_code="backspace")
        self.create_key(m_frame, "Tab", 1, 0, width=s*1.5, columnspan=2, key_code="tab")
        for i, char in enumerate(["q","w","e","r","t","y","u","i","o","p","[","]","\\"]):
            self.create_key(m_frame, char.upper(), 1, i+2, key_code=char)
        self.create_key(m_frame, "Caps", 2, 0, width=s*1.8, columnspan=2, key_code="caps_lock")
        for i, char in enumerate(["a","s","d","f","g","h","j","k","l",";","'"]):
            self.create_key(m_frame, char.upper(), 2, i+2, key_code=char)
        self.create_key(m_frame, "Enter", 2, 13, width=s*1.8, columnspan=2, key_code="enter")
        self.create_key(m_frame, "Shift", 3, 0, width=s*2.3, columnspan=2, key_code="shift")
        for i, char in enumerate(["z","x","c","v","b","n","m",",",".","/"]):
            self.create_key(m_frame, char.upper(), 3, i+2, key_code=char)
        self.create_key(m_frame, "Shift ", 3, 12, width=s*2.3, columnspan=3, key_code="shift_r")
        self.create_key(m_frame, "Ctrl", 4, 0, width=s*1.3, key_code="ctrl_l")
        self.create_key(m_frame, "Win", 4, 1, width=s*1.3, key_code="cmd")
        self.create_key(m_frame, "Alt", 4, 2, width=s*1.3, key_code="alt_l")
        self.create_key(m_frame, "SPACE", 4, 3, width=s*6.5, columnspan=9, key_code="space")
        self.create_key(m_frame, "Alt", 4, 12, width=s*1.3, key_code="alt_gr")
        self.create_key(m_frame, "Ctx", 4, 13, width=s*1.3, key_code="menu")
        self.create_key(m_frame, "Ctrl", 4, 14, width=s*1.3, key_code="ctrl_r")

        n_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        n_frame.grid(row=2, column=2, sticky="n", padx=int(10 * self.scale_factor))
        navs = [["insert", "home", "page_up"], ["delete", "end", "page_down"]]
        for r, row in enumerate(navs):
            for c, k in enumerate(row): self.create_key(n_frame, k[:3].upper(), r, c, key_code=k)
        a_frame = ctk.CTkFrame(n_frame, fg_color="transparent")
        a_frame.grid(row=2, column=0, columnspan=3, pady=(s*self.scale_factor, 0))
        self.create_key(a_frame, "↑", 0, 1, key_code="up")
        self.create_key(a_frame, "←", 1, 0, key_code="left")
        self.create_key(a_frame, "↓", 1, 1, key_code="down")
        self.create_key(a_frame, "→", 1, 2, key_code="right")

        if self.current_mode == "full":
            t_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            t_frame.grid(row=2, column=3, sticky="n")
            num_map = [[("NL","num_lock"),("/","numpad_div"),("*","numpad_mul"),("-","numpad_sub")],
                       [("7","numpad_7"),("8","numpad_8"),("9","numpad_9")],
                       [("4","numpad_4"),("5","numpad_5"),("6","numpad_6")],
                       [("1","numpad_1"),("2","numpad_2"),("3","numpad_3")]]
            for r, row in enumerate(num_map):
                for c, (txt, kid) in enumerate(row): self.create_key(t_frame, txt, r, c, key_code=kid)
            self.create_key(t_frame, "0", 4, 0, width=s*2, columnspan=2, key_code="numpad_0")
            self.create_key(t_frame, ".", 4, 2, key_code="numpad_dot")
            self.create_key(t_frame, "+", 1, 3, height=s*2, rowspan=2, key_code="numpad_add")
            self.create_key(t_frame, "Ent", 3, 3, height=s*2, rowspan=2, key_code="numpad_enter")

    def win32_filter(self, msg, data):
        self.last_is_extended = bool(data.flags & 0x01); return True

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
        self.current_alpha = value; self.attributes("-alpha", value)
    def show_menu(self, event):
        self.create_context_menu(); self.context_menu.post(event.x_root, event.y_root)

if __name__ == "__main__":
    app = FullKeyboardOverlay(); app.mainloop()