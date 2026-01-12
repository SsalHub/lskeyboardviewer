import tkinter as tk
from tkinter import Menu
from pynput import keyboard
import threading

class KeyboardOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Python Key Overlay")
        
        # 1. 타이틀 바 제거 및 최상단 유지
        self.root.overrideredirect(True) 
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg="#2c3e50")  # 배경색 설정

        # 2. 마우스 드래그 이동 기능 설정
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.do_drag)

        # 3. 우클릭 메뉴 설정
        self.create_context_menu()
        self.root.bind("<Button-3>", self.show_menu)

        # 4. 키보드 레이아웃 설정 (QWERTY 일부 예시)
        self.keys_layout = [
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', 'Space']
        ]
        self.buttons = {}
        self.create_widgets()

        # 5. 백그라운드 리스너 실행
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

    def create_widgets(self):
        """키보드 모양의 버튼들 배치"""
        for r, row in enumerate(self.keys_layout):
            row_frame = tk.Frame(self.root, bg="#2c3e50")
            row_frame.pack(pady=2)
            for key_text in row:
                btn = tk.Label(
                    row_frame, text=key_text, width=6, height=2,
                    fg="white", bg="#34495e", font=("Arial", 10, "bold"),
                    relief="flat"
                )
                btn.pack(side=tk.LEFT, padx=2)
                # 입력을 매칭하기 위해 소문자로 저장 (특수키 제외)
                mapping_key = key_text.lower() if len(key_text) == 1 else key_text.lower()
                self.buttons[mapping_key] = btn

    def create_context_menu(self):
        """우클릭 시 나타날 메뉴 구성"""
        self.menu = Menu(self.root, tearoff=0)
        self.menu.add_command(label="최소화", command=self.minimize_window)
        self.menu.add_separator()
        self.menu.add_command(label="종료", command=self.root.destroy)

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def minimize_window(self):
        # overrideredirect 상태에서는 일반적인 최소화가 안 되어 보완이 필요함
        self.root.update_idletasks()
        self.root.withdraw() # 일단 숨기기 (다시 띄우려면 별도의 로직 필요)
        
    # --- 창 이동 로직 ---
    def start_drag(self, event):
        self.x = event.x
        self.y = event.y

    def do_drag(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    # --- 키 입력 처리 ---
    def on_press(self, key):
        try:
            k = key.char.lower() if hasattr(key, 'char') else str(key).replace('Key.', '')
            if k in self.buttons:
                self.buttons[k].config(bg="#e74c3c") # 눌렸을 때 강조색
        except Exception: pass

    def on_release(self, key):
        try:
            k = key.char.lower() if hasattr(key, 'char') else str(key).replace('Key.', '')
            if k in self.buttons:
                self.buttons[k].config(bg="#34495e") # 원래 색상으로
        except Exception: pass

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = KeyboardOverlay()
    app.run()