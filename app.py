import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from pynput import keyboard
from PIL import Image
import os
import json
import configparser

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
    """개별 키 편집용 이미지 선택 팝업"""
    def __init__(self, parent, key_id):
        super().__init__(parent)
        self.parent = parent
        self.key_id = key_id
        self.title(f"이미지 선택 - [{key_id.upper()}]")
        self.geometry("450x550")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set() 
        
        self.resource_path = "./resource/img/"
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
        # [안내] 여기서 speed_multiplier 값을 수정하여 스크롤 속도를 조절하세요.
        speed_multiplier = 100
        scroll_units = int(-1 * (event.delta / 120) * speed_multiplier)
        self.scroll_frame._parent_canvas.yview_scroll(scroll_units, "units")

    def load_thumbnails(self):
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
        files = [f for f in os.listdir(self.resource_path) if f.lower().endswith(valid_extensions)]
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

class ImageGalleryPopup(ctk.CTkToplevel):
    """용병 슬롯 전용 이미지 갤러리 팝업 - Enter 키 검색 및 검색 버튼 추가 버전"""
    def __init__(self, parent, target_slot_key, callback):
        super().__init__(parent)
        self.parent = parent
        self.target_slot_key = target_slot_key
        self.callback = callback 
        self.title("캐릭터 검색 및 선택")
        self.geometry("450x650") 
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        self.resource_path = "./resource/img/"
        self.json_path = "./resource/char_data.json"
        
        # 1. 캐릭터 데이터 로드
        self.char_data = self.load_char_data()
        self.thumbnail_buttons = {} 

        # 2. 검색창 레이아웃 구성
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(pady=10, padx=20, fill="x")

        # 검색 입력창: Enter 키(<Return>) 이벤트 바인딩
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="번호, 이름, 줄임말, 초성 검색...", font=("Arial", 12))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.search_entry.bind("<Return>", self.on_search) 

        # 검색 버튼 추가
        self.search_btn = ctk.CTkButton(search_frame, text="검색", width=60, command=self.on_search)
        self.search_btn.pack(side="left")

        # 팝업이 열린 후 검색창에 자동 포커스
        self.after(200, lambda: self.search_entry.focus_set())

        # 3. 이미지 출력 영역
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=410, height=450)
        self.scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.load_thumbnails()

        # 4. 하단 제거 버튼
        self.remove_btn = ctk.CTkButton(self, text="이미지 제거 (텍스트 모드)", fg_color="#A12F2F", 
                                        hover_color="#822525", command=self.remove_binding)
        self.remove_btn.pack(pady=15)

    def _on_mousewheel(self, event):
        speed_multiplier = 100
        scroll_units = int(-1 * (event.delta / 120) * speed_multiplier)
        self.scroll_frame._parent_canvas.yview_scroll(scroll_units, "units")

    def load_char_data(self):
        """외부 JSON 파일에서 캐릭터 정보를 읽어옵니다."""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"JSON 로드 오류: {e}")
        return {}

    def load_thumbnails(self):
        """초기 모든 이미지를 로드하여 버튼을 생성하되, 화면에는 보이지 않게 설정합니다."""
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
        # 이미지 폴더 내 파일 리스트 (숫자 기준 정렬)
        try:
            files = sorted([f for f in os.listdir(self.resource_path) if f.lower().endswith(valid_extensions)], 
                           key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else 999)
        except FileNotFoundError:
            print(f"오류: {self.resource_path} 경로를 찾을 수 없습니다.")
            return

        for file in files:
            char_id = os.path.splitext(file)[0] # 파일명을 ID로 사용
            file_path = os.path.join(self.resource_path, file)
            try:
                pil_img = Image.open(file_path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(80, 80))
                
                btn = ctk.CTkButton(self.scroll_frame, text="", image=ctk_img, width=100, height=100,
                                    fg_color="#2b2b2b", hover_color="#3d3d3d",
                                    command=lambda p=file_path: self.confirm_selection(p))
                
                # 검색용 데이터와 버튼 객체 매핑
                self.thumbnail_buttons[char_id] = btn
            except: pass
        
        # 처음에는 전체 표시
        self.update_gallery("")

    def confirm_selection(self, path):
        """이미지 선택 완료"""
        self.callback(self.target_slot_key, path)
        self.destroy()

    def remove_binding(self):
        """이미지 제거 요청 처리"""
        self.unbind_all("<MouseWheel>")
        self.callback(self.target_slot_key, None) 
        self.destroy()

    def on_search(self, event=None):
        """검색어 입력 시(Enter) 또는 검색 버튼 클릭 시 갤러리를 업데이트합니다."""
        query = self.search_entry.get().strip().lower()
        self.update_gallery(query)

    def update_gallery(self, query):
        """검색어에 따라 버튼을 필터링하여 다시 배치합니다."""
        # 1. 기존 그리드 초기화 (객체는 파괴하지 않음)
        for btn in self.thumbnail_buttons.values():
            btn.grid_forget()

        # 2. 필터링 로직
        filtered_ids = []
        if not query:
            filtered_ids = list(self.thumbnail_buttons.keys())
        else:
            for cid, info in self.char_data.items():
                # ID 일치, 이름 포함, 줄임말 포함, 초성 포함 여부 확인
                if (query == cid or 
                    query in info.get("name", "").lower() or 
                    any(query in abbr.lower() for abbr in info.get("abbr", [])) or 
                    query in info.get("chosung", "")):
                    if cid in self.thumbnail_buttons:
                        filtered_ids.append(cid)

        # 3. 필터링된 버튼만 다시 배치 (3열 배치)
        cols = 3
        for i, cid in enumerate(filtered_ids):
            self.thumbnail_buttons[cid].grid(row=i // cols, column=i % cols, padx=10, pady=10)

    def destroy(self):
        self.unbind_all("<MouseWheel>")
        super().destroy()

class InGameKeyConfigPopup(ctk.CTkToplevel):
    """SOLDIER 1~50 설정 창 - 부분 재생성 최적화 버전"""
    def __init__(self, parent, soldier_data):
        super().__init__(parent)
        self.parent = parent
        self.soldier_data = soldier_data
        self.title("용병 설정 - 로스트사가")
        self.geometry("650x550")
        self.attributes("-topmost", True)
        
        # 슬롯 정보를 저장할 딕셔너리 (프레임 참조 및 위치 저장)
        self.slot_containers = {} 

        ctk.CTkLabel(self, text="슬롯을 클릭하여 이미지를 지정하세요", font=("Arial", 16, "bold")).pack(pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=800, height=550)
        self.scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.setup_slots()

    def _on_mousewheel(self, event):
        speed_multiplier = 100
        scroll_units = int(-1 * (event.delta / 120) * speed_multiplier)
        self.scroll_frame._parent_canvas.yview_scroll(scroll_units, "units")

    def setup_slots(self):
        """전체 슬롯 초기 생성"""
        cols = 6
        for i in range(1, 51):
            row = (i-1)//cols
            col = (i-1)%cols
            self.create_single_slot(i, row, col)

    def create_single_slot(self, index, row, col):
        """[핵심] 특정 위치에 단일 슬롯 프레임과 버튼을 생성합니다."""
        s_id = f"SOLDIER{index}"
        raw_val = self.soldier_data.get(s_id, "0")
        key_id = get_lostsaga_key_name(raw_val)
        target_key = key_id.lower()
        
        # 1. 개별 슬롯을 담을 프레임 생성
        slot_frame = ctk.CTkFrame(self.scroll_frame, width=120, height=140, fg_color="#333333")
        slot_frame.grid(row=row, column=col, padx=5, pady=5)
        slot_frame.grid_propagate(False)

        display_name = key_id.replace("numpad_", "NUM ").upper()
        ctk.CTkLabel(slot_frame, text=f"{s_id}\n({display_name})", font=("Arial", 10)).pack(pady=5)

        # 2. 이미지 로드 및 참조 유지
        img_path = self.parent.key_bindings.get(target_key)
        display_img = None
        if img_path and os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                display_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(60, 60))
            except: pass

        # 3. 버튼 생성
        btn = ctk.CTkButton(slot_frame, 
                            text="+" if not display_img else "", 
                            image=display_img, 
                            width=80, height=80,
                            fg_color="#262626", hover_color="#404040",
                            command=lambda k=key_id: self.open_gallery_for_slot(k))
        btn.pack(pady=5)
        
        if display_img:
            btn.image_obj = display_img # 가비지 컬렉션 방지 참조

        # 4. 관리를 위해 프레임과 위치 정보 저장
        self.slot_containers[target_key] = {
            'frame': slot_frame,
            'index': index,
            'row': row,
            'col': col
        }

    def open_gallery_for_slot(self, key_val):
        ImageGalleryPopup(self, key_val, self.update_slot_image)

    def update_slot_image(self, key_val, image_path):
        """[해결] 해당 슬롯만 destroy() 후 재생성하여 이미지를 확실하게 갱신합니다."""
        target_key = key_val.lower()
        self.parent.bind_image_to_key(target_key, image_path)
        
        # 기존 슬롯 정보 찾기
        slot_info = self.slot_containers.get(target_key)
        if slot_info:
            # 1. 기존 프레임 파괴
            slot_info['frame'].destroy()
            
            # 2. 동일한 위치에 신규 슬롯 생성 (초기 로드 로직 재사용)
            self.create_single_slot(slot_info['index'], slot_info['row'], slot_info['col'])
            
            # 3. 즉시 반영을 위해 업데이트 강제 호출
            self.update_idletasks()

    def destroy(self):
        self.unbind_all("<MouseWheel>")
        super().destroy()

