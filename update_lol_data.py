# IMPORTS
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pandas as pd
import gspread
import time
import random
import re
import threading
import datetime
import traceback
import queue
from bs4 import BeautifulSoup

# MOTOR SELENIUM
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# CONFIGURACIÓN
VERSION = "25.0"
SHEET_NAME = "Excel Compos LOL"
SOURCE_SHEET = "HOJA BUENA"
TARGET_SHEET = "CRUDO"
CREDENTIALS = "credentials.json"

# Colores Dark Mode
COLOR_BG = "#121212"
COLOR_FG = "#e0e0e0"
COLOR_ACCENT = "#ff00bf" # Magenta
COLOR_SUCCESS = "#00e676"
COLOR_ERROR = "#ff5252"

# 1. MAPEO PARA URLS
SLUG_MAPPING = {
    "WUKONG": "monkeyking",      
    "MONKEYKING": "monkeyking",
    "JARVAN": "jarvan-iv",
    "JARVAN IV": "jarvan-iv",
    "XIN ZHAO": "xin-zhao",
    "RENATA": "renata",
    "AMBESA": "ambessa",
    "AMBESSA": "ambessa",
    "NUNU": "nunu",
    "DRMUNDO": "dr-mundo",
    "MUNDO": "dr-mundo",
    "KOGMAW": "kogmaw",
    "REKSAI": "reksai",
    "BELVETH": "belveth",
    "LEE SIN": "lee-sin",
    "MISS FORTUNE": "miss-fortune",
    "TAHM KENCH": "tahm-kench",
    "TWISTED FATE": "twisted-fate",
    "AURELION SOL": "aurelion-sol",
    "MASTER YI": "master-yi",
    "BRONCHALIX": "SKIP"
}

# 2. MAPEO PARA NORMALIZACIÓN FINAL
OUTPUT_NORMALIZATION = {
    "Dr. Mundo": "DRMUNDO",
    "Jarvan IV": "JARVAN",
    "Nunu & Willump": "NUNU",
    "Renata Glasc": "RENATA",
    "Kog'Maw": "KOGMAW",
    "Rek'Sai": "REKSAI",
    "Bel'Veth": "BELVETH",
    "Kai'Sa": "KAISA",
    "Kha'Zix": "KHAZIX",
    "Vel'Koz": "VELKOZ",
    "Cho'Gath": "CHOGATH",
    "LeBlanc": "LEBLANC",
    "Wukong": "WUKONG",
    "Miss Fortune": "MISS FORTUNE",
    "Tahm Kench": "TAHM KENCH",
    "Twisted Fate": "TWISTED FATE",
    "Lee Sin": "LEE SIN",
    "Xin Zhao": "XIN ZHAO",
    "Master Yi": "MASTER YI",
    "Aurelion Sol": "AURELION SOL"
}


