import cv2
import numpy as np
import os
import pickle
import time
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from datetime import datetime
import platform


#   SISTEMA DE ACESSO E LOG
authorized_people = {"Breno_Dario_RA1371392322016"}
last_access = {}
access_granted_until = {}
log_file = "acessos_registrados.txt"

def inicializar_log():
    try:
        if not os.path.exists(log_file):
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("REGISTRO DE ACESSOS - PORTARIA INTELIGENTE\n")
                f.write("=" * 60 + "\n")
                f.write("Data/Hora\t\tNome\t\tRA\t\tStatus\n")
                f.write("-" * 60 + "\n")
        return True
    except:
        return False

def registrar_acesso(nome, ra, status):
    try:
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        if "_RA" in nome:
            nome_formatado = nome.split("_RA")[0].replace("_", " ")
        else:
            nome_formatado = nome.replace("_", " ")

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{data_hora}\t{nome_formatado:<15}\t{ra:<15}\t{status}\n")

    except Exception as e:
        print(f"Erro ao registrar acesso: {e}")

def access_control(name, cooldown=5, grant_duration=30):
    agora = time.time()

    if name == "Não identificado":
        registrar_acesso("Desconhecido", "N/A", "NEGADO")
        return "Acesso NEGADO"
    
    if name not in authorized_people:
        ra = "N/A"
        if "_RA" in name:
            parts = name.split("_RA")
            if len(parts) > 1:
                ra = "RA" + parts[1].split("_")[0]

        registrar_acesso(name, ra, "NEGADO - Não autorizado")
        return "Acesso NEGADO"

    if name in access_granted_until and agora < access_granted_until[name]:
        return "Acesso LIBERADO"

    if name in last_access and agora - last_access[name] < cooldown:
        return "Acesso já liberado"

    ra = "N/A"
    if "_RA" in name:
        parts = name.split("_RA")
        if len(parts) > 1:
            ra = "RA" + parts[1].split("_")[0]

    registrar_acesso(name, ra, "LIBERADO")

    last_access[name] = agora
    access_granted_until[name] = agora + grant_duration
    return "Acesso LIBERADO"


# CARREGA RECONHECEDOR
def load_recognizer(option, training_data):
    if option == "eigenfaces":
        face_classifier = cv2.face.EigenFaceRecognizer_create()
    elif option == "fisherfaces":
        face_classifier = cv2.face.FisherFaceRecognizer_create()
    else:
        face_classifier = cv2.face.LBPHFaceRecognizer_create()

    if not os.path.exists(training_data):
        raise FileNotFoundError("Arquivo de treinamento não encontrado")

    face_classifier.read(training_data)
    return face_classifier


recognizer_type = "lbph"
training_data = "lbph_classifier.yml"
threshold = 100

try:
    face_classifier = load_recognizer(recognizer_type, training_data)
except:
    face_classifier = None

try:
    with open("face_names.pickle", "rb") as f:
        original_labels = pickle.load(f)
        face_names = {v: k for k, v in original_labels.items()}
except:
    face_names = {}


# DETECTOR DE ROSTOS
detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def extract_ra_from_name(full_name):
    if "_RA" in full_name:
        try:
            parts = full_name.split("_RA")
            if len(parts) > 1:
                ra_part = parts[1]
                if "_" in ra_part:
                    ra = "RA" + ra_part.split("_")[0]
                else:
                    ra = "RA" + ra_part
                return ra
        except:
            pass
    return "N/A"

def format_name(full_name):
    if full_name == "Não identificado":
        return "Não identificado"
    
    if "_RA" in full_name:
        name_part = full_name.split("_RA")[0]
        name_part = name_part.replace("_", " ")
        name_parts = name_part.split()
        formatted = " ".join([part.capitalize() for part in name_parts])
        return formatted
    
    return full_name.replace("_", " ")


