#!/usr/bin/env python3
"""
Auditor de código com a API do Gemini.

Instalação:
    pip install google-genai

Configuração (chave em https://aistudio.google.com/apikey):
    Windows (PowerShell):  $env:GEMINI_API_KEY="a_tua_chave"
    Linux/macOS:           export GEMINI_API_KEY="a_tua_chave"

Uso:
    python auditor_codigo.py caminho/do/projeto
    python auditor_codigo.py ficheiro.py --foco seguranca
    python auditor_codigo.py . --modelo gemini-2.5-pro --saida relatorio.md
    (por omissão usa --modelo auto: testa os modelos do melhor para o pior
     e usa o primeiro que funcionar com a tua chave free)
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

MODELO_PADRAO = "auto"  # "auto" = escolhe o melhor modelo que funcione no teu plano free

# Modelos que não servem para analisar código
EXCLUIR_NO_NOME = (
    "image", "tts", "live", "audio", "embedding", "robotics", "computer-use",
    "imagen", "veo", "aqa", "learnlm", "gemma", "vision", "native",
)
TIER = {"pro": 3, "flash": 2, "flash-lite": 1}

EXTENSOES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".c", ".cpp",
    ".h", ".cs", ".php", ".rb", ".sol", ".sh", ".sql", ".html", ".css",
}

PASTAS_IGNORADAS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
    ".idea", ".vscode", "target",
}

# Nunca enviar ficheiros que costumam conter segredos
FICHEIROS_IGNORADOS = {".env", ".env.local", "secrets.json", "id_rsa", "credentials.json"}

TAMANHO_MAX = 100_000  # caracteres por ficheiro

FOCOS = {
    "geral": "bugs, erros de lógica, tratamento de erros, qualidade e manutenção",
    "seguranca": (
        "vulnerabilidades de segurança: segredos/chaves hardcoded, injeção (SQL/comando), "
        "desserialização insegura, validação de input, uso inseguro de rede/ficheiros, "
        "gestão de chaves privadas e transações (se for código cripto)"
    ),
    "performance": "problemas de desempenho, ciclos ineficientes, chamadas de rede repetidas, memória",
}

PROMPT = """És um auditor de código sénior. Analisa o ficheiro abaixo com foco em: {foco}.

Regras:
- Responde em português de Portugal.
- Lista só problemas reais, cada um com: severidade (CRÍTICO/ALTO/MÉDIO/BAIXO),
  linha(s) aproximada(s), explicação curta e correção sugerida (com snippet quando útil).
- Não inventes problemas. Se não encontrares nada relevante, diz "Sem problemas relevantes".
- Termina com uma nota de 0 a 10 para o ficheiro.