# MOTOR SELENIUM
class SeleniumEngine:
    def __init__(self, log_callback):
        self.log = log_callback
        self.driver = None

    def start_driver(self):
        self.log("🔧 Iniciando Chrome Optimizado...", "info")
        opts = Options()
        opts.add_argument("--disable-blink-features=AutomationControlled") 
        opts.add_argument("--start-maximized")
        # Bloquear imágenes para velocidad
        prefs = {"profile.managed_default_content_settings.images": 2}
        opts.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        self.log("✅ Ready.", "success")

    def stop_driver(self):
        if self.driver: self.driver.quit()

    def clean_slug(self, name):
        name_upper = str(name).strip().upper()
        if name_upper in SLUG_MAPPING: return SLUG_MAPPING[name_upper]
        return name_upper.lower().replace(" ", "-").replace("'", "").replace(".", "")

    def normalize_output_names(self, raw_list):
        clean_list = []
        for name in raw_list:
            if name in OUTPUT_NORMALIZATION:
                clean_list.append(OUTPUT_NORMALIZATION[name])
            else:
                clean_list.append(name.upper())
        return clean_list

    def fetch_data(self, champ_name, current_role, pool_roles_map):
        if not self.driver: self.start_driver()
        
        base_slug = self.clean_slug(champ_name)
        if base_slug == "SKIP": return None

        attempts = [base_slug]
        if base_slug == "monkeyking": attempts.append("wukong")
        if base_slug == "wukong": attempts.append("monkeyking")
        if "-" in base_slug: attempts.append(base_slug.replace("-", ""))

        soup = None
        
        for slug in list(dict.fromkeys(attempts)):
            url = f"https://www.leagueofgraphs.com/champions/counters/{slug}"
            try:
                self.driver.get(url)
                if "Not Found" in self.driver.title: continue
                
                # CLICKER INTELIGENTE
                try:
                    self.driver.execute_script("""
                        var buttons = document.querySelectorAll('.see_more_button');
                        buttons.forEach(function(btn) {
                            if(btn.innerText.toLowerCase().trim() === 'see more') {
                                btn.click();
                            }
                        });
                    """)
                    time.sleep(0.5) 
                except: pass

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                if soup.find("h3"): break
            except Exception as e:
                self.log(f"Err {slug}: {e}", "error")

        if not soup: return None

        # EXTRACCIÓN COUNTERS (BOX ISOLATION)
        countered_by = []
        counters_to = []
        synergies = []

        for box in soup.find_all("div", class_="box"):
            header = box.find(["h3", "h2"])
            if not header: continue
            text = header.get_text(strip=True).lower()
            
            target_list = None
            if "gets countered" in text: 
                target_list = countered_by
            elif "counters lane" in text and "gets" not in text: 
                target_list = counters_to
            elif "is best with" in text: 
                target_list = synergies
            
            if target_list is not None:
                table = box.find("table", class_="data_table")
                if not table: continue
                
                rows = table.find_all("tr")
                for row in rows:
                    if "see_more" in str(row): continue
                    name_span = row.find("span", class_="name")
                    if not name_span: continue
                    c_name = name_span.get_text(strip=True)
                    
                    if target_list is synergies:
                        c_slug = self.clean_slug(c_name)
                        found = False
                        c_roles = set()
                        for pool_champ, roles in pool_roles_map.items():
                            if self.clean_slug(pool_champ) == c_slug:
                                found = True
                                c_roles = roles
                                break
                        if found:
                            if current_role in c_roles: continue
                            target_list.append(c_name)
                    else:
                        target_list.append(c_name)

        # EXTRACCIÓN WR/BAN
        wr = "N/A"
        ban = "N/A"
        
        # 1. Intentar header stats
        header_stats = soup.find("div", id="champHeaderStats")
        if header_stats:
            txt = header_stats.get_text()
            m_wr = re.search(r'Winrate:\s*([\d\.]+)%', txt)
            if m_wr: wr = f"{m_wr.group(1)}%"
            m_ban = re.search(r'Banrate:\s*([\d\.]+)%', txt)
            if m_ban: ban = f"{m_ban.group(1)}%"
        
        # 2. Si falla, intentar navegar a stats
        if wr == "N/A" or ban == "N/A":
            try:
                self.driver.get(f"https://www.leagueofgraphs.com/champions/stats/{slug}")
                s_stats = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Buscar gráficos pie
                pie_wr = s_stats.find(id="graphDD2")
                if pie_wr:
                    m = re.search(r'([\d\.]+)%', pie_wr.get_text())
                    if m: wr = f"{m.group(1)}%"
                
                pie_ban = s_stats.find(id="graphDD3")
                if pie_ban:
                    m = re.search(r'([\d\.]+)%', pie_ban.get_text())
                    if m: ban = f"{m.group(1)}%"
                
                # Fallback texto plano
                if wr == "N/A":
                    txt = s_stats.get_text()
                    m_wr = re.search(r'Winrate:\s*([\d\.]+)%', txt)
                    if m_wr: wr = f"{m_wr.group(1)}%"
                    m_ban = re.search(r'Banrate:\s*([\d\.]+)%', txt)
                    if m_ban: ban = f"{m_ban.group(1)}%"
            except: pass

        # NORMALIZACIÓN FINAL 
        clean_countered = self.normalize_output_names(list(dict.fromkeys(countered_by))[:5])
        clean_counters_to = self.normalize_output_names(list(dict.fromkeys(counters_to))[:5])
        clean_synergies = self.normalize_output_names(list(dict.fromkeys(synergies))[:25])

        return {
            "WINRATE": wr,
            "BANRATE": ban,
            "COUNTERED BY": ", ".join(clean_countered),
            "COUNTERS TO": ", ".join(clean_counters_to),
            "SINERGIA": ", ".join(clean_synergies)
        }