class AccountSelectionPopup(ctk.CTkToplevel):
    def __init__(self, parent, game_path):
        super().__init__(parent)
        self.parent = parent
        self.title("계정 선택")
        self.geometry("300x400")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        # [추가] 최근 계정 사용 여부 확인
        if self.parent.last_account:
            # 창이 나타나기 전에 메세지 박스가 뜨면 포커스 문제가 생길 수 있으므로 after 사용
            self.after(100, self.check_recent_account, game_path)

        save_path = os.path.join(game_path, "Save")
        ctk.CTkLabel(self, text="계정을 선택하세요", font=("Arial", 14, "bold")).pack(pady=20)

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=260, height=300)
        self.scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)

        if os.path.exists(save_path):
            accounts = [d for d in os.listdir(save_path) 
                        if os.path.isdir(os.path.join(save_path, d)) and d.lower() != "default"]
            for acc in accounts:
                btn = ctk.CTkButton(self.scroll_frame, text=acc, 
                                    command=lambda a=acc: self.on_account_select(a, game_path))
                btn.pack(pady=5, padx=10, fill="x")
        else:
            ctk.CTkLabel(self.scroll_frame, text="Save 폴더 없음").pack(pady=20)

    def check_recent_account(self, game_path):
        """최근 계정 사용 확인 메세지창 출력"""
        msg = f"가장 최근에 사용한 계정 '{self.parent.last_account}'을(를)\n다시 사용하시겠습니까?"
        if messagebox.askyesno("최근 계정 확인", msg):
            self.on_account_select(self.parent.last_account, game_path)
    

    def on_account_select(self, account_name, game_path):
        """계정 선택 시 last_account 업데이트 및 저장"""
        ini_path = os.path.join(game_path, "Save", account_name, "customkey.ini")
        if not os.path.exists(ini_path):
            messagebox.showerror("파일 오류", "customkey.ini를 찾을 수 없습니다.")
            return

        # [추가] 최근 사용 계정 정보 업데이트 및 저장
        self.parent.last_account = account_name
        self.parent.save_config()

        """AccountSelectionPopup 클래스 내부의 메서드"""
        ini_path = os.path.join(game_path, "Save", account_name, "customkey.ini")
        if not os.path.exists(ini_path):
            messagebox.showerror("파일 오류", "customkey.ini를 찾을 수 없습니다.")
            return

        content = ""
        # 1. 인코딩 시도 (CP949 우선 사용)
        encodings = ['cp949', 'utf-16', 'utf-8']
        for enc in encodings:
            try:
                with open(ini_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except: continue

        if not content:
            messagebox.showerror("읽기 오류", "파일을 읽을 수 없거나 내용이 비어있습니다.")
            return

        # 2. [Key] 섹션이 시작되는 위치를 찾아 그 앞의 내용을 제거 (파싱 에러 방지)
        key_section_start = content.find("[Key]")
        if key_section_start != -1:
            content = content[key_section_start:]
        else:
            messagebox.showerror("섹션 오류", "[Key] 섹션을 찾을 수 없습니다.")
            return

        # 3. 메모리 내 텍스트로 파싱 진행
        config = configparser.ConfigParser(strict=False)
        try:
            config.read_string(content)
        except Exception as e:
            messagebox.showerror("파싱 오류", f"INI 형식이 올바르지 않습니다: {e}")
            return

        soldier_data = {}
        if config.has_section('Key'):
            for i in range(1, 51):
                key = f"SOLDIER{i}"
                if config.has_option('Key', key): 
                    soldier_data[key] = config.get('Key', key)

        self.destroy()
        InGameKeyConfigPopup(self.parent, soldier_data)

class SaveConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("직접 편집 모드 종료")
        self.geometry("400x200")
        self.attributes("-topmost", True)
        self.grab_set()
        self.result = None
        ctk.CTkLabel(self, text="변경된 설정을 저장하시겠습니까?", font=("Arial", 14, "bold")).pack(pady=20)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(btn_frame, text="저장", width=80, command=lambda: self.set_result("save")).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="다른 이름으로 저장", width=120, command=lambda: self.set_result("save_as")).grid(row=0, column=1, padx=5)
        ctk.CTkButton(btn_frame, text="저장 안 함", width=80, fg_color="#A12F2F", command=lambda: self.set_result("no")).grid(row=1, column=0, padx=5, pady=10)
        ctk.CTkButton(btn_frame, text="취소", width=80, fg_color="#555555", command=lambda: self.set_result("cancel")).grid(row=1, column=1, padx=5, pady=10)
        btn_frame.columnconfigure((0,1), weight=1)

    def set_result(self, res):
        self.result = res
        self.destroy()