#   🔧 LÓGICA DE RECONHECIMENTO
def recognize_faces(frame):
    if face_classifier is None:
        cv2.putText(frame, "ERRO: Classificador não carregado", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame, "Sistema com erro", "Não identificado"
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))

    if len(faces) == 0:
        cv2.putText(frame, "Nenhum rosto detectado", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame, "Acesso NEGADO", "Não identificado"

    status = "Acesso NEGADO"
    recognized_name = "Não identificado"

    for (x, y, w, h) in faces:
        roi = gray[y:y+h, x:x+w]
        roi = cv2.resize(roi, (90, 120))
        roi = cv2.equalizeHist(roi)

        try:
            pred, conf = face_classifier.predict(roi)
            if conf <= threshold:
                name = face_names.get(pred, "Não identificado")
            else:
                name = "Não identificado"
        except:
            name = "Não identificado"
            conf = 999

        recognized_name = name

        if name == "Não identificado":
            status = "Acesso NEGADO"
        else:
            status = access_control(name, grant_duration=30)

        if status == "Acesso LIBERADO" and name != "Não identificado":
            color = (0, 255, 0)
            display_name = format_name(name)
            ra = extract_ra_from_name(name)
        else:
            color = (0, 0, 255)
            display_name = "Não identificado"
            ra = ""

        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(frame, display_name, (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if ra:
            cv2.putText(frame, ra, (x, y+h+25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.putText(frame, f"Conf: {conf:.1f}", (x, y+h+50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    return frame, status, recognized_name


# --------------------------------------------------------------------------
#   INTERFACE COM A CORREÇÃO PEDIDA
# --------------------------------------------------------------------------

class FaceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Portaria Inteligente – Reconhecimento Facial")
        self.root.geometry("1100x850")
        self.root.configure(bg="#0d0d0d")

        self.inicializar_sistema_log()

        self.running = False
        self.last_recognized_name = "Não identificado"
        self.access_granted_time = 0
        self.access_duration = 30

        self.colors = {
            "bg": "#0d0d0d",
            "card": "#1a1a1a",
            "text": "#e6e6e6",
            "accent": "#4da6ff",
            "success": "#4dff88",
            "error": "#ff4d4d",
        }

        self.build_ui()

    def inicializar_sistema_log(self):
        inicializar_log()

    def build_ui(self):
        top = tk.Frame(self.root, bg="#111", height=90)
        top.pack(fill="x")

        tk.Label(
            top,
            text="PORTARIA INTELIGENTE",
            fg=self.colors["accent"],
            bg="#111",
            font=("Segoe UI", 26, "bold")
        ).pack(pady=10)

        tk.Label(
            top,
            text="Sistema de Reconhecimento Facial com Registro de Acessos",
            fg="#aaaaaa",
            bg="#111",
            font=("Segoe UI", 11)
        ).pack()

        tk.Label(
            top,
            text=f"Registros salvos em: {log_file}",
            fg="#4da6ff",
            bg="#111",
            font=("Segoe UI", 9)
        ).pack(pady=5)

        main_container = tk.Frame(self.root, bg=self.colors["bg"])
        main_container.pack(fill="both", expand=True, padx=20, pady=10)

        left_panel = tk.Frame(main_container, bg=self.colors["bg"])
        left_panel.pack(side=tk.LEFT, fill="both", expand=True)

        video_card = tk.LabelFrame(left_panel, text=" CÂMERA AO VIVO ", 
                                  bg=self.colors["card"], fg=self.colors["accent"],
                                  font=("Segoe UI", 12, "bold"), bd=2, relief="ridge")
        video_card.pack(fill="both", expand=True, padx=(0, 10))

        self.video_label = tk.Label(video_card, bg="black")
        self.video_label.pack(padx=10, pady=10, fill="both", expand=True)

        right_panel = tk.Frame(main_container, bg=self.colors["bg"], width=400)
        right_panel.pack(side=tk.RIGHT, fill="y", padx=(10, 0))
        right_panel.pack_propagate(False)

        info_card = tk.LabelFrame(right_panel, text=" STATUS DO SISTEMA ",
                                 bg=self.colors["card"], fg=self.colors["accent"],
                                 font=("Segoe UI", 12, "bold"), bd=2, relief="ridge")
        info_card.pack(fill="both", expand=True, padx=5, pady=5)

        main_info_frame = tk.Frame(info_card, bg=self.colors["card"])
        main_info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.status_label = tk.Label(
            main_info_frame,
            text="⏸ SISTEMA PARADO",
            bg=self.colors["card"],
            fg=self.colors["text"],
            font=("Segoe UI", 18, "bold"),
            pady=15
        )
        self.status_label.pack(pady=(0, 15))

        access_frame = tk.LabelFrame(main_info_frame, text=" INFORMAÇÕES DO ACESSO ",
                                    bg=self.colors["card"], fg="#aaaaaa",
                                    font=("Segoe UI", 10, "bold"), bd=1, relief="flat")
        access_frame.pack(pady=10, padx=0, fill="x")

        info_grid = tk.Frame(access_frame, bg=self.colors["card"])
        info_grid.pack(padx=10, pady=10, fill="x")

        row1 = tk.Frame(info_grid, bg=self.colors["card"])
        row1.pack(fill="x", pady=3)
        tk.Label(
            row1,
            text="Usuário:",
            bg=self.colors["card"],
            fg="#aaaaaa",
            font=("Segoe UI", 10),
            width=12,
            anchor="w"
        ).pack(side=tk.LEFT)
        self.user_label = tk.Label(
            row1,
            text="---",
            bg=self.colors["card"],
            fg=self.colors["accent"],
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        )
        self.user_label.pack(side=tk.LEFT, fill="x", expand=True)

        row2 = tk.Frame(info_grid, bg=self.colors["card"])
        row2.pack(fill="x", pady=3)
        tk.Label(
            row2,
            text="RA:",
            bg=self.colors["card"],
            fg="#aaaaaa",
            font=("Segoe UI", 10),
            width=12,
            anchor="w"
        ).pack(side=tk.LEFT)
        self.ra_label = tk.Label(
            row2,
            text="---",
            bg=self.colors["card"],
            fg=self.colors["accent"],
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        )
        self.ra_label.pack(side=tk.LEFT, fill="x", expand=True)

        row3 = tk.Frame(info_grid, bg=self.colors["card"])
        row3.pack(fill="x", pady=3)
        tk.Label(
            row3,
            text="Tempo Restante:",
            bg=self.colors["card"],
            fg="#aaaaaa",
            font=("Segoe UI", 10),
            width=12,
            anchor="w"
        ).pack(side=tk.LEFT)
        self.time_label = tk.Label(
            row3,
            text="---",
            bg=self.colors["card"],
            fg=self.colors["success"],
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        )
        self.time_label.pack(side=tk.LEFT, fill="x", expand=True)

        row4 = tk.Frame(info_grid, bg=self.colors["card"])
        row4.pack(fill="x", pady=3)
        tk.Label(
            row4,
            text="Último Registro:",
            bg=self.colors["card"],
            fg="#aaaaaa",
            font=("Segoe UI", 10),
            width=12,
            anchor="w"
        ).pack(side=tk.LEFT)
        self.last_log_label = tk.Label(
            row4,
            text="---",
            bg=self.colors["card"],
            fg="#4da6ff",
            font=("Segoe UI", 9),
            anchor="w"
        )
        self.last_log_label.pack(side=tk.LEFT, fill="x", expand=True)

        button_frame = tk.Frame(main_info_frame, bg=self.colors["card"])
        button_frame.pack(pady=20, fill="x")

        btn_start = tk.Button(
            button_frame,
            text="INICIAR RECONHECIMENTO",
            command=self.start,
            bg="#2e7d32",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=5,
            pady=8,
            cursor="hand2",
            bd=0
        )
        btn_start.pack(fill="x", pady=4)

        btn_stop = tk.Button(
            button_frame,
            text="PARAR",
            command=self.stop,
            bg="#c62828",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=5,
            pady=8,
            cursor="hand2",
            bd=0
        )
        btn_stop.pack(fill="x", pady=4)

        btn_exit = tk.Button(
            button_frame,
            text="SAIR DO SISTEMA",
            command=self.exit_app,
            bg="#ff960e",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=5,
            pady=8,
            cursor="hand2",
            bd=0
        )
        btn_exit.pack(fill="x", pady=4)

        btn_logs = tk.Button(
            button_frame,
            text="VISUALIZAR REGISTROS",
            command=self.view_logs,
            bg="#1565c0",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=5,
            pady=8,
            cursor="hand2",
            bd=0
        )
        btn_logs.pack(fill="x", pady=(12, 4))

        footer = tk.Frame(self.root, bg="#111", height=40)
        footer.pack(side=tk.BOTTOM, fill="x")
        
        tk.Label(
            footer,
            text=f"Sistema de Registro de Acessos Breno Dario e Alexandre Jesus © {datetime.now().year} | Arquivo: {log_file}",
            fg="#666666",
            bg="#111",
            font=("Segoe UI", 9)
        ).pack(pady=10)

        self.update_last_log_time()

    def update_last_log_time(self):
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.last_log_label.config(text=current_time)
        self.root.after(1000, self.update_last_log_time)

    def view_logs(self):
        try:
            if os.path.exists(log_file):
                if platform.system() == "Windows":
                    os.startfile(log_file)
                elif platform.system() == "Darwin":
                    os.system(f"open {log_file}")
                else:
                    os.system(f"xdg-open {log_file}")
            else:
                messagebox.showinfo("Registros", "Arquivo não encontrado.")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ----------------------------------------------------------------------
    #   🔧 FUNÇÃO CORRIGIDA — MOSTRA “ACESSO NEGADO / NÃO IDENTIFICADO”
    # ----------------------------------------------------------------------
    def update_user_info(self, name, status, remaining_time=0):
        current_time = time.time()

        # --- Se NÃO identificado -> mostra NEGADO imediatamente ---
        if name == "Não identificado":
            self.user_label.config(text="Não identificado", fg=self.colors["error"])
            self.ra_label.config(text="---", fg=self.colors["error"])
            self.status_label.config(text="ACESSO NEGADO", fg=self.colors["error"])
            self.time_label.config(text="---", fg=self.colors["text"])
            self.access_granted_time = 0
            return

        # --- Se identificado e liberado ---
        if status == "Acesso LIBERADO":
            formatted_name = format_name(name)
            ra = extract_ra_from_name(name)

            self.user_label.config(text=formatted_name, fg=self.colors["success"])
            self.ra_label.config(text=ra, fg=self.colors["success"])
            self.status_label.config(text="ACESSO LIBERADO", fg=self.colors["success"])

            if remaining_time > 0:
                self.time_label.config(text=f"{int(remaining_time)}s", fg=self.colors["success"])
            else:
                self.time_label.config(text="30s", fg=self.colors["success"])

            self.access_granted_time = current_time
            return

        # --- Se acesso negado mas ainda dentro do tempo de liberação anterior ---
        if current_time - self.access_granted_time < self.access_duration:
            remaining = self.access_duration - (current_time - self.access_granted_time)
            self.time_label.config(text=f"{int(remaining)}s", fg=self.colors["success"])
            return

        # --- Caso contrário, acesso negado ---
        self.user_label.config(text="---", fg=self.colors["accent"])
        self.ra_label.config(text="---", fg=self.colors["accent"])
        self.status_label.config(text="ACESSO NEGADO", fg=self.colors["error"])
        self.time_label.config(text="---", fg=self.colors["text"])
        self.access_granted_time = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self.status_label.config(text="🔍 ANALISANDO...", fg=self.colors["accent"])
        threading.Thread(target=self.loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.status_label.config(text="⏸ SISTEMA PARADO", fg=self.colors["text"])
        access_granted_until.clear()

    def exit_app(self):
        if messagebox.askyesno("Sair", "Deseja realmente sair?"):
            self.running = False
            self.root.quit()
            self.root.destroy()

    def loop(self):
        cam = cv2.VideoCapture(0)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cam.isOpened():
            messagebox.showerror("Erro", "Não foi possível acessar a câmera!")
            return

        while self.running:
            ret, frame = cam.read()
            if not ret:
                break

            frame, status, name = recognize_faces(frame)
            
            remaining_time = 0
            current_time = time.time()
            if status == "Acesso LIBERADO" and name in access_granted_until:
                remaining_time = access_granted_until[name] - current_time

            self.update_user_info(name, status, remaining_time)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(rgb))

            self.video_label.config(image=img)
            self.video_label.image = img

        cam.release()


# MAIN
if __name__ == "__main__":
    root = tk.Tk()
    app = FaceApp(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    root.mainloop()
