import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from pynput import keyboard
from PIL import Image
import os
import json
import configparser
import sys

class TransparencySettings(ctk.CTkToplevel):
    """grab_set()을 사용하여 메인 오버레이보다 항상 위에 뜨도록 강제한 버전"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("투명도 설정")
        self.geometry("300x160")
        
        # [핵심 수정] 부모 창보다 위에 뜨도록 하는 3종 세트
        self.attributes("-topmost", True)  # 최상단 고정
        self.transient(parent)             # 부모 창에 종속시킴 (항상 부모 위에 위치)
        
        # 창이 완전히 생성된 후 이벤트를 독점하도록 설정
        self.wait_visibility()             # 창이 보일 때까지 대기
        self.grab_set()                    # 이 창을 닫기 전까지 부모 창 조작 불가 및 레이어 고정
        
        self.resizable(False, False)
        
        # UI 구성
        self.label = ctk.CTkLabel(self, text="오버레이 투명도", font=("Arial", 14, "bold"))
        self.label.pack(pady=(15, 0))

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(pady=10, padx=20, fill="x")

        # 슬라이더 조절 (0.1 ~ 1.0)
        self.slider = ctk.CTkSlider(input_frame, from_=0.1, to=1.0, command=self.update_from_slider)
        self.slider.set(parent.current_alpha) 
        self.slider.pack(side="left", expand=True, padx=(0, 10))

        # 수치 직접 입력창
        self.entry = ctk.CTkEntry(input_frame, width=60, justify="center")
        self.entry.insert(0, str(int(parent.current_alpha * 100)))
        self.entry.pack(side="left")
        self.entry.bind("<Return>", self.update_from_entry)

        ctk.CTkLabel(input_frame, text="%").pack(side="left", padx=2)

        # 하단 닫기 버튼 (모달 창이므로 명확한 종료 버튼이 있으면 편리합니다)
        self.close_btn = ctk.CTkButton(self, text="확인", width=100, command=self.destroy)
        self.close_btn.pack(pady=(0, 10))

    def update_from_slider(self, value):
        self.parent.set_transparency(value)
        self.entry.delete(0, tk.END)
        self.entry.insert(0, str(int(value * 100)))

    def update_from_entry(self, event=None):
        try:
            val = int(self.entry.get())
            if 10 <= val <= 100:
                alpha = val / 100.0
                self.parent.set_transparency(alpha)
                self.slider.set(alpha)
            else:
                messagebox.showwarning("범위 오류", "10% ~ 100% 사이의 값을 입력해주세요.")
        except ValueError:
            messagebox.showerror("입력 오류", "숫자만 입력 가능합니다.")

    def destroy(self):
        """창을 닫을 때 grab_set 해제"""
        self.grab_release()
        super().destroy()

class ImageSelectionPopup(ctk.CTkToplevel):
    """개별 키 편집용 이미지 선택 팝업 - ImageGalleryPopup 디자인과 매치"""
    def __init__(self, parent, key_id):
        super().__init__(parent)
        self.parent = parent
        self.key_id = key_id
        self.title(f"이미지 선택 - [{key_id.upper()}]")
        self.geometry("480x750")
        
        # [디자인 매치] 배경색 및 속성 설정
        self.configure(fg_color="#E7E7E7")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set() 
        
        self.resource_path = "./resource/img/"
        
        # [디자인 매치] 상단 파란색 바 (#2770CB)
        self.header_bar = ctk.CTkFrame(self, height=50, fg_color="#2770CB", corner_radius=10)
        self.header_bar.pack(side="top", fill="x", padx=15, pady=(15, 5))
        
        self.header_label = ctk.CTkLabel(self.header_bar, text=f"키 바인딩 설정 [{key_id.upper()}]", 
                                         font=("Arial", 16, "bold"), text_color="white")
        self.header_label.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self, text="바인딩할 이미지를 선택하세요", font=("Arial", 12), text_color="black").pack(pady=5)

        # [디자인 매치] 스크롤 프레임 스타일
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=440, height=500, 
                                                   fg_color="transparent", 
                                                   scrollbar_button_color="#A0A0A0")
        self.scroll_frame.pack(pady=5, padx=10, fill="both", expand=True)

        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.load_thumbnails()

        self.remove_btn = ctk.CTkButton(self, text="이미지 제거 (텍스트 모드)", fg_color="#A12F2F", 
                                        hover_color="#822525", command=self.remove_binding)
        self.remove_btn.pack(pady=15)

    def _on_mousewheel(self, event):
        speed_multiplier = 100
        scroll_units = int(-1 * (event.delta / 120) * speed_multiplier)
        self.scroll_frame._parent_canvas.yview_scroll(scroll_units, "units")

    def load_thumbnails(self):
        """[디자인 매치] 버튼 스타일 및 중복 체크 흑백 로직 적용"""
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
        files = [f for f in os.listdir(self.resource_path) if f.lower().endswith(valid_extensions)]
        
        # 현재 할당된 이미지 경로들 추출
        bound_paths = [os.path.abspath(p) for p in self.parent.key_bindings.values() if p]
        
        cols = 3
        for i, file in enumerate(files):
            file_path = os.path.join(self.resource_path, file)
            abs_path = os.path.abspath(file_path)
            try:
                pil_img = Image.open(file_path)
                # 이미 사용 중이면 흑백 처리
                if abs_path in bound_paths:
                    pil_img = pil_img.convert("L")
                
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(80, 80))
                
                # 버튼을 슬롯 스타일로 디자인
                btn = ctk.CTkButton(self.scroll_frame, text="", image=ctk_img, width=110, height=110,
                                    fg_color="#2b2b2b", hover_color="#3d3d3d",
                                    border_color="#A0A0A0", border_width=1, corner_radius=8,
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
    """용병 슬롯 전용 이미지 갤러리 팝업 - InGameKeyConfigPopup 컬러톤 매칭 버전"""
    # 이미지 객체를 저장할 클래스 레벨 캐시
    _image_cache = {}

    def __init__(self, parent, target_slot_key, callback):
        super().__init__(parent)
        self.parent = parent
        self.target_slot_key = target_slot_key
        self.callback = callback 
        self.title("캐릭터 검색 및 선택")
        self.geometry("480x750") 
        
        # 디자인 매치: #E7E7E7 배경 및 파란색 헤더
        self.configure(fg_color="#E7E7E7")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        self.resource_path = "./resource/img/"
        self.json_path = "./resource/data.json"
        self.char_data = self.load_char_data()
        self.thumbnail_buttons = {} 

        # 상단 헤더 바 (#2770CB)
        self.header_bar = ctk.CTkFrame(self, height=50, fg_color="#2770CB", corner_radius=10)
        self.header_bar.pack(side="top", fill="x", padx=15, pady=(15, 5))
        self.header_label = ctk.CTkLabel(self.header_bar, text="캐릭터 검색 및 선택", 
                                         font=("Arial", 16, "bold"), text_color="white")
        self.header_label.place(relx=0.5, rely=0.5, anchor="center")

        # 검색창 레이아웃
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(pady=10, padx=20, fill="x")
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="번호, 이름, 초성 검색...", 
                                         fg_color="white", text_color="black")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.search_entry.bind("<Return>", self.on_search) 
        ctk.CTkButton(search_frame, text="검색", width=60, fg_color="#2770CB", command=self.on_search).pack(side="left")

        # [수정] 스크롤 영역 설정 및 마우스 휠 바인딩
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=440, height=500, 
                                                   fg_color="transparent", 
                                                   scrollbar_button_color="#A0A0A0")
        self.scroll_frame.pack(pady=5, padx=10, fill="both", expand=True)

        # [수정] 팝업창 어디서든 휠이 작동하도록 바인딩
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.after(200, lambda: self.search_entry.focus_set())
        
        self.load_thumbnails()

        self.remove_btn = ctk.CTkButton(self, text="이미지 제거 (텍스트 모드)", fg_color="#A12F2F", 
                                        command=self.remove_binding)
        self.remove_btn.pack(pady=15)

    def _on_mousewheel(self, event):
        """마우스 휠 스크롤 로직 (단위 조정)"""
        # Canvas의 yview_scroll을 사용하여 부드럽게 스크롤
        speed_multiplier = 100
        scroll_units = int(-1 * (event.delta / 120) * speed_multiplier)
        self.scroll_frame._parent_canvas.yview_scroll(scroll_units, "units")
    
    def decompose_jamo(self, text):
        """[기능 추가] ㄳ, ㄻ 등의 겹자음을 개별 자음으로 분리하여 검색어와 매칭"""
        mapping = {
            'ㄳ': 'ㄱㅅ', 'ㄵ': 'ㄴㅈ', 'ㄶ': 'ㄴㅎ', 'ㄺ': 'ㄹㄱ', 'ㄻ': 'ㄹㅁ', 
            'ㄼ': 'ㄹㅂ', 'ㄽ': 'ㄹㅅ', 'ㄾ': 'ㄹㅌ', 'ㄿ': 'ㄹㅍ', 'ㅀ': 'ㄹㅎ', 'ㅄ': 'ㅂㅅ'
        }
        return "".join(mapping.get(c, c) for c in text)

    def load_thumbnails(self):
        """[최적화] 이미지 리사이징 및 캐싱 적용 (Fail to allocate bitmap 오류 방지)"""
        bound_paths = []
        if hasattr(self.parent, 'parent') and hasattr(self.parent.parent, 'key_bindings'):
            bound_paths = [os.path.abspath(p) for p in self.parent.parent.key_bindings.values() if p]

        for char_id, info in self.char_data.items():
            if info.get("type") != "char": continue # 용병 타입만 로드

            filename = f"char_icon_{char_id.zfill(3)}.png"
            file_path = os.path.join(self.resource_path, filename)
            abs_path = os.path.abspath(file_path)

            if os.path.exists(file_path):
                is_bound = abs_path in bound_paths
                cache_key = (abs_path, is_bound)

                # 캐시된 이미지가 있으면 사용
                if cache_key in self._image_cache:
                    ctk_img = self._image_cache[cache_key]
                else:
                    try:
                        with Image.open(file_path) as pil_img:
                            if is_bound: pil_img = pil_img.convert("L")
                            # 메모리 절약을 위해 미리 80x80으로 리사이즈
                            thumb = pil_img.resize((80, 80), Image.LANCZOS)
                            ctk_img = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(80, 80))
                            self._image_cache[cache_key] = ctk_img
                    except: continue

                btn = ctk.CTkButton(self.scroll_frame, text="", image=ctk_img, width=110, height=110,
                                    fg_color="#2b2b2b", hover_color="#3d3d3d",
                                    border_color="#A0A0A0", border_width=1, corner_radius=8,
                                    command=lambda p=file_path: self.confirm_selection(p))
                self.thumbnail_buttons[char_id] = btn
        self.update_gallery("")

    def on_search(self, event=None):
        query = self.decompose_jamo(self.search_entry.get().strip().lower())
        self.update_gallery(query)

    def update_gallery(self, query):
        """[수정] data.json의 keyword 리스트를 기반으로 검색 수행"""
        for btn in self.thumbnail_buttons.values(): btn.grid_forget()
        filtered_ids = []
        
        for cid, info in self.char_data.items():
            if cid not in self.thumbnail_buttons: continue
            
            name = info.get("name", "").lower()
            # [수정] keyword 리스트의 모든 항목을 초성 분리하여 검색어와 비교
            keywords = [self.decompose_jamo(k.lower()) for k in info.get("keyword", [])]

            if not query or (query == cid or query in name or any(query in k for k in keywords)):
                filtered_ids.append(cid)

        for i, cid in enumerate(filtered_ids):
            self.thumbnail_buttons[cid].grid(row=i // 3, column=i % 3, padx=8, pady=8)

        for i, cid in enumerate(filtered_ids):
            self.thumbnail_buttons[cid].grid(row=i // 3, column=i % 3, padx=8, pady=8)

    def load_char_data(self):
        """JSON 로드 (encoding 규칙 준수)"""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="euc-kr") as f:
                    return json.load(f)
            except: pass
        return {}

    def confirm_selection(self, path):
        self.callback(self.target_slot_key, path)
        self.destroy()

    def remove_binding(self):
        self.unbind_all("<MouseWheel>")
        self.callback(self.target_slot_key, None) 
        self.destroy()

    def destroy(self):
        self.unbind_all("<MouseWheel>")
        super().destroy()

class InGameKeyConfigPopup(ctk.CTkToplevel):
    """SOLDIER 1~50 설정 창 - 마우스 휠 스크롤 수정 및 최적화 버전"""
    def __init__(self, parent, soldier_data):
        super().__init__(parent)
        self.parent = parent
        self.soldier_data = soldier_data
        self.title("용병 설정 - 로스트사가")
        
        # [디자인] 배경색 #E7E7E7 및 0.8배 축소된 너비(840px) 적용
        self.configure(fg_color="#E7E7E7") 
        self.geometry("840x850") 
        self.attributes("-topmost", True)
        
        self.slot_containers = {} 

        # [디자인] 상단 파란색 바 (#2770CB) 및 여백
        self.header_bar = ctk.CTkFrame(self, height=50, fg_color="#2770CB", corner_radius=10)
        self.header_bar.pack(side="top", fill="x", padx=16, pady=(20, 10))
        
        self.header_label = ctk.CTkLabel(self.header_bar, text="용병 설정 (SOLDIER SLOTS)", 
                                         font=("Arial", 16, "bold"), text_color="white")
        self.header_label.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self, text="슬롯을 클릭하여 이미지를 지정하세요", 
                     font=("Arial", 12), text_color="black").pack(pady=(5, 5))

        # [디자인] 스크롤 영역 (중앙 정렬 설정)
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=800, height=650, 
                                                   fg_color="transparent", 
                                                   scrollbar_button_color="#A0A0A0")
        self.scroll_frame.pack(pady=5, padx=16, fill="both", expand=True)
        
        for c in range(6):
            self.scroll_frame.grid_columnconfigure(c, weight=1)

        # [수정] bind_all 대신 self.bind를 사용하여 팝업창 내 마우스 휠 활성화
        self.bind("<MouseWheel>", self._on_mousewheel)
        
        self.setup_slots()

    def _on_mousewheel(self, event):
        """[수정] 스크롤 영역의 캔버스를 직접 제어하여 마우스 휠 적용"""
        # 델타 값을 120으로 나누어 한 칸씩 부드럽게 스크롤되도록 조정합니다.
        speed_multiplier = 100
        scroll_units = int(-1 * (event.delta / 120) * speed_multiplier)
        self.scroll_frame._parent_canvas.yview_scroll(scroll_units, "units")

    def setup_slots(self):
        """6열 그리드로 슬롯 생성"""
        cols = 6
        for i in range(1, 51):
            row = (i-1)//cols
            col = (i-1)%cols
            self.create_single_slot(i, row, col)

    def create_single_slot(self, index, row, col):
        """[최적화] 이미지 리사이징 및 1:1 정비율 슬롯 생성"""
        s_id = f"SOLDIER{index}"
        raw_val = self.soldier_data.get(s_id, "0")
        key_id = get_lostsaga_key_name(raw_val)
        target_key = key_id.lower()
        
        # [디자인] 슬롯 외곽 프레임 (축소된 128px 너비)
        slot_frame = ctk.CTkFrame(self.scroll_frame, width=128, height=140, 
                                  fg_color="#2b2b2b", border_color="#A0A0A0", 
                                  border_width=2, corner_radius=8)
        slot_frame.grid(row=row, column=col, padx=6, pady=6)
        slot_frame.grid_propagate(False)

        # [디자인] 키 표시 이름 및 가독성 높은 박스 (55x28)
        mapping = {
            "numpad_add": "NUM+", "numpad_div": "NUM /", "numpad_mul": "NUM *",
            "numpad_sub": "NUM -", "numpad_dot": "NUM .", "numpad_enter": "N_ENT",
            "page_up": "PG_UP", "page_down": "PG_DOWN", "caps_lock": "CAPSLOCK"
        }
        display_name = mapping.get(target_key, key_id.replace("numpad_", "NUM ").upper())
        
        key_box = ctk.CTkFrame(slot_frame, width=55, height=28, fg_color="#2770CB", corner_radius=4)
        key_box.place(x=6, y=6) 
        ctk.CTkLabel(key_box, text=display_name, font=("Arial", 11, "bold"), 
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        # [최적화] 비트맵 에러 방지를 위한 리사이징 및 1:1 비율 유지
        img_path = self.parent.key_bindings.get(target_key)
        display_img = None
        if img_path and os.path.exists(img_path):
            try:
                with Image.open(img_path) as raw_img:
                    # 가로/세로 중 작은 쪽을 기준으로 중앙 1:1 비율 이미지 생성
                    img_side = int(min(80, 80)) # 고정된 슬롯 내 버튼 크기에 맞춤
                    resized = raw_img.resize((img_side, img_side), Image.LANCZOS)
                    display_img = ctk.CTkImage(light_image=resized, dark_image=resized, size=(68, 68))
            except: pass

        # 이미지 선택 버튼
        btn = ctk.CTkButton(slot_frame, 
                            text="+" if not display_img else "", 
                            image=display_img, 
                            width=80, height=80,
                            fg_color="transparent",
                            hover_color="#3d3d3d",
                            command=lambda k=key_id: self.open_gallery_for_slot(k))
        btn.place(relx=0.5, rely=0.58, anchor="center")
        
        if display_img:
            btn.image_obj = display_img 

        self.slot_containers[target_key] = {
            'frame': slot_frame, 'index': index, 'row': row, 'col': col
        }

    def open_gallery_for_slot(self, key_val):
        """이미지 갤러리 팝업 열기"""
        ImageGalleryPopup(self, key_val, self.update_slot_image)

    def update_slot_image(self, key_val, image_path):
        """이미지 선택 후 해당 슬롯 UI 갱신"""
        target_key = key_val.lower()
        self.parent.bind_image_to_key(target_key, image_path)
        
        slot_info = self.slot_containers.get(target_key)
        if slot_info:
            slot_info['frame'].destroy()
            self.create_single_slot(slot_info['index'], slot_info['row'], slot_info['col'])
            self.update_idletasks()

    def destroy(self):
        """팝업 종료 시 이벤트 해제"""
        self.unbind("<MouseWheel>")
        super().destroy()

class AccountSelectionPopup(ctk.CTkToplevel):
    """계정 선택 팝업 - 디자인 통일 및 계정명 전용 저장 로직 적용"""
    def __init__(self, parent, game_path):
        super().__init__(parent)
        self.parent = parent
        self.title("계정 선택")
        self.geometry("400x550")
        
        # [디자인 매치] 배경색 및 속성 설정
        self.configure(fg_color="#E7E7E7")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        # [디자인 매치] 상단 파란색 바 (#2770CB)
        self.header_bar = ctk.CTkFrame(self, height=50, fg_color="#2770CB", corner_radius=10)
        self.header_bar.pack(side="top", fill="x", padx=15, pady=(15, 5))
        
        self.header_label = ctk.CTkLabel(self.header_bar, text="계정 선택 (Account Selection)", 
                                         font=("Arial", 16, "bold"), text_color="white")
        self.header_label.place(relx=0.5, rely=0.5, anchor="center")

        # 최근 계정 확인 로직
        if self.parent.last_account:
            self.after(100, self.check_recent_account, game_path)

        save_path = os.path.join(game_path, "Save")
        ctk.CTkLabel(self, text="불러올 계정을 목록에서 선택하세요", font=("Arial", 12), text_color="black").pack(pady=10)

        # 스크롤 영역 스타일 조정
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=360, height=400, 
                                                   fg_color="transparent", 
                                                   scrollbar_button_color="#A0A0A0")
        self.scroll_frame.pack(pady=10, padx=15, fill="both", expand=True)

        if os.path.exists(save_path):
            accounts = [d for d in os.listdir(save_path) 
                        if os.path.isdir(os.path.join(save_path, d)) and d.lower() != "default"]
            for acc in accounts:
                # 버튼 디자인을 슬롯 스타일과 유사하게 조정
                btn = ctk.CTkButton(self.scroll_frame, text=acc, height=40,
                                    fg_color="#2b2b2b", hover_color="#3d3d3d",
                                    command=lambda a=acc: self.on_account_select(a, game_path))
                btn.pack(pady=5, padx=10, fill="x")
        else:
            ctk.CTkLabel(self.scroll_frame, text="Save 폴더를 찾을 수 없습니다.", text_color="red").pack(pady=20)

    def check_recent_account(self, game_path):
        msg = f"가장 최근에 사용한 계정 '{self.parent.last_account}'을(를)\n다시 사용하시겠습니까?"
        if messagebox.askyesno("최근 계정 확인", msg):
            self.on_account_select(self.parent.last_account, game_path)

    def on_account_select(self, account_name, game_path):
        """[수정] 계정 선택 시 전체 저장이 아닌 계정명만 자동 저장"""
        ini_path = os.path.join(game_path, "Save", account_name, "customkey.ini")
        if not os.path.exists(ini_path):
            messagebox.showerror("파일 오류", "customkey.ini를 찾을 수 없습니다.")
            return

        # [수정] 전체 save_config() 대신 알림 없는 전용 메서드 호출
        self.parent.update_last_account(account_name)

        # INI 파싱 로직 (기존과 동일)
        content = ""
        encodings = ['cp949', 'utf-16', 'utf-8']
        for enc in encodings:
            try:
                with open(ini_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except: continue

        key_section_start = content.find("[Key]")
        if key_section_start != -1:
            content = content[key_section_start:]
            config = configparser.ConfigParser(strict=False)
            config.read_string(content)
            
            soldier_data = {}
            if config.has_section('Key'):
                for i in range(1, 51):
                    key = f"SOLDIER{i}"
                    if config.has_option('Key', key): 
                        soldier_data[key] = config.get('Key', key)

            self.destroy()
            InGameKeyConfigPopup(self.parent, soldier_data)
        else:
            messagebox.showerror("섹션 오류", "[Key] 섹션을 찾을 수 없습니다.")

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
    def __init__(self, config_path="./config.json"): # 인자 추가
        super().__init__()
        self.config_file = config_path # 전달받은 경로를 기본 경로로 설정
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
        # [추가] 변경 사항 비교를 위한 원본 설정 복사본 저장
        self.saved_bindings = self.key_bindings.copy()
        
        self.game_path = config_data.get("game_path", r"C:\program files\Lostsaga")
        self.last_account = config_data.get("last_account", "")
        
        self.image_popup = None
        self.resizing = False
        self.resize_edge = None
        
        mode = self.modes[self.current_mode]
        self.geometry(f"{mode['w']}x{mode['h']}")
        self.attributes("-topmost", True)
        self.attributes("-alpha", self.current_alpha) 
        self.overrideredirect(True)                  
        self.configure(fg_color="#1a1a1a")      

        # 설정 로드 시 self.config_file 사용
        config_data = self.load_config()
        self.key_bindings = config_data.get("key_bindings", {})
        self.saved_bindings = self.key_bindings.copy()     
        
        # 윈도우 종료 핸들러 등록
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
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

    def on_closing(self):
        """[수정] 종료 시 미저장 변경사항 확인 로직 추가"""
        if self.edit_mode:
            # 직접 편집 모드인 경우 모드만 종료 (이전 요청 사항 유지)
            self.toggle_edit_mode()
        else:
            # 설정값 비교
            if self.key_bindings != self.saved_bindings:
                if messagebox.askyesno("종료 확인", "변경사항이 저장되지 않았습니다.\n정말로 종료하시겠습니까?"):
                    self.destroy()
            else:
                self.destroy()

    def load_config(self):
        """JSON 설정 로드"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f: 
                    return json.load(f)
            except: pass
        return {"game_path": r"C:\program files\Lostsaga", "last_account": "", "key_bindings": {}}
    
    def load_config_from_file(self):
        """[수정] 외부 설정 파일을 불러오고 현재 활성 설정 파일 경로를 업데이트함"""
        filename = filedialog.askopenfilename(title="설정 파일 불러오기", filetypes=[("JSON files", "*.json")])
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    new_data = json.load(f)
                    self.key_bindings = new_data.get("key_bindings", {})
                    # [핵심] 불러온 파일을 현재 활성 설정 파일로 지정
                    self.config_file = filename 
                    self.saved_bindings = self.key_bindings.copy()
                    self.refresh_ui()
                    # 메뉴 이름 갱신을 위해 메뉴 재생성
                    self.create_context_menu() 
                    messagebox.showinfo("불러오기 완료", f"'{os.path.basename(filename)}' 파일을 불러왔습니다.")
            except:
                messagebox.showerror("오류", "파일을 불러오는 중 오류가 발생했습니다.")

    
    def update_last_account(self, account_name):
        """[기능 추가] 계정 정보만 설정 파일에 알림 없이 저장"""
        self.last_account = account_name
        
        # 1. 현재 디스크에 저장된 설정을 그대로 읽어옴 (메모리의 미저장 변경사항 보호)
        config_data = self.load_config()
        
        # 2. 계정 정보만 교체
        config_data["last_account"] = account_name
        
        # 3. 파일에 저장 (메시지 박스 출력 없음)
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"계정 정보 자동 저장 실패: {e}")

    def save_config(self, filename=None):
        """[수정] 저장 성공 시 현재 활성 파일 경로를 업데이트함"""
        target = filename if filename else self.config_file
        data = {
            "key_bindings": self.key_bindings, 
            "game_path": self.game_path,
            "last_account": getattr(self, 'last_account', "")
        }
        try:
            with open(target, "w", encoding="utf-8") as f: 
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            self.saved_bindings = self.key_bindings.copy()
            # [추가] 저장이 완료된 파일을 현재 활성 설정 파일로 업데이트
            self.config_file = target 
            messagebox.showinfo("저장 완료", f"'{os.path.basename(target)}' 파일에 저장을 완료했습니다.")
            # 별표(*) 표시 제거를 위해 메뉴 갱신
            self.create_context_menu() 
            return True
        except Exception as e:
            messagebox.showerror("저장 실패", f"파일 저장 중 오류가 발생했습니다: {e}")
            return False

    def save_config_as(self):
        """다른 이름으로 저장"""
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filename:
            return self.save_config(filename)
        return False

    def revert_changes(self):
        """변경사항 초기화하기 (마지막 저장 상태로 복구)"""
        if messagebox.askyesno("변경사항 초기화", "저장되지 않은 모든 변경사항을 취소하시겠습니까?"):
            self.key_bindings = self.saved_bindings.copy()
            self.refresh_ui()
            messagebox.showinfo("초기화 완료", "마지막 저장 상태로 복구되었습니다.")

    def create_context_menu(self):
        """[수정] 저장 메뉴에 현재 활성화된 설정 파일명을 표시함"""
        if self.context_menu: 
            self.context_menu.destroy()
            
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", borderwidth=0)
        
        has_changes = (self.key_bindings != self.saved_bindings)
        save_prefix = "* " if has_changes else "  "
        
        # [추가] 현재 활성화된 파일의 이름 추출
        current_config_name = os.path.basename(self.config_file)

        # 레이아웃 설정 메뉴
        layout_menu = tk.Menu(self.context_menu, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d")
        layout_menu.add_command(label=f"  {'• ' if self.current_mode == 'full' else '   '}풀 배열 (Full)  ", command=lambda: self.switch_layout("full"))
        layout_menu.add_command(label=f"  {'• ' if self.current_mode == 'tkl' else '   '}텐키리스 (TKL)  ", command=lambda: self.switch_layout("tkl"))
        self.context_menu.add_cascade(label="  키보드 레이아웃 설정", menu=layout_menu)

        if self.edit_mode:
            self.context_menu.add_command(label="  직접 편집 완료하기  ", command=self.toggle_edit_mode)
        else:
            img_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", borderwidth=0)
            img_menu.add_command(label="  인게임 설정으로 편집하기  ", command=lambda: AccountSelectionPopup(self, self.game_path))
            img_menu.add_command(label="  직접 편집하기  ", command=self.toggle_edit_mode)
            self.context_menu.add_cascade(label="  이미지 바인딩 설정", menu=img_menu)
            self.context_menu.add_command(label="  배경 투명도 설정 열기", command=self.open_slider_window)
            self.context_menu.add_separator()
            
            # [수정] 동적으로 파일명을 출력하도록 레이블 변경
            self.context_menu.add_command(label="  설정 파일 불러오기", command=self.load_config_from_file)
            self.context_menu.add_command(label=f"{save_prefix}{current_config_name}에 저장하기", command=self.save_config)
            self.context_menu.add_command(label=f"{save_prefix}다른 이름으로 현재 설정 저장", command=self.save_config_as)
            
            if has_changes:
                self.context_menu.add_command(label=f"{save_prefix}변경사항 초기화", command=self.revert_changes)
            self.context_menu.add_separator()

            self.context_menu.add_command(label="  모든 설정 완전 초기화", command=self.reset_all_settings)
            self.context_menu.add_command(label="  창 크기 초기화", command=self.reset_to_original_size)
            self.context_menu.add_separator()

            self.context_menu.add_command(label="  종료", command=self.on_closing)

    def open_slider_window(self):
        """투명도 설정 팝업 열기"""
        TransparencySettings(self)

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
            self.withdraw()
            self.overrideredirect(True)
            self.set_transparency(self.pre_edit_alpha)
            self.configure(fg_color="#1a1a1a")
            self.deiconify()
        else:
            self.withdraw()
            self.pre_edit_alpha = self.current_alpha
            self.overrideredirect(False)
            self.title("직접 편집 모드 - 키를 클릭하여 수정하세요")
            self.set_transparency(1.0)
            self.configure(fg_color="#2a1a1a")
            self.deiconify()
            
        self.edit_mode = not self.edit_mode
        self.refresh_ui()
        self.create_context_menu()

    def bind_image_to_key(self, key_id, path):
        if path: self.key_bindings[key_id] = path
        else: self.key_bindings.pop(key_id, None)
        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.buttons = {}
        self.setup_layout()

    def switch_layout(self, mode_key):
        self.current_mode = mode_key
        mode = self.modes[mode_key]
        self.geometry(f"{mode['w']}x{mode['h']}")
        self.scale_factor = 1.0 * self.scale_factor_w
        self.update_idletasks()
        self.aspect_ratio = mode['w'] / mode['h']
        self.refresh_ui()

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
                # [최적화] 리사이징을 통한 비트맵 에러 방지
                with Image.open(self.key_bindings[target_id]) as raw_img:
                    # [수정] 가로/세로 중 작은 값을 기준으로 1:1 비율 유지
                    img_side = int(min(k_w, k_h) * 0.8)
                    resized = raw_img.resize((img_side, img_side), Image.LANCZOS)
                    img_obj = ctk.CTkImage(light_image=resized, dark_image=resized, size=(img_side, img_side))
                display_text = ""
            except: pass
        
        cmd = (lambda tid=target_id: ImageSelectionPopup(self, tid)) if self.edit_mode else None
        btn = ctk.CTkButton(parent, text=display_text, image=img_obj, width=k_w, height=k_h, 
                            fg_color="#333333", text_color="white", corner_radius=int(4*self.scale_factor), 
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
    def open_slider_window(self): TransparencySettings(self)
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
    # 실행 시 인자가 있으면 해당 경로를 사용, 없으면 기본 config.json 사용
    # 예: python app.py custom_config.json
    target_config = sys.argv[1] if len(sys.argv) > 1 else "./config.json"
    
    app = FullKeyboardOverlay(config_path=target_config)
    app.mainloop()