Ficheiro: {nome}
```
{codigo}
```"""


def pontuar(nome: str):
    """Ordena modelos: versão mais recente > pro > flash > flash-lite > estável > preview."""
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", nome)
    versao = float(m.group(1)) if m else 0.0
    if "flash-lite" in nome:
        tier = TIER["flash-lite"]
    elif "flash" in nome:
        tier = TIER["flash"]
    elif "pro" in nome:
        tier = TIER["pro"]
    else:
        tier = 0
    estavel = 0 if ("preview" in nome or "exp" in nome) else 1
    return (versao, tier, estavel)


def listar_candidatos(client):
    candidatos = []
    for m in client.models.list():
        nome = (m.name or "").replace("models/", "")
        acoes = m.supported_actions or []
        if not nome.startswith("gemini-") or "generateContent" not in acoes:
            continue
        if any(x in nome for x in EXCLUIR_NO_NOME):
            continue
        # ignora aliases datados duplicados (ex.: -001, -0827) se existir o alias simples
        candidatos.append(nome)
    return sorted(set(candidatos), key=pontuar, reverse=True)


def escolher_modelo(client, max_testes: int = 10) -> str:
    """Testa os modelos do melhor para o pior e devolve o primeiro que responde
    com a tua chave (no plano free, os 'pro' costumam dar erro de quota)."""
    candidatos = listar_candidatos(client)
    if not candidatos:
        sys.exit("Não encontrei modelos Gemini disponíveis para esta chave.")

    print(f"{len(candidatos)} modelos encontrados. A testar do melhor para o pior...")
    for nome in candidatos[:max_testes]:
        try:
            r = client.models.generate_content(
                model=nome,
                contents="Responde apenas: OK",
                config=types.GenerateContentConfig(max_output_tokens=64),
            )
            if r.text is not None:
                print(f"  ✔ {nome}")
                return nome
            print(f"  ✘ {nome} (resposta vazia)")
        except Exception as e:
            motivo = str(e).splitlines()[0][:90]
            print(f"  ✘ {nome} ({motivo})")
    sys.exit("Nenhum modelo respondeu. Verifica a chave e a quota em aistudio.google.com.")


def recolher_ficheiros(alvo: Path):
    if alvo.is_file():
        return [alvo]
    encontrados = []
    for raiz, pastas, nomes in os.walk(alvo):
        pastas[:] = [p for p in pastas if p not in PASTAS_IGNORADAS]
        for nome in nomes:
            caminho = Path(raiz) / nome
            if nome in FICHEIROS_IGNORADOS:
                continue
            if caminho.suffix.lower() in EXTENSOES:
                encontrados.append(caminho)
    return sorted(encontrados)


def auditar_ficheiro(client, modelo, caminho: Path, foco: str) -> str:
    try:
        codigo = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"Erro a ler o ficheiro: {e}"

    if len(codigo) > TAMANHO_MAX:
        codigo = codigo[:TAMANHO_MAX]
        aviso = "\n\n_(ficheiro truncado por ser demasiado grande)_"
    else:
        aviso = ""

    prompt = PROMPT.format(foco=FOCOS[foco], nome=str(caminho), codigo=codigo)

    for tentativa in range(3):
        try:
            resposta = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            return (resposta.text or "Sem resposta do modelo.") + aviso
        except Exception as e:  # limites de quota, rede, etc.
            if tentativa == 2:
                return f"Erro na API: {e}"
            time.sleep(2 ** (tentativa + 1))
    return "Erro desconhecido."


def main():
    ap = argparse.ArgumentParser(description="Auditoria de código com Gemini")
    ap.add_argument("alvo", help="Ficheiro ou pasta a auditar")
    ap.add_argument("--foco", choices=FOCOS.keys(), default="geral")
    ap.add_argument("--modelo", default=MODELO_PADRAO)
    ap.add_argument("--saida", default="relatorio_auditoria.md")
    args = ap.parse_args()

    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        sys.exit("Define a variável de ambiente GEMINI_API_KEY primeiro.")

    alvo = Path(args.alvo)
    if not alvo.exists():
        sys.exit(f"Caminho não existe: {alvo}")

    ficheiros = recolher_ficheiros(alvo)
    if not ficheiros:
        sys.exit("Nenhum ficheiro de código encontrado.")

    client = genai.Client(api_key=chave)
    modelo = escolher_modelo(client) if args.modelo == "auto" else args.modelo

    print(f"\n{len(ficheiros)} ficheiro(s) a auditar com {modelo} (foco: {args.foco})")

    partes = [f"# Relatório de auditoria\n\nFoco: **{args.foco}** | Modelo: `{modelo}`\n"]
    for i, f in enumerate(ficheiros, 1):
        print(f"[{i}/{len(ficheiros)}] {f}")
        resultado = auditar_ficheiro(client, modelo, f, args.foco)
        partes.append(f"\n---\n\n## `{f}`\n\n{resultado}\n")

    Path(args.saida).write_text("\n".join(partes), encoding="utf-8")
    print(f"\nRelatório guardado em {args.saida}")


if __name__ == "__main__":
    main()
