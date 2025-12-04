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
import platform  # Adicionado para verificar o sistema operacional


#   SISTEMA DE ACESSO E LOG
authorized_people = {"Breno_RA1371392322016.1", "Illee_Silva_RA137139232203.1"}
last_access = {}
access_granted_until = {}
log_file = "acessos_registrados.txt"

def inicializar_log():
    """Cria o arquivo de log com cabeçalho se não existir"""
    try:
        if not os.path.exists(log_file):
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("REGISTRO DE ACESSOS - PORTARIA INTELIGENTE\n")
                f.write("=" * 60 + "\n")
                f.write("Data/Hora\t\tNome\t\tRA\t\tStatus\n")
                f.write("-" * 60 + "\n")
            print(f"Arquivo de log criado: {log_file}")
        else:
            print(f"Arquivo de log já existe: {log_file}")
        return True
    except Exception as e:
        print(f"Erro ao criar arquivo de log: {e}")
        return False

def registrar_acesso(nome, ra, status):
    """Registra o acesso no arquivo TXT"""
    try:
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Formata o nome para exibição
        if "_RA" in nome:
            nome_formatado = nome.split("_RA")[0].replace("_", " ")
        else:
            nome_formatado = nome.replace("_", " ")
        
        # Escreve no arquivo
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{data_hora}\t{nome_formatado:<15}\t{ra:<15}\t{status}\n")
        
        print(f"Registro: {data_hora} - {nome_formatado} - {ra} - {status}")
        
        # Também exibe no console para debug
        print(f"DEBUG: Registro salvo: {nome} | RA: {ra} | Status: {status}")
        
    except Exception as e:
        print(f"Erro ao registrar acesso: {e}")

def access_control(name, cooldown=5, grant_duration=30):
    agora = time.time()

    if name == "Não identificado":
        registrar_acesso("Desconhecido", "N/A", "NEGADO")
        return "Acesso NEGADO"
    
    if name not in authorized_people:
        # Extrai RA mesmo para não autorizados (para registro)
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

    # Extrai RA para registro
    ra = "N/A"
    if "_RA" in name:
        parts = name.split("_RA")
        if len(parts) > 1:
            ra = "RA" + parts[1].split("_")[0]
    
    # Registra acesso LIBERADO
    registrar_acesso(name, ra, "LIBERADO")
    
    last_access[name] = agora
    access_granted_until[name] = agora + grant_duration
    return "Acesso LIBERADO"


#   CARREGA RECONHECEDOR
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
    print("Classificador carregado com sucesso!")
except Exception as e:
    print(f"Erro ao carregar classificador: {e}")
    face_classifier = None

try:
    with open("face_names.pickle", "rb") as f:
        original_labels = pickle.load(f)
        face_names = {v: k for k, v in original_labels.items()}
        print("Nomes carregados do treinamento:")
        for id_val, name in face_names.items():
            print(f"  ID {id_val}: {name}")
except Exception as e:
    print(f"Erro ao carregar nomes: {e}")
    face_names = {}


#   DETECTOR DE ROSTOS
detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def extract_ra_from_name(full_name):
    """Extrai o RA do nome completo"""
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
    """Formata o nome para exibição mais amigável"""
    if full_name == "Não identificado":
        return "Não identificado"
    
    if "_RA" in full_name:
        name_part = full_name.split("_RA")[0]
        name_part = name_part.replace("_", " ")
        name_parts = name_part.split()
        formatted = " ".join([part.capitalize() for part in name_parts])
        return formatted
    return full_name.replace("_", " ")