# DASHBOARD
class CoachApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"LoL Team Architect - {VERSION}")
        self.geometry("1100x700")
        self.configure(bg=COLOR_BG)
        self.queue = queue.Queue()
        self._init_ui()
        self.engine = SeleniumEngine(self.log_gui)
        self.after(100, self._process_queue)

    def _init_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", fieldbackground="#2b2b2b", foreground="#ccc", rowheight=25, borderwidth=0)
        style.configure("Treeview.Heading", background="#1a1a1a", foreground=COLOR_ACCENT, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[('selected', COLOR_ACCENT)], foreground=[('selected', 'black')])
        
        f_top = tk.Frame(self, bg="#111", height=50)
        f_top.pack(fill=tk.X)
        tk.Label(f_top, text=f"ENGINE {VERSION}", bg="#111", fg=COLOR_ACCENT, font=("Segoe UI", 14, "bold")).pack(pady=10)

        f_c = tk.Frame(self, bg=COLOR_BG)
        f_c.pack(fill=tk.X, padx=20, pady=10)
        self.btn_start = tk.Button(f_c, text="▶ START", bg=COLOR_SUCCESS, fg="black", font=("Segoe UI", 11, "bold"), relief="flat", command=self.start_thread)
        self.btn_start.pack(side=tk.LEFT)
        self.lbl_status = tk.Label(f_c, text="Ready", bg=COLOR_BG, fg="gray")
        self.lbl_status.pack(side=tk.LEFT, padx=20)
        self.progress = ttk.Progressbar(self, length=100, mode="determinate")
        self.progress.pack(fill=tk.X, padx=20, pady=5)

        paned = tk.PanedWindow(self, orient=tk.VERTICAL, bg=COLOR_BG, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        f_t = tk.Frame(paned, bg=COLOR_BG)
        cols = ("CHAMP", "WR", "BAN", "COUNTERED", "COUNTERS", "SINERGIA")
        self.tree = ttk.Treeview(f_t, columns=cols, show="headings")
        self.tree.column("CHAMP", width=100); self.tree.column("WR", width=60); self.tree.column("BAN", width=60)
        self.tree.column("COUNTERED", width=200); self.tree.column("COUNTERS", width=200); self.tree.column("SINERGIA", width=300)
        for c in cols: self.tree.heading(c, text=c)
        sb_y = ttk.Scrollbar(f_t, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        paned.add(f_t, height=450)

        self.txt_log = scrolledtext.ScrolledText(paned, bg="#000", fg="#ccc", font=("Consolas", 9))
        self.txt_log.tag_config("error", foreground=COLOR_ERROR); self.txt_log.tag_config("success", foreground=COLOR_SUCCESS)
        paned.add(self.txt_log)

    def log_gui(self, msg, tag="info"):
        self.queue.put(("log", msg, tag))

    def _process_queue(self):
        try:
            while True:
                kind, data, extra = self.queue.get_nowait()
                if kind == "log":
                    self.txt_log.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {data}\n", extra)
                    self.txt_log.see(tk.END)
                elif kind == "row":
                    self.tree.insert("", tk.END, values=data); self.tree.see(self.tree.get_children()[-1])
                elif kind == "progress":
                    self.progress["value"] = data; self.lbl_status.config(text=extra)
                elif kind == "finish":
                    self.btn_start.config(state="normal", bg=COLOR_SUCCESS); self.engine.stop_driver()
                    messagebox.showinfo("Done", "Finalizado.")
        except queue.Empty: pass
        self.after(100, self._process_queue)

    def start_thread(self):
        self.btn_start.config(state="disabled", bg="#555"); self.tree.delete(*self.tree.get_children())
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            self.log_gui("Conectando GSheets...", "info")
            gc = gspread.service_account(filename=CREDENTIALS)
            sh = gc.open(SHEET_NAME)
            ws_src = sh.worksheet(SOURCE_SHEET)

            # --- BACKUP CORRECTO (DE CRUDO) ---
            try:
                self.log_gui("Creando Backup de CRUDO...", "info")
                ws_tgt_actual = sh.worksheet(TARGET_SHEET)
                ws_tgt_actual.duplicate(new_sheet_name=f"Backup_{int(time.time())}")
            except: 
                self.log_gui("No existe CRUDO previo, omitiendo backup.", "info")

            raw = ws_src.get_all_values()
            headers = [h.upper().strip() for h in raw[0]]
            try: idx_champ = headers.index("CHAMP"); idx_rol = headers.index("ROL")
            except: self.log_gui("Faltan columnas", "error"); return

            pool_roles_map = {}
            pool_list = []
            for r in raw[1:]:
                if len(r) > idx_champ:
                    c_name = r[idx_champ].strip()
                    c_role = r[idx_rol].strip().upper() if len(r) > idx_rol else "UNKNOWN"
                    if c_name and ":" not in c_name and "BRONCHALIX" not in c_name.upper():
                        pool_list.append({"name": c_name, "role": c_role})
                        if c_name not in pool_roles_map: pool_roles_map[c_name] = set()
                        pool_roles_map[c_name].add(c_role)

            results = []
            total = len(pool_list)
            for i, item in enumerate(pool_list):
                champ = item['name']; role = item['role']
                self.queue.put(("progress", (i/total)*100, f"Minando {champ}..."))
                data = self.engine.fetch_data(champ, role, pool_roles_map)
                
                row = {"CHAMP": champ}
                if data:
                    row.update(data)
                    self.log_gui(f"✅ {champ}: OK", "success")
                    self.queue.put(("row", (champ, data['WINRATE'], data['BANRATE'], data['COUNTERED BY'], data['COUNTERS TO'], data['SINERGIA']), None))
                else:
                    self.log_gui(f"⚠️ {champ}: Fallo", "error")
                    row.update({"WINRATE": "N/A", "BANRATE": "N/A", "COUNTERED BY": "", "COUNTERS TO": "", "SINERGIA": ""})
                    self.queue.put(("row", (champ, "N/A", "N/A", "-", "-", "-"), None))
                results.append(row)

            self.queue.put(("progress", 99, "Guardando..."))
            df = pd.DataFrame(results).fillna("")
            cols = ["CHAMP", "WINRATE", "BANRATE", "COUNTERED BY", "COUNTERS TO", "SINERGIA"]
            for c in cols: 
                if c not in df.columns: df[c] = ""
            
            try: ws_tgt = sh.worksheet(TARGET_SHEET)
            except: ws_tgt = sh.add_worksheet(TARGET_SHEET, 1000, 20)
            
            ws_tgt.clear()
            ws_tgt.update([df[cols].columns.values.tolist()] + df[cols].astype(str).values.tolist())
            
            self.queue.put(("progress", 100, "Completado")); self.queue.put(("finish", None, None))

        except Exception as e:
            self.log_gui(f"ERROR: {e}", "error"); self.engine.stop_driver()

if __name__ == "__main__":
    app = CoachApp()
    app.mainloop()