class FullKeyboardOverlay(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.modes = {"full": {"w": 1090, "h": 276}, "tkl": {"w": 900, "h": 276}}
        self.current_mode = "full"
        self.min_width_limit = 720 
        self.current_alpha = 0.85
        self.pre_edit_alpha = 0.85 
        self.scale_factor_w = 0.97
        self.scale_factor = 1.0 * self.scale_factor_w
        self.base_key_size = 42
        self.edit_mode = False
        self.config_file = "./config.json"
        
        config_data = self.load_config()
        self.key_bindings = config_data.get("key_bindings", {})
        self.game_path = config_data.get("game_path", r"C:\program files\Lostsaga")
        self.last_account = config_data.get("last_account", "") # 최근 계정 불러오기
        
        self.image_popup = None
        self.resizing = False
        self.resize_edge = None
        
        mode = self.modes[self.current_mode]
        self.geometry(f"{mode['w']}x{mode['h']}")
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

    def load_config(self):
        """JSON 설정 로드 (last_account 필드 추가)"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f: return json.load(f)
            except: pass
        return {"key_bindings": {}, "game_path": r"C:\program files\Lostsaga", "last_account": ""}

    def save_config(self, filename=None):
        """JSON 설정 저장 (last_account 필드 추가)"""
        target = filename if filename else self.config_file
        data = {
            "key_bindings": self.key_bindings, 
            "game_path": self.game_path,
            "last_account": getattr(self, 'last_account', "") # 현재 인스턴스의 계정명 저장
        }
        try:
            with open(target, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except: return False

    def save_config_as(self):
        """다른 이름으로 저장 다이얼로그를 띄웁니다."""
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filename:
            return self.save_config(filename)
        return False

    def create_context_menu(self):
        """우클릭 메뉴 구성 (편집 모드 시 항목 제한 및 초기화 기능 추가)"""
        if self.context_menu: 
            self.context_menu.destroy()
            
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", borderwidth=0)
        
        # [공통] 키보드 레이아웃 설정 메뉴
        bmode_full = "> " if self.current_mode == "full" else "   "
        bmode_tkl = "> " if self.current_mode == "tkl" else "   "
        layout_menu = tk.Menu(self.context_menu, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d")
        layout_menu.add_command(label=f"  {bmode_full}풀 배열 (Full Layout)  ", command=lambda: self.switch_layout("full"))
        layout_menu.add_command(label=f"  {bmode_tkl}텐키리스 (TKL Layout)  ", command=lambda: self.switch_layout("tkl"))
        # layout_menu.add_command(label=f"  {bmode_tkl}커스텀 레이아웃  ", command=lambda: self.switch_layout("custom"))
        self.context_menu.add_cascade(label="  키보드 레이아웃 설정...", menu=layout_menu)
        self.context_menu.add_separator()

        if self.edit_mode:
            # --- 편집 모드일 때: 레이아웃 선택과 완료 버튼만 표시 ---
            self.context_menu.add_command(label="  직접 편집 완료하기  ", command=self.toggle_edit_mode)
        else:
            # --- 일반 모드일 때: 전체 메뉴 표시 ---
            img_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", borderwidth=0)
            img_menu.add_command(label="  인게임 설정으로 편집하기   ", command=lambda: AccountSelectionPopup(self, self.game_path))
            img_menu.add_command(label="  직접 편집하기  ", command=self.toggle_edit_mode)
            self.context_menu.add_cascade(label="  이미지 바인딩 설정...", menu=img_menu)
            self.context_menu.add_separator()
            
            self.context_menu.add_command(label="  현재 상태 저장  ", command=self.save_config)
            self.context_menu.add_command(label="  다른 이름으로 현재 상태 저장  ", command=self.save_config_as)
            self.context_menu.add_command(label="  현재 상태 초기화  ", command=self.reset_all_settings) # 새 기능 추가
            self.context_menu.add_command(label="  창 크기 초기화  ", command=self.reset_to_original_size)
            self.context_menu.add_separator()

            self.context_menu.add_command(label="  종료  ", command=self.destroy)

    def reset_all_settings(self):
        """모든 키 바인딩 설정을 삭제하고 초기화합니다."""
        if messagebox.askyesno("설정 초기화", "모든 키 바인딩 설정을 초기화하시겠습니까?\n(이미지 정보가 모두 사라집니다.)"):
            self.key_bindings = {}
            self.refresh_ui()
            messagebox.showinfo("초기화 완료", "모든 설정이 초기화되었습니다.")

    def set_game_directory(self):
        path = filedialog.askdirectory(title="로스트사가 설치 폴더 선택", initialdir=self.game_path)
        if path:
            self.game_path = os.path.normpath(path)
            self.save_config()

    def toggle_edit_mode(self):
        if self.edit_mode:
            dialog = SaveConfirmDialog(self)
            self.wait_window(dialog)
            if dialog.result == "save": self.save_config()
            elif dialog.result == "cancel": return
            self.withdraw(); self.overrideredirect(True); self.set_transparency(self.pre_edit_alpha); self.configure(fg_color="#1a1a1a"); self.deiconify()
        else:
            self.withdraw(); self.pre_edit_alpha = self.current_alpha; self.overrideredirect(False); self.title("편집 모드 실행 중"); self.set_transparency(1.0); self.configure(fg_color="#2a1a1a"); self.deiconify()
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
        self.aspect_ratio = mode['w'] / mode['h']
        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.buttons = {}
        self.setup_layout()

    def reset_to_original_size(self):
        mode = self.modes[self.current_mode]
        self.geometry(f"{mode['w']}x{mode['h']}")
        self.scale_factor = 1.0 * self.scale_factor_w
        self.update_idletasks()
        self.aspect_ratio = mode['w'] / mode['h']
        self.refresh_ui()

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
        cmd = (lambda tid=target_id: ImageSelectionPopup(self, tid)) if self.edit_mode else None
        btn = ctk.CTkButton(parent, text=display_text, image=img_obj, width=k_w, height=k_h, fg_color="#333333", 
                            text_color="white", corner_radius=int(4*self.scale_factor), 
                            font=("Arial", int(11*self.scale_factor), "bold"), hover=self.edit_mode, command=cmd)
        btn.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan, padx=1, pady=1, sticky="nsew")
        self.buttons[target_id] = btn

    def setup_layout(self):
        s = self.base_key_size
        content_cols = 3 if self.current_mode == "full" else 2
        self.main_frame.grid_columnconfigure(0, weight=1); self.main_frame.grid_columnconfigure(content_cols + 1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1); self.main_frame.grid_rowconfigure(3, weight=1)
        f_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        f_frame.grid(row=1, column=1, columnspan=content_cols, sticky="w", pady=(0, 5))
        for i, group in enumerate([["Esc"], [1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]):
            tmp = ctk.CTkFrame(f_frame, fg_color="transparent")
            tmp.pack(side="left", padx=0 if i == 0 else (int(54 * self.scale_factor), 0))
            for idx, key in enumerate(group): self.create_key(tmp, f"F{key}" if isinstance(key, int) else key, 0, idx)
        m_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); m_frame.grid(row=2, column=1, sticky="n")
        for i, char in enumerate(["`","1","2","3","4","5","6","7","8","9","0","-","="]): self.create_key(m_frame, char, 0, i)
        self.create_key(m_frame, "Back", 0, 13, width=s*2, columnspan=2, key_code="backspace")
        self.create_key(m_frame, "Tab", 1, 0, width=s*1.5, columnspan=2, key_code="tab")
        for i, char in enumerate(["q","w","e","r","t","y","u","i","o","p","[","]","\\"]): self.create_key(m_frame, char.upper(), 1, i+2, key_code=char)
        self.create_key(m_frame, "Caps", 2, 0, width=s*1.8, columnspan=2, key_code="caps_lock")
        for i, char in enumerate(["a","s","d","f","g","h","j","k","l",";","'"]): self.create_key(m_frame, char.upper(), 2, i+2, key_code=char)
        self.create_key(m_frame, "Enter", 2, 13, width=s*1.8, columnspan=2, key_code="enter")
        self.create_key(m_frame, "Shift", 3, 0, width=s*2.3, columnspan=2, key_code="shift")
        for i, char in enumerate(["z","x","c","v","b","n","m",",",".","/"]): self.create_key(m_frame, char.upper(), 3, i+2, key_code=char)
        self.create_key(m_frame, "Shift ", 3, 12, width=s*2.3, columnspan=3, key_code="shift_r")
        self.create_key(m_frame, "Ctrl", 4, 0, width=s*1.3, key_code="ctrl_l"); self.create_key(m_frame, "Win", 4, 1, width=s*1.3, key_code="cmd"); self.create_key(m_frame, "Alt", 4, 2, width=s*1.3, key_code="alt_l")
        self.create_key(m_frame, "SPACE", 4, 3, width=s*6.5, columnspan=9, key_code="space"); self.create_key(m_frame, "Alt", 4, 12, width=s*1.3, key_code="alt_gr"); self.create_key(m_frame, "Ctx", 4, 13, width=s*1.3, key_code="menu"); self.create_key(m_frame, "Ctrl", 4, 14, width=s*1.3, key_code="ctrl_r")
        n_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); n_frame.grid(row=2, column=2, sticky="n", padx=int(10 * self.scale_factor))
        for r, row in enumerate([["insert", "home", "page_up"], ["delete", "end", "page_down"]]):
            for c, k in enumerate(row): self.create_key(n_frame, k[:3].upper(), r, c, key_code=k)
        a_frame = ctk.CTkFrame(n_frame, fg_color="transparent"); a_frame.grid(row=2, column=0, columnspan=3, pady=(s*self.scale_factor, 0))
        self.create_key(a_frame, "↑", 0, 1, key_code="up"); self.create_key(a_frame, "←", 1, 0, key_code="left"); self.create_key(a_frame, "↓", 1, 1, key_code="down"); self.create_key(a_frame, "→", 1, 2, key_code="right")
        if self.current_mode == "full":
            t_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); t_frame.grid(row=2, column=3, sticky="n")
            for r, row in enumerate([[("NL","num_lock"),("/","numpad_div"),("*","numpad_mul"),("-","numpad_sub")],[("7","numpad_7"),("8","numpad_8"),("9","numpad_9")],[("4","numpad_4"),("5","numpad_5"),("6","numpad_6")],[("1","numpad_1"),("2","numpad_2"),("3","numpad_3")]]):
                for c, (txt, kid) in enumerate(row): self.create_key(t_frame, txt, r, c, key_code=kid)
            self.create_key(t_frame, "0", 4, 0, width=s*2, columnspan=2, key_code="numpad_0"); self.create_key(t_frame, ".", 4, 2, key_code="numpad_dot"); self.create_key(t_frame, "+", 1, 3, height=s*2, rowspan=2, key_code="numpad_add"); self.create_key(t_frame, "Ent", 3, 3, height=s*2, rowspan=2, key_code="numpad_enter")

    def win32_filter(self, msg, data): self.last_is_extended = bool(data.flags & 0x01); return True
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
            vk_map = {96:"numpad_0", 97:"numpad_1", 98:"numpad_2", 99:"numpad_3", 100:"numpad_4", 101:"numpad_5", 102:"numpad_6", 103:"numpad_7", 104:"numpad_8", 105:"numpad_9", 106:"numpad_mul", 107:"numpad_add", 109:"numpad_sub", 111:"numpad_div", 110:"numpad_dot", 144:"num_lock"}
            if vk in vk_map: return vk_map[vk]
            if vk == 21 or key == keyboard.Key.alt_r or (vk == 18 and self.last_is_extended): return "alt_gr"
            if vk == 25 or key == keyboard.Key.ctrl_r or (vk == 17 and self.last_is_extended): return "ctrl_r"
            if hasattr(key, 'char') and key.char: return key.char.lower()
            return str(key).replace('Key.', '').lower()
        except: return None
    def open_slider_window(self): TransparencySlider(self)
    def set_transparency(self, value): self.current_alpha = value; self.attributes("-alpha", value)
    def show_menu(self, event): self.create_context_menu(); self.context_menu.post(event.x_root, event.y_root)

def get_lostsaga_key_name(vk_code_str):
    """로스트사가 전용 키 코드를 프로그램 내부 key_code로 변환합니다."""
    try:
        vk = int(vk_code_str)
        # 제공된 목록 기반 매핑 테이블
        mapping = {
            # 특수키
            96: "`", 32: "space", 173: "caps_lock",
            # 방향키
            134: "left", 135: "right", 136: "up", 137: "down",
            # 시스템 및 넘패드 기호
            128: "shift", 129: "shift_r", 131: "ctrl_r",
            156: "numpad_div", 157: "numpad_mul", 158: "numpad_sub", 159: "numpad_add",
            160: "numpad_enter", 161: "numpad_.",
            # 네비게이션
            150: "insert", 152: "home", 154: "page_up",
            151: "delete", 153: "end", 155: "page_down"
        }
        if 48 <= vk and vk <= 57:  # 일반 숫자
            return f"{vk - 48}"
        if 97 <= vk and vk <= 122:  # 알파벳
            return f"{chr(vk)}"
        if 138 <= vk and vk <= 149: # 펑션 키
            return f"F{vk - 137}"
        if 162 <= vk and vk <= 171: # 넘패드 숫자
            return f"numpad_{vk - 162}"
        return mapping.get(vk, f"key_{vk}")
    except:
        return vk_code_str

if __name__ == "__main__":
    app = FullKeyboardOverlay(); app.mainloop()