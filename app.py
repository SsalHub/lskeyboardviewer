import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from pynput import keyboard
from PIL import Image, ImageTk, ImageGrab
import os
import json
import configparser
import sys
import ctypes  # Win32 API 호출을 위해 추가

BASIC_ICON_MAP = {
    "ATTACK": "basic_icon_attack.png",
    "DEFENSE": "basic_icon_guard.png",
    "JUMP": "basic_icon_jump.png",
    "WEAPON_SKILL": "basic_icon_weapon.png",
    "ARMOR_SKILL": "basic_icon_armor.png",
    "HELM_SKILL": "basic_icon_helmet.png",
    "CLOAK_SKILL": "basic_icon_trinket.png"
}
# Win32 관련 상수 (클래스 상단 또는 메서드 내부 정의)
GWL_STYLE = -16
WS_POPUP = 0x80000000      # 팝업 스타일 (타이틀 바 없음)
WS_THICKFRAME = 0x00040000 # 리사이징 테두리 활성화
WS_CAPTION = 0x00C00000    # 타이틀 바 + 테두리
SWP_FRAMECHANGED = 0x0020
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004

def resource_path(relative_path):
    """ 실행 파일 내부의 임시 폴더 경로를 참조하도록 수정합니다. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class KeyCapturePopup(ctk.CTkToplevel):
    """키 입력을 대기하고 감지된 키의 VK 코드를 반환하는 팝업"""
    def __init__(self, parent, ini_key, display_name, callback):
        super().__init__(parent)
        self.parent = parent
        self.ini_key = ini_key
        self.callback = callback
        
        self.title("키 입력 대기")
        self.geometry("300x120")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()
        
        # 중앙 라벨 설정
        self.label = ctk.CTkLabel(self, text=f"[{display_name}]에 해당하는\n키를 눌러주세요.", 
                                  font=("Arial", 14, "bold"))
        self.label.pack(expand=True)
        
        # pynput을 사용하여 시스템 레벨의 VK 코드를 정확히 포착
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

    def on_key_press(self, key):
        """키가 눌리면 VK 코드를 추출하고 콜백 실행 후 창을 닫음"""
        try:
            # pynput의 vk 속성 추출
            vk = getattr(key, 'vk', None)
            if vk is None:
                # 특수키(Shift, Ctrl 등) 처리
                vk_map = {keyboard.Key.shift: 128, keyboard.Key.shift_r: 129, keyboard.Key.ctrl_r: 131}
                vk = vk_map.get(key)

            if vk is not None:
                # 메인 쓰레드에서 UI를 갱신하도록 after 사용
                self.after(0, lambda: self.callback(self.ini_key, str(vk)))
                self.after(0, self.destroy)
                return False # 리스너 중단
        except Exception as e:
            print(f"키 캡처 오류: {e}")
        return True

    def destroy(self):
        """종료 시 리스너와 grab 해제"""
        if hasattr(self, 'listener'):
            self.listener.stop()
        self.grab_release()
        super().destroy()

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
    """개별 키 편집용 이미지 선택 팝업 - 검색 기능 및 전역 캐시 적용 버전"""
    def __init__(self, parent, key_id):
        super().__init__(parent)
        self.parent = parent
        self.key_id = key_id
        self.title(f"이미지 선택 - [{key_id.upper()}]")
        self.geometry("480x750")
        
        # 디자인 매치: 배경색 및 속성 설정
        self.configure(fg_color="#E7E7E7")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set() 
        
        self.resource_path = resource_path("./resource/img/")
        self.thumbnail_buttons = {} # 검색 필터링을 위한 버튼 저장소
        
        # 상단 파란색 바 (#2770CB)
        self.header_bar = ctk.CTkFrame(self, height=50, fg_color="#2770CB", corner_radius=10)
        self.header_bar.pack(side="top", fill="x", padx=15, pady=(15, 5))
        
        self.header_label = ctk.CTkLabel(self.header_bar, text=f"키 바인딩 설정 [{key_id.upper()}]", 
                                         font=("Arial", 16, "bold"), text_color="white")
        self.header_label.place(relx=0.5, rely=0.5, anchor="center")

        # [추가] 검색창 레이아웃
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(pady=10, padx=20, fill="x")
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="이름, 초성 검색...", 
                                         fg_color="white", text_color="black")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.search_entry.bind("<Return>", self.on_search) 
        ctk.CTkButton(search_frame, text="검색", width=60, fg_color="#2770CB", command=self.on_search).pack(side="left")

        # 스크롤 프레임 스타일
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=440, height=500, 
                                                   fg_color="transparent", 
                                                   scrollbar_button_color="#A0A0A0")
        self.scroll_frame.pack(pady=5, padx=10, fill="both", expand=True)

        self.bind("<MouseWheel>", self._on_mousewheel)
        self.after(200, lambda: self.search_entry.focus_set()) # 창 열릴 때 검색창 포커스
        
        self.load_thumbnails()

        self.remove_btn = ctk.CTkButton(self, text="이미지 제거 (텍스트 모드)", fg_color="#A12F2F", 
                                        hover_color="#822525", command=self.remove_binding)
        self.remove_btn.pack(pady=15)

    def _on_mousewheel(self, event):
        """마우스 휠 스크롤 로직"""
        self.scroll_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def decompose_jamo(self, text):
        """[기능 추가] ㄳ, ㄻ 등의 겹자음을 분리하여 검색어 매칭"""
        mapping = {
            'ㄳ': 'ㄱㅅ', 'ㄵ': 'ㄴㅈ', 'ㄶ': 'ㄴㅎ', 'ㄺ': 'ㄹㄱ', 'ㄻ': 'ㄹㅁ', 
            'ㄼ': 'ㄹㅂ', 'ㄽ': 'ㄹㅅ', 'ㄾ': 'ㄹㅌ', 'ㄿ': 'ㄹㅍ', 'ㅀ': 'ㄹㅎ', 'ㅄ': 'ㅂㅅ'
        }
        return "".join(mapping.get(c, c) for c in text)

    def load_thumbnails(self):
        """[수정] 전역 캐시를 사용하여 이미지를 로드하고 검색용 딕셔너리에 저장"""
        bound_files = [os.path.basename(p) for p in self.parent.key_bindings.values() if p]
        
        # 캐시된 이미지들 순회
        for filename, pil_img in self.parent.image_cache.items():
            file_path = os.path.join(self.resource_path, filename)
            
            # 사용 중인 이미지는 흑백 처리
            display_pil = pil_img.convert("L") if filename in bound_files else pil_img
            ctk_img = ctk.CTkImage(light_image=display_pil, dark_image=display_pil, size=(80, 80))
                
            btn = ctk.CTkButton(self.scroll_frame, text="", image=ctk_img, width=110, height=110,
                                fg_color="#2b2b2b", hover_color="#3d3d3d",
                                border_color="#A0A0A0", border_width=1, corner_radius=8,
                                command=lambda p=file_path: self.select_image(p))
            self.thumbnail_buttons[filename] = btn
            
        self.update_gallery("") # 초기 상태(전체 출력)

    def convert_to_jamo(self, text):
        """[신규] 영문 입력을 한글 자판 위치에 맞는 자음/모음으로 변환 후 분리합니다."""
        mapping = {
            'q': 'ㅂ', 'w': 'ㅈ', 'e': 'ㄷ', 'r': 'ㄱ', 't': 'ㅅ', 'y': 'ㅛ', 'u': 'ㅕ', 'i': 'ㅑ', 'o': 'ㅐ', 'p': 'ㅔ',
            'a': 'ㅁ', 's': 'ㄴ', 'd': 'ㅇ', 'f': 'ㄹ', 'g': 'ㅎ', 'h': 'ㅗ', 'j': 'ㅓ', 'k': 'ㅏ', 'l': 'ㅣ',
            'z': 'ㅋ', 'x': 'ㅌ', 'c': 'ㅊ', 'v': 'ㅍ', 'b': 'ㅠ', 'n': 'ㅜ', 'm': 'ㅡ',
            'Q': 'ㅃ', 'W': 'ㅉ', 'E': 'ㄸ', 'R': 'ㄲ', 'T': 'ㅆ', 'O': 'ㅒ', 'P': 'ㅖ'
        }
        converted = "".join(mapping.get(char, char) for char in text)
        return self.decompose_jamo(converted) # 기존 초성 분리 함수 호출

    def on_search(self, event=None):
        """[수정] 영타를 한글로 변환하여 검색을 수행합니다."""
        raw_query = self.search_entry.get().strip()
        # 영타 위치를 한글로 자동 해석
        query = self.convert_to_jamo(raw_query).lower()
        self.update_gallery(query)

    def update_gallery(self, query):
        """[신규] 파일명 및 data.json 정보를 기반으로 검색 결과 필터링"""
        for btn in self.thumbnail_buttons.values():
            btn.grid_forget()

        filtered_files = []
        for filename in self.thumbnail_buttons.keys():
            if not query:
                filtered_files.append(filename)
                continue

            # 1. 파일명 자체에 검색어가 포함되는지 확인
            if query in filename.lower():
                filtered_files.append(filename)
                continue

            # 2. 용병 아이콘인 경우(char_icon_xxx.png) data.json의 이름/키워드와 대조
            if filename.startswith("char_icon_"):
                try:
                    char_id = str(int(filename.replace("char_icon_", "").replace(".png", "")))
                    if char_id in self.parent.char_data:
                        info = self.parent.char_data[char_id]
                        name = info.get("name", "").lower()
                        keywords = [self.decompose_jamo(k.lower()) for k in info.get("keyword", [])]
                        
                        if query in name or any(query in k for k in keywords):
                            filtered_files.append(filename)
                except: pass

        # 필터링된 결과 배치
        cols = 3
        for i, fname in enumerate(filtered_files):
            self.thumbnail_buttons[fname].grid(row=i // cols, column=i % cols, padx=10, pady=10)
        self.scroll_frame._parent_canvas.yview_moveto(0)

    def select_image(self, path):
        """[수정] 이미지 선택 시 중복 여부를 확인하고 기존 바인딩을 해제한 뒤 재할당합니다."""
        existing_key = None
        # 현재 선택한 이미지가 다른 키에 이미 바인딩되어 있는지 확인
        for k, v in self.parent.key_bindings.items():
            if v == path and k != self.key_id:
                existing_key = k
                break

        if existing_key:
            # 중복된 경우 확인 팝업 출력
            if messagebox.askyesno("중복 확인", f"이미 [{existing_key.upper()}] 키에 설정된 이미지입니다.\n새로 바꾸시겠습니까?"):
                # 기존 키의 바인딩을 해제 (None으로 설정)
                self.parent.bind_image_to_key(existing_key, None)
                # 현재 키에 새 이미지 바인딩
                self.parent.bind_image_to_key(self.key_id, path)
                self.destroy()
        else:
            # 중복이 없는 경우 일반적인 바인딩 진행
            self.parent.bind_image_to_key(self.key_id, path)
            self.destroy()

    def remove_binding(self):
        self.parent.bind_image_to_key(self.key_id, None)
        self.destroy()

    def destroy(self):
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

        self.resource_path = resource_path("./resource/img/")
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
        """[수정] 전역 캐시를 사용하여 갤러리 생성 (속도 대폭 향상)"""
        bound_paths = [os.path.basename(p) for p in self.parent.parent.key_bindings.values() if p]

        # 파일 목록 대신 캐시된 리스트 사용
        for char_id, info in self.parent.parent.char_data.items():
            if info.get("type") != "char": continue # 용병 타입만 로드

            filename = f"char_icon_{char_id.zfill(3)}.png"
            file_path = os.path.join(self.resource_path, filename)
            abs_path = os.path.abspath(file_path)

            filename = f"char_icon_{char_id.zfill(3)}.png"
            if filename in self.parent.parent.image_cache:
                pil_img = self.parent.parent.image_cache[filename]
                
                # 흑백 처리가 필요한 경우에만 메모리 상에서 변환
                if filename in bound_paths:
                    display_pil = pil_img.convert("L")
                else:
                    display_pil = pil_img
                
                ctk_img = ctk.CTkImage(light_image=display_pil, dark_image=display_pil, size=(80, 80))

                btn = ctk.CTkButton(self.scroll_frame, text="", image=ctk_img, width=110, height=110,
                                    fg_color="#2b2b2b", hover_color="#3d3d3d",
                                    border_color="#A0A0A0", border_width=1, corner_radius=8,
                                    command=lambda p=file_path: self.confirm_selection(p))
                self.thumbnail_buttons[char_id] = btn
        self.update_gallery("")

    def convert_to_jamo(self, text):
        """[신규] 영문 입력을 한글 자판 위치에 맞는 자음/모음으로 변환 후 분리합니다."""
        mapping = {
            'q': 'ㅂ', 'w': 'ㅈ', 'e': 'ㄷ', 'r': 'ㄱ', 't': 'ㅅ', 'y': 'ㅛ', 'u': 'ㅕ', 'i': 'ㅑ', 'o': 'ㅐ', 'p': 'ㅔ',
            'a': 'ㅁ', 's': 'ㄴ', 'd': 'ㅇ', 'f': 'ㄹ', 'g': 'ㅎ', 'h': 'ㅗ', 'j': 'ㅓ', 'k': 'ㅏ', 'l': 'ㅣ',
            'z': 'ㅋ', 'x': 'ㅌ', 'c': 'ㅊ', 'v': 'ㅍ', 'b': 'ㅠ', 'n': 'ㅜ', 'm': 'ㅡ',
            'Q': 'ㅃ', 'W': 'ㅉ', 'E': 'ㄸ', 'R': 'ㄲ', 'T': 'ㅆ', 'O': 'ㅒ', 'P': 'ㅖ'
        }
        converted = "".join(mapping.get(char, char) for char in text)
        return self.decompose_jamo(converted) # 기존 초성 분리 함수 호출

    def on_search(self, event=None):
        """[수정] 영타를 한글로 변환하여 검색을 수행합니다."""
        raw_query = self.search_entry.get().strip()
        # 영타 위치를 한글로 자동 해석
        query = self.convert_to_jamo(raw_query).lower()
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
        self.scroll_frame._parent_canvas.yview_moveto(0)

    def load_char_data(self):
        """JSON 로드 (encoding 규칙 준수)"""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="euc-kr") as f:
                    return json.load(f)
            except: pass
        return {}

    def confirm_selection(self, path):
        """[수정] 경로 오차 해결 및 동일 이미지 재할당 방지 로직 적용"""
        selected_filename = os.path.basename(path)
        current_bindings = self.parent.parent.key_bindings
        
        # 1. 현재 키에 똑같은 이미지를 다시 할당하려는지 검사
        assigned_path = current_bindings.get(self.target_slot_key, "")
        if assigned_path and os.path.basename(assigned_path) == selected_filename:
            messagebox.showinfo("알림", "이미 할당된 이미지입니다.")
            return

        # 2. 다른 키에 이미 설정된 이미지인지 검사 (파일명 기준)
        existing_key = None
        for k, v in current_bindings.items():
            if v and os.path.basename(v) == selected_filename and k != self.target_slot_key:
                existing_key = k
                break

        if existing_key:
            if messagebox.askyesno("중복 확인", f"이미 '{existing_key.upper()}'에 설정된 이미지입니다.\n새로 바꾸시겠습니까?"):
                # 기존 키 해제 및 UI 갱신
                self.parent.parent.bind_image_to_key(existing_key, None)
                self.parent.refresh_specific_slot(existing_key) 
                # 새 슬롯 할당
                self.callback(self.target_slot_key, path)
                self.destroy()
        else:
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
    """상단 고정 조작키 구역과 하단 용병 슬롯의 디자인을 개별 최적화한 설정 팝업"""
    def __init__(self, parent, all_key_data):
        super().__init__(parent)
        self.parent = parent
        self.all_key_data = all_key_data # SOLDIER + 기본/스킬 키 통합 데이터
        self.title("용병 및 스킬 설정 - 로스트사가")
        self.configure(fg_color="#E7E7E7") 
        self.geometry("860x1000") 
        self.attributes("-topmost", True)
        self.slot_containers = {} 

        # 1. 헤더 바
        self.basic_header_bar = ctk.CTkFrame(self, height=50, fg_color="#2770CB", corner_radius=10)
        self.basic_header_bar.pack(side="top", fill="x", padx=16, pady=(20, 10))
        self.basic_header_label = ctk.CTkLabel(self.basic_header_bar, text="기본 조작키 설정", 
                                         font=("Arial", 16, "bold"), text_color="white")
        self.basic_header_label.place(relx=0.5, rely=0.5, anchor="center")

        # 2. 상단 고정 구역 (공격, 방어, 점프 + 스킬 4종)
        self.top_section = ctk.CTkFrame(self, fg_color="transparent")
        self.top_section.pack(side="top", fill="x", padx=16, pady=5)
        self.setup_basic_skill_slots()

        # 구분선
        separator = ctk.CTkFrame(self, height=2, fg_color="#A0A0A0")
        separator.pack(side="top", fill="x", padx=20, pady=10)
        # ctk.CTkLabel(self, text="용병 슬롯 목록 (HERO SLOTS)", font=("Arial", 12, "bold"), text_color="#555555").pack(side="top")
        self.hero_header_bar = ctk.CTkFrame(self, height=50, fg_color="#2770CB", corner_radius=10)
        self.hero_header_bar.pack(side="top", fill="x", padx=16, pady=(20, 10))
        self.hero_header_label = ctk.CTkLabel(self.hero_header_bar, text="용병 조작키 설정", 
                                         font=("Arial", 16, "bold"), text_color="white")
        self.hero_header_label.place(relx=0.5, rely=0.5, anchor="center")

        # 3. 하단 캐릭터 슬롯 구역 (스크롤 가능)
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=820, height=500, fg_color="transparent")
        self.scroll_frame.pack(pady=5, padx=16, fill="both", expand=True)
        for c in range(6): self.scroll_frame.grid_columnconfigure(c, weight=1)

        self.bind("<MouseWheel>", self._on_mousewheel)
        self.sync_all_bindings()
        self.setup_soldier_slots()


    def _on_mousewheel(self, event):
        speed_multiplier = 100
        scroll_units = int(-1 * (event.delta / 120) * speed_multiplier)
        self.scroll_frame._parent_canvas.yview_scroll(scroll_units, "units")

    def sync_all_bindings(self):
        """[신규] .ini 로드 시 현재 모든 조작 설정을 메인 오버레이 바인딩에 동기화합니다."""
        # 기존에 등록된 기본 조작 아이콘들만 선별적으로 제거 (용병 아이콘은 유지하기 위함)
        basic_filenames = set(BASIC_ICON_MAP.values())
        keys_to_remove = [k for k, v in self.parent.key_bindings.items() 
                          if os.path.basename(v) in basic_filenames]
        
        for k in keys_to_remove:
            self.parent.key_bindings.pop(k, None)

        # 방향키 기호 매핑
        dir_symbols = {"UP": "↑", "DOWN": "↓", "LEFT": "←", "RIGHT": "→",
                       "LEFTUP": "↖", "RIGHTUP": "↗", "LEFTDOWN": "↙", "RIGHTDOWN": "↘"}

        for ini_key, vk_str in self.all_key_data.items():
            key_name = get_lostsaga_key_name(vk_str).lower()
            if ini_key in BASIC_ICON_MAP:
                self.parent.key_bindings[key_name] = f"./resource/img/{BASIC_ICON_MAP[ini_key]}"
            elif ini_key in dir_symbols:
                # 방향키 설정인 경우 특수 접두사 "DIR:"와 함께 기호를 저장합니다.
                self.parent.key_bindings[key_name] = f"DIR:{dir_symbols[ini_key]}"
        
        self.parent.refresh_ui()
        self.parent.save_config()

    def setup_soldier_slots(self):
        """하단 스크롤 영역에 1~50번 용병 슬롯을 배치합니다."""
        cols = 6
        for i in range(1, 51):
            ini_key = f"SOLDIER{i}"
            row = (i-1)//cols
            col = (i-1)%cols
            self.create_slot_logic(self.scroll_frame, ini_key, "soldier", row, col)

    def setup_basic_skill_slots(self):
        """[수정] 기본 조작 및 스킬 슬롯을 2행으로 구성하고 중앙 정렬합니다."""
        # 1행: 점프 / 방어 / 공격용 컨테이너 (자동 중앙 정렬)
        row1_container = ctk.CTkFrame(self.top_section, fg_color="transparent")
        row1_container.pack(side="top", pady=5) 
        
        row1_keys = [
            ("JUMP", "점프", "jump"), 
            ("DEFENSE", "방어", "guard"), 
            ("ATTACK", "공격", "attack")
        ]
        
        # 2행: 망토 / 투구 / 갑옷 / 무기용 컨테이너 (자동 중앙 정렬)
        row2_container = ctk.CTkFrame(self.top_section, fg_color="transparent")
        row2_container.pack(side="top", pady=5)
        
        row2_keys = [
            ("CLOAK_SKILL", "망토", "trinket"), 
            ("HELM_SKILL", "투구", "helmet"), 
            ("ARMOR_SKILL", "갑옷", "armor"), 
            ("WEAPON_SKILL", "무기", "weapon")
        ]

        # 1행 배치 (row1_container 내부 0열부터 시작)
        for i, (ini_key, name, icon_id) in enumerate(row1_keys):
            self.create_slot_logic(row1_container, ini_key, name, 0, i, icon_id)

        # 2행 배치 (row2_container 내부 0열부터 시작)
        for i, (ini_key, name, icon_id) in enumerate(row2_keys):
            self.create_slot_logic(row2_container, ini_key, name, 0, i, icon_id)

    def create_slot_logic(self, parent_frame, ini_key, display_label, row, col, default_icon_id=None):
        """[수정] 중앙 상단 레이블 및 이미지 버튼 클릭 시 콘솔 출력 적용"""
        raw_val = self.all_key_data.get(ini_key, "0")
        key_id = get_lostsaga_key_name(raw_val)
        target_key = key_id.lower()
        
        # 슬롯 프레임 생성
        slot_frame = ctk.CTkFrame(parent_frame, width=115, height=130, fg_color="#2b2b2b", 
                                  border_color="#A0A0A0", border_width=2, corner_radius=8)
        slot_frame.grid(row=row, column=int(col), padx=5, pady=5)
        slot_frame.grid_propagate(False)

        # 할당된 키 표시 이름 계산
        mapping = {"numpad_add": "NUM+", "numpad_div": "NUM /", "numpad_mul": "NUM *", "numpad_sub": "NUM -", "numpad_dot": "NUM .", "numpad_enter": "N_ENT", "page_up": "PG_UP", "page_down": "PG_DOWN", "caps_lock": "CAPSLOCK"}
        key_display = mapping.get(target_key, key_id.replace("numpad_", "NUM ").upper())

        if default_icon_id:
            # [기본 및 스킬 슬롯 전용 디자인]
            # 1. 중앙 상단 파란색 박스 (기능명 + 할당 키 값)
            label_text = f"{display_label} ({key_display})"
            # 박스 너비를 텍스트 길이에 맞춰 약간 확장
            label_box = ctk.CTkFrame(slot_frame, width=105, height=25, fg_color="#2770CB", corner_radius=4)
            label_box.place(relx=0.5, y=6, anchor="n") # 중앙 상단 배치
            ctk.CTkLabel(label_box, text=label_text, font=("Arial", 10, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

            # 2. 중앙 이미지 로드 (전역 캐시 활용)
            icon_file = f"basic_icon_{default_icon_id}.png"
            display_img = None
            if icon_file in self.parent.image_cache:
                pil_img = self.parent.image_cache[icon_file]
                display_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(65, 65))

            # 3. 중앙 이미지 버튼 (클릭 시 콘솔에 'OK' 출력)
            btn = ctk.CTkButton(slot_frame, text="" if display_img else display_label, image=display_img, 
                            width=75, height=75, fg_color="transparent", hover_color="#3d3d3d",
                            command=lambda k=ini_key, n=display_label: self.open_key_capture(k, n))
            btn.place(relx=0.5, rely=0.6, anchor="center")

        else:
            # [기존 용병 슬롯 디자인]
            if display_label == "soldier":
                display_label = key_display
            
            label_box = ctk.CTkFrame(slot_frame, width=55, height=25, fg_color="#2770CB", corner_radius=4)
            label_box.place(x=6, y=6)
            ctk.CTkLabel(label_box, text=display_label, font=("Arial", 10, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

            img_path = self.parent.key_bindings.get(target_key)
            display_img = None
            if img_path:
                filename = os.path.basename(img_path)
                if filename in self.parent.image_cache:
                    pil_img = self.parent.image_cache[filename]
                    display_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(65, 65))

            btn = ctk.CTkButton(slot_frame, text="+" if not display_img else "", image=display_img, 
                                width=75, height=75, fg_color="transparent", hover_color="#3d3d3d",
                                command=lambda k=key_id: self.open_gallery_for_slot(k))
            btn.place(relx=0.5, rely=0.6, anchor="center")

        # UI 갱신을 위해 슬롯 정보 저장
        self.slot_containers[ini_key] = {
            'frame': slot_frame, 'parent': parent_frame, 'label': display_label, 
            'row': row, 'col': col, 'icon_id': default_icon_id
        }

    def open_key_capture(self, ini_key, display_name):
        """키 입력 대기 팝업을 엽니다."""
        KeyCapturePopup(self, ini_key, display_name, self.update_key_value)

    def update_key_value(self, ini_key, new_vk_str):
        """[수정] 키 값이 변하면 데이터를 업데이트하고 전체 동기화를 실행합니다."""
        # 1. 데이터 업데이트
        self.all_key_data[ini_key] = new_vk_str
        
        # 2. 메인 오버레이와 동기화 실행 (기존 잔상 제거 및 새 위치 할당 포함)
        self.sync_all_bindings()
        
        # 3. 현재 팝업창의 해당 슬롯 UI 갱신
        info = self.slot_containers.get(ini_key)
        if info:
            info['frame'].destroy()
            self.create_slot_logic(info['parent'], ini_key, info['label'], info['row'], info['col'], info['icon_id'])
            self.update_idletasks()
        
        print(f"설정 변경 반영 완료: {ini_key} -> {get_lostsaga_key_name(new_vk_str)}")

    def open_gallery_for_slot(self, key_val):
        """이미지 갤러리 팝업을 엽니다."""
        from app import ImageGalleryPopup 
        ImageGalleryPopup(self, key_val, self.update_slot_image)

    def refresh_specific_slot(self, key_id):
        """[신규] 특정 키(예: 'a')와 연동된 모든 슬롯의 UI를 새로고침하여 이미지를 제거/업데이트합니다."""
        target_key = key_id.lower()
        for ini_key, info in self.slot_containers.items():
            raw_val = self.all_key_data.get(ini_key, "0")
            # 현재 슬롯의 할당 키가 대상 키와 일치하면 해당 슬롯만 다시 그립니다.
            if get_lostsaga_key_name(raw_val).lower() == target_key:
                info['frame'].destroy()
                self.create_slot_logic(info['parent'], ini_key, info['label'], 
                                       info['row'], info['col'], info['icon_id'])
        self.update_idletasks()

    def update_slot_image(self, key_val, image_path):
        """[수정] 이미지 선택 후 해당 키를 사용하는 모든 슬롯을 갱신합니다."""
        target_key = key_val.lower()
        self.parent.bind_image_to_key(target_key, image_path) # 메인 오버레이 데이터 변경
        self.refresh_specific_slot(target_key) # 현재 설정 창의 슬롯 UI 갱신

    def destroy(self):
        self.unbind("<MouseWheel>")
        super().destroy()

class AccountSelectionPopup(ctk.CTkToplevel):
    """디자인이 통일된 계정 선택 팝업 - 설치 경로 찾기 버튼 추가 버전"""
    def __init__(self, parent, game_path):
        super().__init__(parent)
        self.parent = parent
        self.title("계정 선택")
        self.geometry("400x550")
        self.configure(fg_color="#E7E7E7")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        # 1. 헤더 바 생성
        self.header_bar = ctk.CTkFrame(self, height=50, fg_color="#2770CB", corner_radius=10)
        self.header_bar.pack(side="top", fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(self.header_bar, text="계정 선택 (Account Selection)", 
                     font=("Arial", 16, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        # 2. 스크롤 프레임 생성
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=360, height=400, fg_color="transparent")
        self.scroll_frame.pack(pady=10, padx=15, fill="both", expand=True)

        # 3. 최근 계정 확인 및 초기 목록 로드
        if self.parent.last_account: 
            self.after(100, self.check_recent_account, self.parent.game_path)
        
        self.load_accounts(self.parent.game_path)
        
    def check_recent_account(self, game_path):
        if messagebox.askyesno("최근 계정 확인", f"최근 계정 '{self.parent.last_account}'을(를) 사용하시겠습니까?"):
            self.on_account_select(self.parent.last_account, game_path)

    def on_account_select(self, account_name, game_path):
        """계정 선택 시 customkey.ini에서 용병 및 기본/스킬 키 데이터를 추출합니다."""
        ini_path = os.path.join(game_path, "Save", account_name, "customkey.ini")
        if not os.path.exists(ini_path):
            messagebox.showerror("파일 오류", "customkey.ini를 찾을 수 없습니다.")
            return

        self.parent.update_last_account(account_name)
        content = ""
        # 인코딩 오류 방지를 위한 다중 시도
        for enc in ['cp949', 'utf-16', 'utf-8']:
            try:
                with open(ini_path, 'r', encoding=enc) as f: 
                    content = f.read()
                    break
            except: 
                continue

        # [Key] 섹션 찾기
        key_section_start = content.find("[Key]")
        if key_section_start != -1:
            content = content[key_section_start:]
            config = configparser.ConfigParser(strict=False)
            config.read_string(content)
            
            # 1. SOLDIER1~50 데이터 추출
            all_key_data = {
                f"SOLDIER{i}": config.get('Key', f"SOLDIER{i}") 
                for i in range(1, 51) 
                if config.has_option('Key', f"SOLDIER{i}")
            }
            
            # 2. 기본 조작 및 스킬 키 목록 정의
            extra_keys = [
                "ATTACK", "DEFENSE", "JUMP", 
                "CLOAK_SKILL", "HELM_SKILL", "ARMOR_SKILL", "WEAPON_SKILL",
                "UP", "DOWN", "LEFT", "RIGHT", "LEFTUP", "RIGHTUP", "LEFTDOWN", "RIGHTDOWN"
            ]
            
            # 3. 추가 키 데이터 추출
            for key in extra_keys:
                if config.has_option('Key', key):
                    all_key_data[key] = config.get('Key', key)

            # 팝업 닫고 결과 데이터를 InGameKeyConfigPopup으로 전달
            self.destroy()
            InGameKeyConfigPopup(self.parent, all_key_data)
        else: 
            messagebox.showerror("섹션 오류", "[Key] 섹션을 찾을 수 없습니다.")

    def browse_and_refresh(self):
        """[신규] 파일 탐색기를 열어 경로를 수정하고 목록을 새로고침합니다."""
        path = filedialog.askdirectory(title="로스트사가 설치 폴더 선택", initialdir=self.parent.game_path)
        if path:
            new_path = os.path.normpath(path)
            self.parent.game_path = new_path
            self.parent.save_config() # config.json 업데이트
            self.load_accounts(new_path) # 새 경로로 목록 다시 부르기

    def load_accounts(self, game_path):
        """[수정] 경로 내 Save 폴더 유무에 따라 목록 또는 경로 찾기 버튼을 표시합니다."""
        # 기존 목록 초기화
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        save_path = os.path.join(game_path, "Save")
        
        if os.path.exists(save_path):
            # Save 폴더가 있을 때: 계정 목록 출력
            accounts = [d for d in os.listdir(save_path) 
                        if os.path.isdir(os.path.join(save_path, d)) and d.lower() != "default"]
            
            if not accounts:
                ctk.CTkLabel(self.scroll_frame, text="계정 데이터를 찾을 수 없습니다.", text_color="#555555").pack(pady=20)
            
            for acc in accounts:
                ctk.CTkButton(self.scroll_frame, text=acc, height=40, fg_color="#2b2b2b", 
                              command=lambda a=acc: self.on_account_select(a, game_path)).pack(pady=5, padx=10, fill="x")
        else:
            # [핵심 추가] Save 폴더가 없을 때: 설치 경로 찾기 버튼 배치
            ctk.CTkLabel(self.scroll_frame, text="로스트사가 설치 경로가 지정되지 않았습니다.\n로스트사가 설치 경로를 다시 지정해주세요.\n(Save 폴더가 보여야만 합니다.)", 
                         text_color="#A12F2F", font=("Arial", 13)).pack(pady=(20, 10))
            
            ctk.CTkButton(self.scroll_frame, text="로스트사가 설치 경로 찾기", 
                          fg_color="#2770CB", hover_color="#1f538d",
                          command=self.browse_and_refresh).pack(pady=10, padx=20)

    def destroy(self):
        self.grab_release()
        super().destroy()

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
    """[수정] 리소스 전역 캐싱 최적화가 적용된 메인 오버레이 클래스"""
    def __init__(self, config_path="./config.json"):
        super().__init__()
        self.config_file = config_path 
        self.image_cache = {}  # 파일명: 리사이즈된 PIL.Image 객체
        self.char_data = {}    # data.json 파싱 데이터
        
        # 1. 프로그램 실행 시 리소스 미리 불러오기
        self.preload_resources()
        
        self.modes = {
            "full": {"w": 1040, "h": 320}, 
            "tkl": {"w": 840, "h": 320},
            "minimal_tkl": {"w": 350, "h": 120},
            "minimal_full": {"w": 350, "h": 155} # 3x3 배치를 위해 세로 크기 조정
        }
        self.current_mode = "full"
        # self.min_width_limit = 600
        # self.current_alpha = 0.85
        self.current_alpha = 1.00
        self.pre_edit_alpha = 1.00 
        self.scale_factor = 1.0
        self.start_drag_x_root = 0
        self.start_drag_y_root = 0
        self.resizing = False
        # self.resize_edge = None
        self.base_key_size = 42
        self.edit_mode = False
        self.always_on_top = True
        self.resizable(False, False)
        mode = self.modes[self.current_mode]
        self.aspect_ratio = mode['w'] / mode['h']
        self.title("LostSaga KeyboardViewer")

        # [수정] overrideredirect를 False로 설정하여 정식 윈도우로 등록
        self.overrideredirect(False)
        # 초기화 시 타이틀 바 숨김 적용
        self.after(10, lambda: self._update_window_style(False))
        # Win32 API를 사용하여 타이틀 바(Caption)만 강제로 제거
        # 이를 통해 작업 표시줄 아이콘은 유지하면서 테두리 없는 창을 만듭니다.
        GWL_STYLE = -16
        WS_CAPTION = 0x00C00000
        # 윈도우 핸들(HWND) 가져오기
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        # 현재 스타일 가져오기
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        # 타이틀 바 스타일 비트 제거
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~WS_CAPTION)
        
        config_data = self.load_config()
        self.key_bindings = config_data.get("key_bindings", {
            "a": "./resource/img/basic_icon_jump.png",
            "s": "./resource/img/basic_icon_guard.png",
            "d": "./resource/img/basic_icon_attack.png",
            "q": "./resource/img/basic_icon_trinket.png",
            "w": "./resource/img/basic_icon_helmet.png",
            "e": "./resource/img/basic_icon_armor.png",
            "r": "./resource/img/basic_icon_weapon.png"}
        )
        self.saved_bindings = self.key_bindings.copy()
        self.game_path = config_data.get("game_path", r"C:\program files\Lostsaga")
        self.last_account = config_data.get("last_account", "")
        
        self.geometry(f"{self.modes[self.current_mode]['w']}x{self.modes[self.current_mode]['h']}")
        self.attributes("-topmost", True)
        self.attributes("-alpha", self.current_alpha) 
        # self.overrideredirect(True)                  
        self.configure(fg_color="#1a1a1a")      
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.context_menu = None
        self.bind("<Button-3>", self.show_menu)
        self.bind("<Motion>", self.check_edge)
        self.bind("<ButtonPress-1>", self.on_button_press)
        self.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<B1-Motion>", self.handle_mouse_action)
        self.bind("<FocusIn>", lambda e: None)
        self.bind("<FocusOut>", lambda e: None)
        
        self.use_transparent_bg = False
        self.transparent_color = "#121212" # 투명으로 처리할 고유 색상
        # 초기 배경 설정 적용
        if self.use_transparent_bg:
            self.configure(fg_color=self.transparent_color)
            self.attributes("-transparentcolor", self.transparent_color)
        else:
            self.configure(fg_color="#1a1a1a")
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=0)
        self.main_frame.pack(expand=True, fill="both")
        self.buttons = {}
        self.create_context_menu()
        self.setup_layout()
        # [핵심] 윈도우 배치를 완료한 뒤 정확한 비율을 계산합니다.
        self.update_idletasks()
        # self.aspect_ratio = self.winfo_width() / self.winfo_height()
        
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release, win32_event_filter=self.win32_filter)
        self.listener.daemon = True 
        self.listener.start()
    
    def preload_resources(self):
        """[핵심] 디스크 부하를 줄이기 위해 모든 이미지와 데이터를 메모리에 적재"""
        # data.json 로드
        json_path = resource_path("./resource/data.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="euc-kr") as f:
                    self.char_data = json.load(f)
            except: pass

        # 이미지 폴더 캐싱
        img_dir = resource_path("./resource/img/")
        if os.path.exists(img_dir):
            for file in os.listdir(img_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    path = os.path.join(img_dir, file)
                    try:
                        with Image.open(path) as img:
                            # 128x128로 미리 리사이즈하여 보관 (품질과 성능의 균형)
                            cached = img.resize((128, 128), Image.LANCZOS).convert("RGBA")
                            self.image_cache[file] = cached
                    except: continue

    def on_closing(self):
        """프로그램 종료 시 리소스 점유를 확실히 해제하여 임시 폴더 삭제 오류를 방지합니다."""
        # 1. 편집 모드일 경우 모드 해제 로직 수행
        if self.edit_mode: 
            self.toggle_edit_mode()
            # 편집 모드 해제 후 바로 종료되지 않게 하려면 여기서 return을 하거나 
            # 아래 저장 확인 로직으로 넘어가도록 구성합니다.

        # 2. 저장되지 않은 내용 확인
        if self.key_bindings != self.saved_bindings:
            if not messagebox.askyesno("종료 확인", "변경사항이 저장되지 않았습니다.\n종료하시겠습니까?"):
                return
        
        # 3. [핵심] 키보드 리스너 쓰레드를 명시적으로 정지
        if hasattr(self, 'listener') and self.listener:
            self.listener.stop()
            
        # 4. 모든 팝업 및 창 리소스 해제 후 종료
        self.quit()    # 이벤트 루프 중지
        self.destroy() # 창 파괴

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f: return json.load(f)
            except: pass
        return {"game_path": r"C:\program files\Lostsaga", "last_account": "", "key_bindings": {}}
    
    def load_config_from_file(self):
        filename = filedialog.askopenfilename(title="설정 파일 불러오기", filetypes=[("JSON files", "*.json")])
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    new_data = json.load(f)
                    self.key_bindings = new_data.get("key_bindings", {})
                    self.config_file = filename 
                    self.saved_bindings = self.key_bindings.copy()
                    self.refresh_ui(); self.create_context_menu() 
                    # messagebox.showinfo("불러오기 완료", f"'{os.path.basename(filename)}' 파일을 불러왔습니다.")
            except: messagebox.showerror("오류", "파일을 불러오는 중 오류가 발생했습니다.")

    def update_last_account(self, account_name):
        self.last_account = account_name
        config_data = self.load_config()
        config_data["last_account"] = account_name
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
        except: pass

    def save_config(self, filename=None):
        target = filename if filename else self.config_file
        data = {"key_bindings": self.key_bindings, "game_path": self.game_path, "last_account": self.last_account}
        try:
            with open(target, "w", encoding="utf-8") as f: 
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.saved_bindings = self.key_bindings.copy()
            self.config_file = target 
            messagebox.showinfo("저장 완료", f"'{os.path.basename(target)}'에 저장을 완료했습니다.")
            self.create_context_menu() 
            return True
        except: return False

    def save_config_as(self):
        filename = filedialog.asksaveasfilename(initialdir=os.getcwd(), defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filename: return self.save_config(filename)
        return False

    def revert_changes(self):
        if messagebox.askyesno("변경사항 초기화", "저장되지 않은 변경사항을 취소하시겠습니까?"):
            self.key_bindings = self.saved_bindings.copy(); self.refresh_ui()

    def toggle_always_on_top(self):
        """항상 위 표시 모드를 토글합니다."""
        self.always_on_top = not self.always_on_top
        self.attributes("-topmost", self.always_on_top)
        self.create_context_menu() # 메뉴 텍스트 갱신

    def toggle_background_transparency(self):
        """배경 투명화 모드를 토글합니다."""
        self.use_transparent_bg = not self.use_transparent_bg
        if self.use_transparent_bg:
            self.configure(fg_color=self.transparent_color)
            self.attributes("-transparentcolor", self.transparent_color)
        else:
            self.attributes("-transparentcolor", "") # 투명 속성 제거
            self.configure(fg_color="#1a1a1a") # 원래 배경색 복구
        self.create_context_menu() # 메뉴 체크 표시 갱신

    def minimize_window(self):
        """프로그램을 최소화합니다."""
        self.iconify()

    def create_context_menu(self):
        if self.context_menu: self.context_menu.destroy()
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", borderwidth=0)
        has_changes = (self.key_bindings != self.saved_bindings)
        save_prefix = "* " if has_changes else "  "
        fname = os.path.basename(self.config_file)

        layout_menu = tk.Menu(self.context_menu, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d")
        layout_menu.add_command(label=f"  {'• ' if self.current_mode == 'full' else '   '}풀 배열 (Full)", command=lambda: self.switch_layout("full"))
        layout_menu.add_command(label=f"  {'• ' if self.current_mode == 'tkl' else '   '}텐키리스 (TKL)", command=lambda: self.switch_layout("tkl"))
        layout_menu.add_command(label=f"  {'• ' if self.current_mode == 'minimal_full' else '   '}최소-풀배열 (Minimal Full)", command=lambda: self.switch_layout("minimal_full"))
        layout_menu.add_command(label=f"  {'• ' if self.current_mode == 'minimal_tkl' else '   '}최소-텐키리스 (Minimal TKL)", command=lambda: self.switch_layout("minimal_tkl"))
        self.context_menu.add_cascade(label="  키보드 레이아웃 설정", menu=layout_menu)

        if self.edit_mode: self.context_menu.add_command(label="  직접 편집 완료하기", command=self.toggle_edit_mode)
        else:
            self.context_menu.add_separator()
            img_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d")
            img_menu.add_command(label="  인게임 설정으로 편집하기", command=lambda: AccountSelectionPopup(self, self.game_path))
            img_menu.add_command(label="  직접 편집하기", command=self.toggle_edit_mode)
            self.context_menu.add_cascade(label="  용병 아이콘 설정", menu=img_menu)
            self.context_menu.add_command(label="  키보드 투명도 설정 열기", command=self.open_slider_window)
            # self.context_menu.add_command(label="  모든 설정 완전 초기화", command=self.reset_all_settings)
            bg_trans_prefix = "• " if self.use_transparent_bg else "  "
            self.context_menu.add_command(label=f"{bg_trans_prefix}배경을 투명하게 표시", 
                                        command=self.toggle_background_transparency)
            topmost_prefix = "• " if self.always_on_top else "  "
            self.context_menu.add_command(label=f"{topmost_prefix}항상 위에 표시", command=self.toggle_always_on_top)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="  현재 상태 캡쳐하기", command=self.capture_current_state)
            self.context_menu.add_separator()
            if has_changes: self.context_menu.add_command(label="  변경사항 초기화하기", command=self.revert_changes)
            self.context_menu.add_command(label=f"{save_prefix}설정을 {fname}에 저장하기", command=self.save_config)
            self.context_menu.add_command(label=f"{save_prefix}설정을 다른 이름으로 저장", command=self.save_config_as)
            self.context_menu.add_command(label="  기존 설정 파일 불러오기", command=self.load_config_from_file)
            self.context_menu.add_separator()
            # [추가] 윈도우 제어 옵션
            self.context_menu.add_command(label="  최소화", command=self.minimize_window)
            self.context_menu.add_command(label="  종료", command=self.on_closing)

    def open_slider_window(self):
        """투명도 설정 팝업 열기"""
        TransparencySettings(self)

    def reset_all_settings(self):
        """모든 키 바인딩 설정을 삭제하고 초기화합니다."""
        if messagebox.askyesno("설정 초기화", "모든 키 바인딩 설정을 초기화하시겠습니까?\n(이미지 정보가 모두 사라집니다.)"):
            self.key_bindings = {
                "a": "./resource/img/basic_icon_jump.png",
                "s": "./resource/img/basic_icon_guard.png",
                "d": "./resource/img/basic_icon_attack.png",
                "q": "./resource/img/basic_icon_trinket.png",
                "w": "./resource/img/basic_icon_helmet.png",
                "e": "./resource/img/basic_icon_armor.png",
                "r": "./resource/img/basic_icon_weapon.png"
            }
            self.refresh_ui()
            messagebox.showinfo("초기화 완료", "모든 설정이 초기화되었습니다.")

    def set_game_directory(self):
        path = filedialog.askdirectory(title="로스트사가 설치 폴더 선택", initialdir=self.game_path)
        if path:
            self.game_path = os.path.normpath(path)
            self.save_config()

    def toggle_edit_mode(self):
        mode = self.modes[self.current_mode] # 현재 모드 설정값 가져오기
        if self.edit_mode:
            # [편집 모드 종료 -> 일반 모드로]
            self.withdraw()
            self._update_window_style(False) # 타이틀 바 제거
            self.geometry(f"{mode['w']}x{mode['h']}")
            self.set_transparency(self.pre_edit_alpha)
            self.configure(fg_color="#1a1a1a")
            self.title("LostSaga KeyboardViewer")
            self.deiconify()
        else:
            # [일반 모드 종료 -> 편집 모드로]
            self.withdraw()
            self.pre_edit_alpha = self.current_alpha
            self._update_window_style(True)  # 타이틀 바 복구
            self.geometry(f"{mode['w']}x{mode['h'] + 40}")
            self.set_transparency(1.0)
            self.configure(fg_color="#2a1a1a")
            self.title("직접 편집 모드 - 키를 클릭하여 수정하세요")
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
        # self.scale_factor = 1.0
        self.update_idletasks()
        self.aspect_ratio = mode['w'] / mode['h']
        self.refresh_ui()

    def reset_to_original_size(self):
        mode = self.modes[self.current_mode]
        self.geometry(f"{mode['w']}x{mode['h']}")
        # self.scale_factor = 1.0
        self.update_idletasks()
        self.aspect_ratio = mode['w'] / mode['h']
        self.refresh_ui()

    def check_edge(self, event):
        """[복구] 마우스 위치에 따른 리사이징 방향 감지 및 커서 변경"""
        if self.resizing: return
        
        x = self.winfo_pointerx() - self.winfo_rootx()
        y = self.winfo_pointery() - self.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        
        margin = 15 
        at_top, at_bottom = y < margin, y > h - margin
        at_left, at_right = x < margin, x > w - margin
        
        if at_top and at_left: self.resize_edge = "nw"; self.config(cursor="size_nw_se")
        elif at_top and at_right: self.resize_edge = "ne"; self.config(cursor="size_ne_sw")
        elif at_bottom and at_left: self.resize_edge = "sw"; self.config(cursor="size_ne_sw")
        elif at_bottom and at_right: self.resize_edge = "se"; self.config(cursor="size_nw_se")
        elif at_top: self.resize_edge = "n"; self.config(cursor="size_ns")
        elif at_bottom: self.resize_edge = "s"; self.config(cursor="size_ns")
        elif at_left: self.resize_edge = "w"; self.config(cursor="size_we")
        elif at_right: self.resize_edge = "e"; self.config(cursor="size_we")
        else:
            self.resize_edge = None
            self.config(cursor="")

    def _update_window_style(self, show_caption=False):
        """[수정] 리사이징 테두리(WS_THICKFRAME)를 다시 활성화합니다."""
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        
        if show_caption:
            # WS_CAPTION(0x00C00000)과 WS_THICKFRAME(0x00040000) 모두 활성화
            new_style = ctypes.windll.user32.GetWindowLongW(hwnd, -16) | 0x00C00000 | 0x00040000
        else:
            # 일반 모드에서도 리사이징이 가능하도록 WS_POPUP과 WS_THICKFRAME 조합
            new_style = 0x80000000 | 0x00040000
            
        ctypes.windll.user32.SetWindowLongW(hwnd, -16, new_style)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0004)

    def on_focus_in(self, event):
        """[수정] 포커스 시 테두리 두께가 변하지 않도록 색상만 변경합니다."""
        self.main_frame.configure(border_color="white") # 혹은 선호하는 색상 (#2770CB 등)

    def on_focus_out(self, event):
        self.main_frame.configure(border_color="#1a1a1a")

    def on_button_press(self, event):
        # [수정] 리사이징 시작 여부 판단 추가
        if self.resize_edge:
            self.resizing = True
            self.start_x_root, self.start_y_root = event.x_root, event.y_root
            self.start_geom = (self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())
        else:
            self.start_drag_x_root = event.x_root
            self.start_drag_y_root = event.y_root
            self.start_win_x = self.winfo_x()
            self.start_win_y = self.winfo_y()

    def on_button_release(self, event):
        self.resizing = False # 리사이징 종료 시 상태만 리셋

    def handle_mouse_action(self, event):
        """[수정] 리사이징 시 내부 크기는 무시하고 창 크기만 조절합니다."""
        if self.resizing:
            orig_x, orig_y, orig_w, orig_h = self.start_geom
            dx = event.x_root - self.start_x_root
            dy = event.y_root - self.start_y_root
            
            new_w = orig_w + (dx if "e" in self.resize_edge else -dx if "w" in self.resize_edge else 0)
            new_h = orig_h + (dy if "s" in self.resize_edge else -dy if "n" in self.resize_edge else 0)
            
            # 최소 크기 제한 (키보드가 하나도 안 보일 정도는 아니게)
            new_w = max(100, new_w)
            new_h = max(50, new_h)
            
            new_x = orig_x + (orig_w - new_w) if "w" in self.resize_edge else orig_x
            new_y = orig_y + (orig_h - new_h) if "n" in self.resize_edge else orig_y
            
            # [중요] refresh_ui를 호출하지 않고 창 크기만 변경합니다.
            self.geometry(f"{int(new_w)}x{int(new_h)}+{int(new_x)}+{int(new_y)}")
        else:
            dx = event.x_root - self.start_drag_x_root
            dy = event.y_root - self.start_drag_y_root
            self.geometry(f"+{self.start_win_x + dx}+{self.start_win_y + dy}")

    def create_key(self, parent, text, row, col, width=None, height=None, columnspan=1, rowspan=1, key_code=None):
        """[수정] Minimal 모드 시 방향키는 텍스트를, 나머지는 고정 이미지를 출력함"""
        k_w = (width if width else self.base_key_size) * self.scale_factor
        k_h = (height if height else self.base_key_size) * self.scale_factor
        target_id = key_code if key_code else text.lower()
        display_text = text
        img_obj = None

        # [방향키 정의] 텍스트 출력을 강제할 키 목록
        dir_keys = ["up", "down", "left", "right", "home", "end", "page_up", "page_down", "clear",
                    "numpad_0", "numpad_1", "numpad_2", "numpad_3", "numpad_4", "numpad_5", 
                    "numpad_6", "numpad_7", "numpad_8", "numpad_9"]
        minimal_fixed = {
            "q": "basic_icon_trinket.png", "w": "basic_icon_helmet.png", "e": "basic_icon_armor.png", "r": "basic_icon_weapon.png",
            "a": "basic_icon_jump.png", "s": "basic_icon_guard.png", "d": "basic_icon_attack.png"
        }
        # 바인딩 확인
        binding_val = self.key_bindings.get(target_id, "")
        
        filename = None
        if binding_val.startswith("DIR:"):
            # 인게임 설정에 의해 방향키로 지정된 경우 화살표 출력
            display_text = binding_val.split(":")[1]
            filename = None
        elif self.current_mode.startswith("minimal"):
            if target_id in dir_keys:
                # 방향키는 이미지를 할당하지 않아 텍스트(↑ 등)가 출력됨
                img_obj = None
            elif target_id in minimal_fixed:
                filename = minimal_fixed[target_id]
        elif target_id in self.key_bindings:
            filename = os.path.basename(self.key_bindings[target_id])
        elif binding_val:
            filename = os.path.basename(binding_val)

        if filename and filename in self.image_cache:
            pil_img = self.image_cache[filename]
            side = int(min(k_w, k_h) * 0.8) 
            img_obj = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(side, side))
            display_text = ""
        
        # 버튼 생성
        cmd = (lambda tid=target_id: ImageSelectionPopup(self, tid)) if self.edit_mode else None
        btn = ctk.CTkButton(parent, text=display_text, image=img_obj, width=k_w, height=k_h, 
                            fg_color="#333333", text_color="white", command=cmd, hover=self.edit_mode)
        btn.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan, padx=1, pady=1, sticky="nsew")
        self.buttons[target_id] = btn

    def setup_layout(self):
        s = self.base_key_size
        
        # 1. 메인 프레임의 행/열 가중치를 설정하여 중앙 정렬 기반 마련
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        # 2. 모든 키보드 요소를 담을 중앙 컨테이너 생성
        # sticky="" 설정을 통해 이 컨테이너 자체가 창의 정중앙에 위치함
        center_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        center_container.grid(row=0, column=0, sticky="")
        
        # [추가] 상하 중앙 정렬을 위해 0번 행에 가중치를 부여합니다.
        self.main_frame.grid_rowconfigure(0, weight=1)

        if self.current_mode.startswith("minimal"):
            left_frame = ctk.CTkFrame(center_container, fg_color="transparent")
            left_frame.pack(side="left", padx=10)
            
            # QWER / ASD 배치 로직
            for i, char in enumerate(["q", "w", "e", "r"]):
                self.create_key(left_frame, char.upper(), 0, i * 2, columnspan=2, key_code=char)
            for i, char in enumerate(["a", "s", "d"]):
                self.create_key(left_frame, char.upper(), 1, i * 2 + 1, columnspan=2, key_code=char)
                
            # 2. 방향키 영역
            arrow_frame = ctk.CTkFrame(center_container, fg_color="transparent")
            arrow_frame.pack(side="left", padx=10)

            if self.current_mode == "minimal_tkl":
                self.create_key(arrow_frame, "↑", 0, 1, key_code="up")
                self.create_key(arrow_frame, "←", 1, 0, key_code="left")
                self.create_key(arrow_frame, "↓", 1, 1, key_code="down")
                self.create_key(arrow_frame, "→", 1, 2, key_code="right")
            
            elif self.current_mode == "minimal_full":
                self.create_key(arrow_frame, "↖", 0, 0, key_code="numpad_7")
                self.create_key(arrow_frame, "↑", 0, 1, key_code="numpad_8")
                self.create_key(arrow_frame, "↗", 0, 2, key_code="numpad_9")
                self.create_key(arrow_frame, "←", 1, 0, key_code="numpad_4")
                self.create_key(arrow_frame, "↓", 1, 1, key_code="numpad_5")
                self.create_key(arrow_frame, "→", 1, 2, key_code="numpad_6")
                self.create_key(arrow_frame, "↙", 2, 0, key_code="numpad_1")
                self.create_key(arrow_frame, ".", 2, 1, key_code="numpad_2")
                self.create_key(arrow_frame, "↘", 2, 2, key_code="numpad_3")
        else:
            # content_cols = 3 if self.current_mode == "full" else 2
            # self.main_frame.grid_columnconfigure(0, weight=1); self.main_frame.grid_columnconfigure(content_cols + 1, weight=1)
            # self.main_frame.grid_rowconfigure(0, weight=1); self.main_frame.grid_rowconfigure(3, weight=1)
            # [수정] 빈 컬럼에 weight를 주는 대신, 실제 데이터가 들어가는 컬럼들이 확장되도록 설정
            for c in range(3): self.main_frame.grid_columnconfigure(c, weight=0)

            # 펑션 키 프레임
            f_frame = ctk.CTkFrame(center_container, fg_color="transparent")
            f_frame.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))# 1. Esc (4칸)
            self.create_key(f_frame, "Esc", 0, 0, width=s, columnspan=4)

            # 2. 여백 1: Esc와 F1 사이 (4칸)
            # [수정] 너비를 s * 1.0에서 1.2 정도로 미세하게 늘림
            ctk.CTkLabel(f_frame, text="", width=s * 1.0).grid(row=0, column=4, columnspan=4)

            # 3. F1 ~ F4 (16칸)
            for i in range(1, 5):
                self.create_key(f_frame, f"F{i}", 0, 4 + (i * 4), width=s, columnspan=4)

            # 4. 여백 2: F4와 F5 사이 (2칸)
            # [수정] 너비를 s * 0.5에서 0.65 정도로 미세하게 늘림
            ctk.CTkLabel(f_frame, text="", width=s * 0.65).grid(row=0, column=24, columnspan=2)

            # 5. F5 ~ F8 (16칸)
            for i in range(5, 9):
                self.create_key(f_frame, f"F{i}", 0, 26 + ((i-5) * 4), width=s, columnspan=4)

            # 6. 여백 3: F8과 F9 사이 (2칸)
            # [수정] 너비를 s * 0.5에서 0.65 정도로 미세하게 늘림
            ctk.CTkLabel(f_frame, text="", width=s * 0.65).grid(row=0, column=42, columnspan=2)

            # 7. F9 ~ F12 (16칸)
            for i in range(9, 13):
                self.create_key(f_frame, f"F{i}", 0, 44 + ((i-9) * 4), width=s, columnspan=4)
            
            # 메인 키 프레임
            m_frame = ctk.CTkFrame(center_container, fg_color="transparent")
            m_frame.grid(row=1, column=0, sticky="nw")
            # --- Row 0: 숫자열 (1키=4칸 기준, 총 60칸) ---
            for i, char in enumerate(["`","1","2","3","4","5","6","7","8","9","0","-","="]):
                self.create_key(m_frame, char, 0, i * 4, columnspan=4)
            self.create_key(m_frame, "Back", 0, 52, width=s*2, columnspan=8, key_code="backspace")

            # --- Row 1: QWERTY열 (Tab=1.5u=6칸) ---
            self.create_key(m_frame, "Tab", 1, 0, width=s*1.5, columnspan=6, key_code="tab")
            for i, char in enumerate(["q","w","e","r","t","y","u","i","o","p","[","]"]):
                self.create_key(m_frame, char.upper(), 1, 6 + (i * 4), columnspan=4, key_code=char)
            self.create_key(m_frame, "\\", 1, 6 + (12 * 4), width=s*1.5, columnspan=6, key_code=char)

            # --- Row 2: Caps Lock열 (Caps=1.75u=7칸 / Enter=2.25u=9칸) ---
            # [수정] Caps Lock을 1.75u로 설정하여 7칸 차지
            self.create_key(m_frame, "Caps", 2, 0, width=s*1.75, columnspan=7, key_code="caps_lock")
            for i, char in enumerate(["a","s","d","f","g","h","j","k","l",";","'"]):
                self.create_key(m_frame, char.upper(), 2, 7 + (i * 4), columnspan=4, key_code=char)
            self.create_key(m_frame, "Enter", 2, 51, width=s*2.25, columnspan=9, key_code="enter")

            # --- Row 3: Shift열 (L-Shift=2.25u=9칸 / R-Shift=2.25u=9칸) ---
            # [수정] Left Shift를 2.25u로 설정 (Caps Lock보다 0.5u 김)
            self.create_key(m_frame, "Shift", 3, 0, width=s*2.25, columnspan=9, key_code="shift")
            for i, char in enumerate(["z","x","c","v","b","n","m",",",".","/"]):
                self.create_key(m_frame, char.upper(), 3, 9 + (i * 4), columnspan=4, key_code=char)
            # [수정] Right Shift도 동일하게 2.25u로 설정
            self.create_key(m_frame, "Shift ", 3, 49, width=s*2.25, columnspan=11, key_code="shift_r")

            # --- Row 4: 하단 조작열 (1.25u~1.5u 기준 배치) ---
            self.create_key(m_frame, "Ctrl", 4, 0, width=s*1.25, columnspan=5, key_code="ctrl_l")
            self.create_key(m_frame, "Win", 4, 5, width=s*1.25, columnspan=5, key_code="cmd")
            self.create_key(m_frame, "Alt", 4, 10, width=s*1.25, columnspan=5, key_code="alt_l")
            self.create_key(m_frame, "SPACE", 4, 15, width=s*6.25, columnspan=30, key_code="space")
            self.create_key(m_frame, "Alt", 4, 45, width=s*1.25, columnspan=5, key_code="alt_gr")
            self.create_key(m_frame, "Ctx", 4, 50, width=s*1.25, columnspan=5, key_code="menu")
            self.create_key(m_frame, "Ctrl", 4, 55, width=s*1.25, columnspan=5, key_code="ctrl_r")

            # Numpad
            # 넘패드 및 기타 프레임들도 순차적으로 column 번호 조정
            # 방향키/인서트 프레임
            n_frame = ctk.CTkFrame(center_container, fg_color="transparent")
            n_frame.grid(row=1, column=1, sticky="n", padx=15)
            for r, row in enumerate([["insert", "home", "page_up"], ["delete", "end", "page_down"]]):
                for c, k in enumerate(row): self.create_key(n_frame, k[:3].upper(), r, c, key_code=k)
            a_frame = ctk.CTkFrame(n_frame, fg_color="transparent"); a_frame.grid(row=2, column=0, columnspan=3, pady=(s*self.scale_factor, 0))
            self.create_key(a_frame, "↑", 0, 1, key_code="up"); self.create_key(a_frame, "←", 1, 0, key_code="left"); self.create_key(a_frame, "↓", 1, 1, key_code="down"); self.create_key(a_frame, "→", 1, 2, key_code="right")
            if self.current_mode == "full":
                t_frame = ctk.CTkFrame(center_container, fg_color="transparent")
                t_frame.grid(row=1, column=2, sticky="nw")
                for r, row in enumerate([[("NL","num_lock"),("/","numpad_div"),("*","numpad_mul"),("-","numpad_sub")],[("7","numpad_7"),("8","numpad_8"),("9","numpad_9")],[("4","numpad_4"),("5","numpad_5"),("6","numpad_6")],[("1","numpad_1"),("2","numpad_2"),("3","numpad_3")]]):
                    for c, (txt, kid) in enumerate(row): self.create_key(t_frame, txt, r, c, key_code=kid)
                self.create_key(t_frame, "0", 4, 0, width=s*2, columnspan=2, key_code="numpad_0"); self.create_key(t_frame, ".", 4, 2, key_code="numpad_dot"); self.create_key(t_frame, "+", 1, 3, height=s*2, rowspan=2, key_code="numpad_add"); self.create_key(t_frame, "Ent", 3, 3, height=s*2, rowspan=2, key_code="numpad_enter")

    def capture_current_state(self):
        """[수정] 캡쳐 순간에만 투명도를 100%로 고정하여 선명한 이미지를 저장합니다."""
        try:
            # 1. 기본 파일명 생성 (현재 설정 파일명 기준)
            base_name = os.path.splitext(os.path.basename(self.config_file))[0]
            default_filename = f"{base_name}.png"

            # 2. 저장 경로 선택 (경로가 결정되기 전까지는 투명도 유지)
            file_path = filedialog.asksaveasfilename(
                initialfile=default_filename,
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
                title="키보드 레이아웃 캡쳐 저장"
            )

            if file_path:
                # [추가] 현재 설정된 투명도 임시 저장
                original_alpha = self.current_alpha
                
                # [추가] 캡쳐를 위해 불투명 상태(100%)로 변경
                self.set_transparency(1.0)
                # 윈도우 속성 변경을 즉시 적용하기 위해 강제 업데이트
                self.update() 
                
                # 3. 윈도우 영역 계산 및 캡쳐 실행
                self.update_idletasks()
                x = self.winfo_rootx()
                y = self.winfo_rooty()
                w = self.winfo_width()
                h = self.winfo_height()
                bbox = (x, y, x + w, y + h)

                # 실제 화면 캡쳐
                captured_image = ImageGrab.grab(bbox=bbox)
                captured_image.save(file_path)
                
                # [추가] 원래 설정했던 투명도로 자동 복구
                self.set_transparency(original_alpha)
                
                messagebox.showinfo("캡쳐 성공", f"캡쳐 성공 : {default_filename} 파일이 저장되었습니다.")
                
        except Exception as e:
            # 오류 발생 시에도 원래 투명도로 복구 시도
            if 'original_alpha' in locals():
                self.set_transparency(original_alpha)
            messagebox.showerror("캡쳐 실패", f"저장 중 오류가 발생했습니다: {e}")

    def win32_filter(self, msg, data): self.last_is_extended = bool(data.flags & 0x01); return True
    def on_press(self, key):
        k = self.parse_key(key)
        if k in self.buttons: self.buttons[k].configure(fg_color="#1f538d")
    def on_release(self, key):
        k = self.parse_key(key)
        if k in self.buttons: self.buttons[k].configure(fg_color="#333333")
    def parse_key(self, key):
        """[수정] 확장 키 플래그를 확인하여 일반 방향키와 넘패드 방향키를 정확히 구분합니다."""
        try:
            vk = getattr(key, 'vk', None)
            
            # 1. 엔터키 구분 (기존 로직)
            if key == keyboard.Key.enter: 
                return "numpad_enter" if self.last_is_extended else "enter"
            
            # 2. 넘락(Num Lock)이 켜져 있을 때의 가상 키 매핑 (기존 로직)
            vk_map = {
                12:"numpad_5",
                96:"numpad_0", 97:"numpad_1", 98:"numpad_2", 99:"numpad_3", 100:"numpad_4", 
                101:"numpad_5", 102:"numpad_6", 103:"numpad_7", 104:"numpad_8", 105:"numpad_9", 
                106:"numpad_mul", 107:"numpad_add", 109:"numpad_sub", 111:"numpad_div", 110:"numpad_dot", 144:"num_lock"
            }
            if vk in vk_map: return vk_map[vk]

            # 3. [핵심 추가] 확장 키 플래그가 없는 방향키/기능키는 넘패드로 처리합니다.
            k = str(key).replace('Key.', '').lower()
            
            # 넘패드 방향키와 전용 방향키 구분 매핑 테이블
            extended_map = {
                "up": "numpad_8", "down": "numpad_2", "left": "numpad_4", "right": "numpad_6",
                "home": "numpad_7", "end": "numpad_1", "page_up": "numpad_9", "page_down": "numpad_3",
                "insert": "numpad_0", "delete": "numpad_dot",
                "clear": "numpad_5"
            }
            
            # 확장 키가 아닌데(last_is_extended == False) 위 목록에 해당하면 넘패드 키입니다.
            if not self.last_is_extended and k in extended_map:
                return extended_map[k]

            if hasattr(key, 'char') and key.char: return key.char.lower()
            return k
        except: 
            return None
    def open_slider_window(self): TransparencySettings(self)
    def set_transparency(self, value): self.current_alpha = value; self.attributes("-alpha", value)
    def show_menu(self, event): self.create_context_menu(); self.context_menu.post(event.x_root, event.y_root)

def get_lostsaga_key_name(vk_code_str):
    try:
        vk = int(vk_code_str)
        mapping = {
            96: "`", 32: "space", 173: "caps_lock", 134: "left", 135: "right", 136: "up", 137: "down", 
            128: "shift", 129: "shift_r", 131: "ctrl_r", 156: "numpad_div", 157: "numpad_mul", 
            158: "numpad_sub", 159: "numpad_add", 160: "numpad_enter", 161: "numpad_dot", # [수정]
            150: "insert", 152: "home", 154: "page_up", 151: "delete", 153: "end", 155: "page_down"
        }
        if 48 <= vk <= 57: return f"{vk - 48}"
        if 65 <= vk <= 90: return chr(vk).lower()
        if 97 <= vk <= 122: return f"{chr(vk)}"
        if 138 <= vk <= 149: return f"F{vk - 137}"
        if 162 <= vk <= 171: return f"numpad_{vk - 162}"
        return mapping.get(vk, f"key_{vk}")
    except: return vk_code_str

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "./config.json"
    app = FullKeyboardOverlay(config_path=target)
    app.mainloop()