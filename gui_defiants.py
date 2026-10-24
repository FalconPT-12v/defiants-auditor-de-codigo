#!/usr/bin/env python3
"""
DeFiAnts Code Auditor — interface gráfica para o auditor_codigo.py

Estrutura esperada:
    gui_defiants.py
    auditor_codigo.py
    assets/defiants.png

Instalação:
    pip install google-genai pillow     (pillow é opcional, só para redimensionar a imagem melhor)

Uso:
    python gui_defiants.py
"""

import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

try:
    from google import genai
    from google.genai import types
except ImportError:
    sys.exit("Falta instalar a biblioteca:  pip install google-genai")

try:
    import auditor_codigo as core
except ImportError:
    sys.exit("Falta o ficheiro auditor_codigo.py na mesma pasta que este script.")

try:
    from PIL import Image, ImageTk  # opcional
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

AQUI = Path(__file__).resolve().parent
IMAGEM = next((c for c in (AQUI / "assets" / "defiants.png", AQUI / "defiants.png") if c.exists()),
              AQUI / "assets" / "defiants.png")

# Paleta DeFiAnts
BG = "#0b0618"
PANEL = "#150b2e"
PANEL_2 = "#1d1040"
ROXO = "#b46cff"
ROXO_ESCURO = "#6d28d9"
CIANO = "#22d3ee"
TEXTO = "#e9ddff"
TEXTO_SUAVE = "#9a86c9"
ERRO = "#ff6b8b"
OK = "#5eead4"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DeFiAnts · Code Auditor")
        self.configure(bg=BG)
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.fila = queue.Queue()
        self.parar = threading.Event()
        self.thread = None
        self.relatorio_atual = ""
        self.foto = None

        self._estilos()
        self._construir()
        self.after(100, self._processar_fila)

    # ------------------------------------------------------------------ UI
    def _estilos(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2,
                    foreground=TEXTO, arrowcolor=ROXO, bordercolor=ROXO_ESCURO,
                    lightcolor=PANEL_2, darkcolor=PANEL_2, padding=4)
        s.map("TCombobox", fieldbackground=[("readonly", PANEL_2)],
              foreground=[("readonly", TEXTO)])
        s.configure("Neon.Horizontal.TProgressbar", troughcolor=PANEL_2,
                    background=ROXO, bordercolor=PANEL_2,
                    lightcolor=ROXO, darkcolor=ROXO_ESCURO)
        self.option_add("*TCombobox*Listbox.background", PANEL_2)
        self.option_add("*TCombobox*Listbox.foreground", TEXTO)
        self.option_add("*TCombobox*Listbox.selectBackground", ROXO_ESCURO)

    def _botao(self, pai, texto, comando, cor=ROXO, fg="#12002b", **kw):
        b = tk.Button(pai, text=texto, command=comando, bg=cor, fg=fg,
                      activebackground=CIANO, activeforeground="#00131a",
                      relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                      font=("Segoe UI", 10, "bold"), **kw)
        return b

    def _label(self, pai, texto, cor=TEXTO_SUAVE, tam=9, bold=False, **kw):
        return tk.Label(pai, text=texto, bg=kw.pop("bg", PANEL), fg=cor,
                        font=("Segoe UI", tam, "bold" if bold else "normal"), **kw)

    def _construir(self):
        # ---------- coluna esquerda: imagem + marca ----------
        esq = tk.Frame(self, bg=PANEL, width=340)
        esq.pack(side="left", fill="y")
        esq.pack_propagate(False)

        self._carregar_imagem(esq)

        tk.Label(esq, text="DeFiAnts", bg=PANEL, fg=ROXO,
                 font=("Consolas", 28, "bold")).pack(pady=(14, 0))
        tk.Label(esq, text="CODE AUDITOR", bg=PANEL, fg=TEXTO,
                 font=("Consolas", 12, "bold")).pack()
        tk.Frame(esq, bg=ROXO_ESCURO, height=2).pack(fill="x", padx=30, pady=12)
        tk.Label(esq, text="BUILD · HODL · EARN · REPEAT", bg=PANEL, fg=CIANO,
                 font=("Consolas", 10, "bold")).pack()
        tk.Label(esq, text="COLONY OVER EVERYTHING", bg=PANEL, fg=TEXTO_SUAVE,
                 font=("Consolas", 9)).pack(pady=(6, 0))
        tk.Label(esq, text="DF-ANTS-001", bg=PANEL, fg=TEXTO_SUAVE,
                 font=("Consolas", 8)).pack(side="bottom", pady=10)

        # ---------- coluna direita ----------
        dir_ = tk.Frame(self, bg=BG)
        dir_.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        # Configuração
        cfg = tk.Frame(dir_, bg=PANEL, padx=14, pady=12)
        cfg.pack(fill="x")
        cfg.columnconfigure(1, weight=1)

        # Alvo
        self._label(cfg, "Alvo (ficheiro ou pasta)").grid(row=0, column=0, sticky="w", pady=4)
        self.var_alvo = tk.StringVar()
        tk.Entry(cfg, textvariable=self.var_alvo, bg=PANEL_2, fg=TEXTO,
                 insertbackground=CIANO, relief="flat", font=("Consolas", 10)
                 ).grid(row=0, column=1, sticky="ew", padx=8, ipady=5)
        caixa = tk.Frame(cfg, bg=PANEL)
        caixa.grid(row=0, column=2)
        self._botao(caixa, "Pasta", self._escolher_pasta, cor=PANEL_2, fg=ROXO).pack(side="left", padx=2)
        self._botao(caixa, "Ficheiro", self._escolher_ficheiro, cor=PANEL_2, fg=ROXO).pack(side="left", padx=2)

        # Chave
        self._label(cfg, "GEMINI_API_KEY").grid(row=1, column=0, sticky="w", pady=4)
        self.var_chave = tk.StringVar(value=os.environ.get("GEMINI_API_KEY", ""))
        tk.Entry(cfg, textvariable=self.var_chave, show="•", bg=PANEL_2, fg=TEXTO,
                 insertbackground=CIANO, relief="flat", font=("Consolas", 10)
                 ).grid(row=1, column=1, sticky="ew", padx=8, ipady=5)
        self._label(cfg, "não é guardada em disco", tam=8).grid(row=1, column=2, sticky="w")

        # Foco + modelo
        self._label(cfg, "Foco").grid(row=2, column=0, sticky="w", pady=4)
        linha = tk.Frame(cfg, bg=PANEL)
        linha.grid(row=2, column=1, columnspan=2, sticky="w", padx=8)
        self.var_foco = tk.StringVar(value="seguranca")
        ttk.Combobox(linha, textvariable=self.var_foco, values=list(core.FOCOS.keys()),
                     state="readonly", width=14).pack(side="left")
        self._label(linha, "   Modelo").pack(side="left")
        self.var_modelo = tk.StringVar(value="auto")
        self.combo_modelo = ttk.Combobox(linha, textvariable=self.var_modelo,
                                         values=["auto"], width=30)
        self.combo_modelo.pack(side="left", padx=6)
        self._botao(linha, "Listar modelos", self._listar_modelos,
                    cor=PANEL_2, fg=CIANO).pack(side="left", padx=4)

        # Ações
        acoes = tk.Frame(dir_, bg=BG)
        acoes.pack(fill="x", pady=(12, 6))
        self.btn_run = self._botao(acoes, "▶  AUDITAR", self._iniciar)
        self.btn_run.pack(side="left")
        self.btn_stop = self._botao(acoes, "■ Parar", self._parar, cor=PANEL_2, fg=ERRO)
        self.btn_stop.pack(side="left", padx=8)
        self.btn_stop.config(state="disabled")
        self.btn_save = self._botao(acoes, "💾 Guardar relatório", self._guardar,
                                    cor=PANEL_2, fg=OK)
        self.btn_save.pack(side="right")
        self.btn_save.config(state="disabled")

        self.var_estado = tk.StringVar(value="Pronto.")
        tk.Label(dir_, textvariable=self.var_estado, bg=BG, fg=CIANO,
                 font=("Consolas", 9), anchor="w").pack(fill="x")
        self.barra = ttk.Progressbar(dir_, style="Neon.Horizontal.TProgressbar",
                                     mode="determinate")
        self.barra.pack(fill="x", pady=(4, 8))

        # Log + relatório
        painel = tk.PanedWindow(dir_, orient="vertical", bg=BG, sashwidth=6, bd=0)
        painel.pack(fill="both", expand=True)

        self.log = scrolledtext.ScrolledText(
            painel, height=7, bg="#080413", fg=OK, insertbackground=CIANO,
            relief="flat", font=("Consolas", 9), state="disabled", wrap="word")
        painel.add(self.log, minsize=80)

        self.saida = scrolledtext.ScrolledText(
            painel, bg=PANEL, fg=TEXTO, insertbackground=CIANO, relief="flat",
            font=("Consolas", 10), wrap="word", padx=10, pady=8)
        self.saida.insert("1.0", "O relatório aparece aqui.")
        painel.add(self.saida, minsize=160)

        self.saida.tag_configure("h", foreground=ROXO, font=("Consolas", 11, "bold"))
        self.saida.tag_configure("crit", foreground=ERRO)

    def _carregar_imagem(self, pai):
        if not IMAGEM.exists():
            tk.Label(pai, text="🐜", bg=PANEL, fg=ROXO, font=("Segoe UI", 80)).pack(pady=30)
            return
        try:
            if HAS_PIL:
                img = Image.open(IMAGEM).convert("RGB")
                img = img.resize((310, 310), Image.LANCZOS)
                self.foto = ImageTk.PhotoImage(img)
            else:
                base = tk.PhotoImage(file=str(IMAGEM))
                fator = max(1, base.width() // 310)
                self.foto = base.subsample(fator, fator)
            tk.Label(pai, image=self.foto, bg=PANEL, bd=0).pack(pady=(15, 0))
        except Exception as e:
            tk.Label(pai, text=f"(imagem não carregou: {e})", bg=PANEL,
                     fg=ERRO, wraplength=300).pack(pady=30)

    # ------------------------------------------------------------ helpers
    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", f"{time.strftime('%H:%M:%S')}  {msg}\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _escolher_pasta(self):
        p = filedialog.askdirectory(title="Escolhe a pasta do projeto")
        if p:
            self.var_alvo.set(p)

    def _escolher_ficheiro(self):
        p = filedialog.askopenfilename(title="Escolhe o ficheiro")
        if p:
            self.var_alvo.set(p)

    def _cliente(self):
        chave = self.var_chave.get().strip()
        if not chave:
            messagebox.showwarning("Chave em falta", "Cola a tua GEMINI_API_KEY.")
            return None
        return genai.Client(api_key=chave)

    def _listar_modelos(self):
        client = self._cliente()
        if not client:
            return
        self._log("A listar modelos...")

        def trabalho():
            try:
                nomes = core.listar_candidatos(client)
                self.fila.put(("modelos", nomes))
            except Exception as e:
                self.fila.put(("log", f"Erro a listar modelos: {e}"))

        threading.Thread(target=trabalho, daemon=True).start()

    def _guardar(self):
        if not self.relatorio_atual:
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".md", initialfile="relatorio_auditoria.md",
            filetypes=[("Markdown", "*.md"), ("Texto", "*.txt")])
        if p:
            Path(p).write_text(self.relatorio_atual, encoding="utf-8")
            self._log(f"Relatório guardado em {p}")

    # ------------------------------------------------------------- ações
    def _iniciar(self):
        alvo = Path(self.var_alvo.get().strip())
        if not self.var_alvo.get().strip() or not alvo.exists():
            messagebox.showwarning("Alvo inválido", "Escolhe um ficheiro ou pasta que exista.")
            return
        client = self._cliente()
        if not client:
            return

        self.parar.clear()
        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_save.config(state="disabled")
        self.saida.delete("1.0", "end")
        self.barra["value"] = 0
        self.relatorio_atual = ""

        args = (client, alvo, self.var_foco.get(), self.var_modelo.get().strip() or "auto")
        self.thread = threading.Thread(target=self._trabalho, args=args, daemon=True)
        self.thread.start()

    def _parar(self):
        self.parar.set()
        self.var_estado.set("A parar depois do ficheiro atual...")

    # ---------------------------------------------------- thread de trabalho
    def _escolher_modelo(self, client, max_testes=10):
        candidatos = core.listar_candidatos(client)
        if not candidatos:
            raise RuntimeError("Nenhum modelo Gemini disponível para esta chave.")
        self.fila.put(("log", f"{len(candidatos)} modelos encontrados. A testar do melhor para o pior..."))
        for nome in candidatos[:max_testes]:
            if self.parar.is_set():
                raise RuntimeError("Cancelado.")
            self.fila.put(("estado", f"A testar {nome}..."))
            try:
                r = client.models.generate_content(
                    model=nome, contents="Responde apenas: OK",
                    config=types.GenerateContentConfig(max_output_tokens=64))
                if r.text is not None:
                    self.fila.put(("log", f"✔ {nome}"))
                    return nome
                self.fila.put(("log", f"✘ {nome} (resposta vazia)"))
            except Exception as e:
                motivo = str(e).splitlines()[0][:90]
                self.fila.put(("log", f"✘ {nome} ({motivo})"))
        raise RuntimeError("Nenhum modelo respondeu. Verifica a chave e a quota.")

    def _trabalho(self, client, alvo, foco, modelo):
        try:
            ficheiros = core.recolher_ficheiros(alvo)
            if not ficheiros:
                raise RuntimeError("Nenhum ficheiro de código encontrado.")

            if modelo == "auto":
                modelo = self._escolher_modelo(client)
            self.fila.put(("log", f"{len(ficheiros)} ficheiro(s) · modelo {modelo} · foco {foco}"))

            partes = [f"# Relatório de auditoria\n\nFoco: **{foco}** | Modelo: `{modelo}`\n"]
            self.fila.put(("append", f"# Relatório de auditoria\nFoco: {foco} | Modelo: {modelo}\n\n", "h"))

            total = len(ficheiros)
            for i, f in enumerate(ficheiros, 1):
                if self.parar.is_set():
                    self.fila.put(("log", "Interrompido pelo utilizador."))
                    break
                self.fila.put(("estado", f"[{i}/{total}] {f.name}"))
                resultado = core.auditar_ficheiro(client, modelo, f, foco)
                partes.append(f"\n---\n\n## `{f}`\n\n{resultado}\n")
                self.fila.put(("append", f"## {f}\n", "h"))
                self.fila.put(("append", resultado + "\n\n", None))
                self.fila.put(("progresso", i, total))

            self.fila.put(("fim", "\n".join(partes)))
        except Exception as e:
            self.fila.put(("erro", str(e)))

    # ------------------------------------------------------- fila → UI
    def _processar_fila(self):
        try:
            while True:
                item = self.fila.get_nowait()
                tipo = item[0]
                if tipo == "log":
                    self._log(item[1])
                elif tipo == "estado":
                    self.var_estado.set(item[1])
                elif tipo == "progresso":
                    self.barra["value"] = item[1] * 100 / item[2]
                elif tipo == "append":
                    self.saida.insert("end", item[1], item[2] or ())
                    self.saida.see("end")
                elif tipo == "modelos":
                    self.combo_modelo["values"] = ["auto"] + item[1]
                    self._log(f"{len(item[1])} modelos disponíveis (lista no seletor).")
                elif tipo == "fim":
                    self.relatorio_atual = item[1]
                    self.var_estado.set("Concluído.")
                    self._log("Auditoria concluída.")
                    self._terminar(guardar=True)
                elif tipo == "erro":
                    self.var_estado.set("Erro.")
                    self._log(f"ERRO: {item[1]}")
                    messagebox.showerror("Erro", item[1])
                    self._terminar(guardar=bool(self.relatorio_atual))
        except queue.Empty:
            pass
        self.after(100, self._processar_fila)

    def _terminar(self, guardar):
        self.btn_run.config(state="normal")
        self.btn_stop.config(state="disabled")
        if guardar:
            self.btn_save.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