#   AJUSTE COMPLETO
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
    last_liberated_name = None
    remaining_time = 0

    current_time = time.time()
    for name in list(access_granted_until.keys()):
        if current_time < access_granted_until[name]:
            last_liberated_name = name
            remaining_time = access_granted_until[name] - current_time
            status = "Acesso LIBERADO"
            recognized_name = name
            break

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
        except Exception as e:
            print(f"Erro no predict: {e}")
            name = "Não identificado"
            conf = 999

        if status == "Acesso LIBERADO" and last_liberated_name:
            name = last_liberated_name
            recognized_name = name
        else:
            recognized_name = name
            status = access_control(name, grant_duration=30)

        if status == "Acesso LIBERADO":
            color = (0, 255, 0)
            display_name = format_name(recognized_name)
            
            if last_liberated_name and remaining_time > 0:
                display_name += f" ({int(remaining_time)}s)"
        else:
            color = (0, 0, 255)
            display_name = "Não identificado"

        thickness = 3 if status == "Acesso LIBERADO" else 2
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, thickness)
        
        cv2.putText(frame, display_name, (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        if status == "Acesso LIBERADO":
            ra = extract_ra_from_name(recognized_name)
            cv2.putText(frame, ra, (x, y+h+25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        cv2.putText(frame, f"Conf: {conf:.1f}", (x, y+h+50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    return frame, status, recognized_name


#   INTERFACE 
class FaceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Portaria Inteligente – Reconhecimento Facial")
        self.root.geometry("1100x850")
        self.root.configure(bg="#0d0d0d")

        # Inicializar o arquivo de log aqui
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
        # Inicializa o sistema de log quando a aplicação começa
        if inicializar_log():
            print("Sistema de log inicializado com sucesso!")
        else:
            print("Aviso: Não foi possível inicializar o sistema de log")
            
        # Verificar se o arquivo existe e é acessível
        try:
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    print(f"Arquivo de log contém {len(lines)} linhas")
        except Exception as e:
            print(f"Erro ao verificar arquivo de log: {e}")

    #   UI
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

        # Painel esquerdo: Vídeo
        left_panel = tk.Frame(main_container, bg=self.colors["bg"])
        left_panel.pack(side=tk.LEFT, fill="both", expand=True)

        video_card = tk.LabelFrame(left_panel, text=" CÂMERA AO VIVO ", 
                                  bg=self.colors["card"], fg=self.colors["accent"],
                                  font=("Segoe UI", 12, "bold"), bd=2, relief="ridge")
        video_card.pack(fill="both", expand=True, padx=(0, 10))

        self.video_label = tk.Label(video_card, bg="black")
        self.video_label.pack(padx=10, pady=10, fill="both", expand=True)

        # Painel direito: Informações (aumentado para 400 pixels)
        right_panel = tk.Frame(main_container, bg=self.colors["bg"], width=400)
        right_panel.pack(side=tk.RIGHT, fill="y", padx=(10, 0))
        right_panel.pack_propagate(False)  # Mantém a largura fixa

        info_card = tk.LabelFrame(right_panel, text=" STATUS DO SISTEMA ",
                                 bg=self.colors["card"], fg=self.colors["accent"],
                                 font=("Segoe UI", 12, "bold"), bd=2, relief="ridge")
        info_card.pack(fill="both", expand=True, padx=5, pady=5)

        # Container principal com padding ajustado
        main_info_frame = tk.Frame(info_card, bg=self.colors["card"])
        main_info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Status principal
        self.status_label = tk.Label(
            main_info_frame,
            text="⏸ SISTEMA PARADO",
            bg=self.colors["card"],
            fg=self.colors["text"],
            font=("Segoe UI", 18, "bold"),
            pady=15
        )
        self.status_label.pack(pady=(0, 15))

        # Informações do acesso
        access_frame = tk.LabelFrame(main_info_frame, text=" INFORMAÇÕES DO ACESSO ",
                                    bg=self.colors["card"], fg="#aaaaaa",
                                    font=("Segoe UI", 10, "bold"), bd=1, relief="flat")
        access_frame.pack(pady=10, padx=0, fill="x")

        # Container para informações em grid
        info_grid = tk.Frame(access_frame, bg=self.colors["card"])
        info_grid.pack(padx=10, pady=10, fill="x")

        # Linha 1: Usuário
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

        # Linha 2: RA
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

        # Linha 3: Tempo Restante
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

        # Linha 4: Último Registro
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

        # Frame para botões
        button_frame = tk.Frame(main_info_frame, bg=self.colors["card"])
        button_frame.pack(pady=20, fill="x")

        # Botão Iniciar
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
        btn_start.bind("<Enter>", lambda e: btn_start.config(bg="#388e3c"))
        btn_start.bind("<Leave>", lambda e: btn_start.config(bg="#2e7d32"))

        # Botão Parar
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
        btn_stop.bind("<Enter>", lambda e: btn_stop.config(bg="#d32f2f"))
        btn_stop.bind("<Leave>", lambda e: btn_stop.config(bg="#c62828"))

        # Botão Sair
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
        btn_exit.bind("<Enter>", lambda e: btn_exit.config(bg="#ff960e"))
        btn_exit.bind("<Leave>", lambda e: btn_exit.config(bg="#ff960e"))

        # Botão para visualizar logs
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
        btn_logs.bind("<Enter>", lambda e: btn_logs.config(bg="#1976d2"))
        btn_logs.bind("<Leave>", lambda e: btn_logs.config(bg="#1565c0"))

        # Footer
        footer = tk.Frame(self.root, bg="#111", height=40)
        footer.pack(side=tk.BOTTOM, fill="x")
        
        tk.Label(
            footer,
            text=f"Sistema de Registro de Acessos Breno Dario e Alexandre Jesus © {datetime.now().year} | Arquivo: {log_file}",
            fg="#666666",
            bg="#111",
            font=("Segoe UI", 9)
        ).pack(pady=10)

        # Atualiza o label do último registro
        self.update_last_log_time()

    def update_last_log_time(self):
        """Atualiza o timestamp do último registro"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.last_log_label.config(text=current_time)
        self.root.after(1000, self.update_last_log_time)

    def view_logs(self):

        # Aquivo de registro de acesso
        try:
            if os.path.exists(log_file):
                if platform.system() == "Windows":
                    os.startfile(log_file)
                elif platform.system() == "Darwin":  # macOS
                    os.system(f"open {log_file}")
                else:  # Linux
                    os.system(f"xdg-open {log_file}")
            else:
                messagebox.showinfo("Registros", "Arquivo de registros ainda não foi criado.")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o arquivo de log: {e}\n\n"
                                        f"O arquivo está localizado em: {os.path.abspath(log_file)}")

    def update_user_info(self, name, status, remaining_time=0):
        current_time = time.time()
        
        if status == "Acesso LIBERADO" and name != "Não identificado":
            formatted_name = format_name(name)
            ra = extract_ra_from_name(name)
            
            self.user_label.config(text=formatted_name, fg=self.colors["success"])
            self.ra_label.config(text=ra, fg=self.colors["success"])
            self.status_label.config(text="✅ ACESSO LIBERADO", fg=self.colors["success"])
            
            if remaining_time > 0:
                self.time_label.config(text=f"{int(remaining_time)} segundos", fg=self.colors["success"])
            else:
                self.time_label.config(text="30 segundos", fg=self.colors["success"])
            
            self.access_granted_time = current_time
            
        else:
            if current_time - self.access_granted_time < self.access_duration:
                remaining = self.access_duration - (current_time - self.access_granted_time)
                if remaining > 0:
                    self.time_label.config(text=f"{int(remaining)} segundos", fg=self.colors["success"])
                    return
            
            self.user_label.config(text="---", fg=self.colors["accent"])
            self.ra_label.config(text="---", fg=self.colors["accent"])
            self.status_label.config(text="❌ ACESSO NEGADO", fg=self.colors["error"])
            self.time_label.config(text="---", fg=self.colors["text"])

    def start(self):
        if self.running:
            return
        self.running = True
        self.status_label.config(text="🔍 ANALISANDO...", fg=self.colors["accent"])
        threading.Thread(target=self.loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.status_label.config(text="⏸ SISTEMA PARADO", fg=self.colors["text"])
        self.user_label.config(text="---", fg=self.colors["accent"])
        self.ra_label.config(text="---", fg=self.colors["accent"])
        self.time_label.config(text="---", fg=self.colors["text"])
        access_granted_until.clear()

    def exit_app(self):
        if messagebox.askyesno("Sair", "Tem certeza que deseja sair do sistema?"):
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
            if status == "Acesso LIBERADO" and name != "Não identificado":
                if name in access_granted_until:
                    remaining_time = access_granted_until[name] - current_time
                    if remaining_time < 0:
                        status = "Acesso NEGADO"
            
            self.update_user_info(name, status, remaining_time)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(rgb))

            self.video_label.config(image=img)
            self.video_label.image = img

        cam.release()


#   MAIN
if __name__ == "__main__":
    root = tk.Tk()
    app = FaceApp(root)
    
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    
    root.mainloop()