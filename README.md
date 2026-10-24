# 🐜 DeFiAnts Code Auditor

Auditor de código com a **API do Gemini**, com interface gráfica (Tkinter) e linha de comandos.
Percorre um ficheiro ou projeto, envia cada ficheiro ao Gemini e gera um relatório em Markdown com
severidade, linhas aproximadas, explicação e correção sugerida.

<p align="center">
  <img src="assets/defiants.png" alt="DeFiAnts" width="320">
</p>

> **BUILD · HODL · EARN · REPEAT**

## Funcionalidades

- Escolha **automática do melhor modelo disponível** na tua chave (testa do melhor para o pior e usa o primeiro que responder — útil no plano free, onde os modelos `pro` costumam dar erro de quota)
- Três focos de análise: `geral`, `seguranca` e `performance`
- Interface gráfica com tema DeFiAnts, barra de progresso, log em direto e botão de parar
- Relatório em Markdown
- Ignora pastas pesadas (`.git`, `node_modules`, `venv`, ...) e **nunca envia** ficheiros como `.env`, `credentials.json` ou `id_rsa`
- Repete automaticamente chamadas que falhem por quota ou rede

## Instalação

```bash
git clone https://github.com/<o-teu-utilizador>/defiants-code-auditor.git
cd defiants-code-auditor
pip install -r requirements.txt
```

Cria uma chave em <https://aistudio.google.com/apikey> e define-a como variável de ambiente:

```bash
# Linux / macOS
export GEMINI_API_KEY="a_tua_chave"

# Windows (PowerShell)
$env:GEMINI_API_KEY="a_tua_chave"
```

## Uso

### Interface gráfica

```bash
python gui_defiants.py
```

Escolhe a pasta ou o ficheiro, o foco e (opcionalmente) o modelo, e carrega em **AUDITAR**.
A chave também pode ser colada na própria janela; não é guardada em disco.

> O Tkinter vem com o Python no Windows e macOS. Em Linux pode ser preciso instalar
> `python3-tk` (ex.: `sudo apt install python3-tk`).

### Linha de comandos

```bash
python auditor_codigo.py ./meu_projeto
python auditor_codigo.py ficheiro.py --foco seguranca
python auditor_codigo.py . --modelo gemini-2.5-flash --saida relatorio.md
```

| Opção      | Descrição                                              | Padrão                   |
|------------|--------------------------------------------------------|--------------------------|
| `alvo`     | Ficheiro ou pasta a auditar                            | —                        |
| `--foco`   | `geral`, `seguranca` ou `performance`                  | `geral`                  |
| `--modelo` | Nome do modelo, ou `auto` para escolher o melhor       | `auto`                   |
| `--saida`  | Ficheiro do relatório                                  | `relatorio_auditoria.md` |

## Estrutura

```
defiants-code-auditor/
├── auditor_codigo.py   # lógica + CLI
├── gui_defiants.py     # interface gráfica
├── assets/defiants.png # imagem do tema
├── requirements.txt
└── LICENSE
```

## Privacidade e segurança

- O código auditado é enviado para os servidores da Google através da API do Gemini. Não auditar código que não possas partilhar.
- Remove chaves e segredos hardcoded **antes** de auditar, e nunca faças commit da tua `GEMINI_API_KEY`.
- A análise é feita por IA e pode falhar ou inventar problemas. Trata o relatório como ajuda, não como auditoria definitiva — sobretudo em código que mexe com fundos ou chaves privadas.

## Licença

MIT — ver [LICENSE](LICENSE).
