# -*- coding: utf-8 -*-
"""pai_nosso_refatorado_v3.ipynb

# 🎬 Pipeline Multilíngue v3 — Legendas por Idioma (sem morfologia)

Versão simplificada: cada idioma aparece numa cor sólida, sem análise gramatical.

**Estratégia de segmentação:**
- **Whisper** é o mestre de timestamps e segmentação (frases completas, pausas naturais)
- **YouTube** fornece o texto correto em PT (substitui o texto do Whisper, mantém os cortes)
- **Groq** traduz PT → EN/ES/FR respeitando os mesmos segmentos

| # | Fase | O que faz |
|---|------|-----------|
| 0 | Setup | Instala deps, monta Drive, importa módulos |
| Init | — | Cria config e pipeline |
| B0 | YouTube | Baixa legenda PT para texto de referência (opcional) |
| 1 | Áudio | Edge TTS → .wav |
| 2 | Whisper | Transcrição → SRT mestre (segmentação correta) |
| 3 | Correção PT | Substitui texto Whisper pelo texto YouTube (mantém timestamps) |
| 4 | Traduções | Groq traduz PT → EN/ES/FR |
| 5 | Vídeo | Clipes + áudio + trilha + legendas coloridas |

> **Drive:** `MyDrive/pai_nosso_refatorado_v3/pipeline/`
"""

# ╔══════════════════════════════════════════════════════════════════╗
# ║  CÉLULA 0 — Setup (rode uma vez por sessão)                    ║
# ╚══════════════════════════════════════════════════════════════════╝

!apt-get -qq -y install ffmpeg espeak-ng > /dev/null 2>&1
print('✅ ffmpeg + espeak-ng')

!pip install -q edge-tts openai-whisper openai pandas gdown yt-dlp nest_asyncio
print('✅ pacotes Python')

from google.colab import drive, userdata
try:
    drive.flush_and_unmount()
except:
    pass
drive.mount('/content/drive', force_remount=True)
print('✅ Drive montado')

import shutil, os, sys, logging
from pathlib import Path

PASTA_MODULOS = '/content/drive/MyDrive/pai_nosso_refatorado_v3/pipeline/modulos'
DESTINO       = '/content/pipeline'

if os.path.exists(DESTINO):
    shutil.rmtree(DESTINO)

if os.path.exists(PASTA_MODULOS):
    shutil.copytree(PASTA_MODULOS, DESTINO)
    print(f'✅ Módulos copiados → {DESTINO}')
    for f in sorted(Path(DESTINO).glob('*.py')):
        print(f'   📄 {f.name}')
else:
    print(f'❌ Pasta não encontrada: {PASTA_MODULOS}')

if DESTINO not in sys.path:
    sys.path.insert(0, DESTINO)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(name)-22s  %(levelname)s  %(message)s',
    datefmt='%H:%M:%S',
)
os.chdir('/content')
print('\n✅ Setup concluído!')

# ╔══════════════════════════════════════════════════════════════════╗
# ║  INICIALIZAÇÃO                                                 ║
# ╚══════════════════════════════════════════════════════════════════╝

import nest_asyncio
nest_asyncio.apply()

from config import PipelineConfig
from groq_client import GroqClient
from video_pipeline import VideoPipeline
from checkpoint import Checkpoint
from google.colab import userdata

config = PipelineConfig(
    NOME_ORACAO = 'pai_nosso',
    # Para outra oração:
    # NOME_ORACAO  = 'ave_maria',
    # TEXTO_ORACAO = 'Ave Maria, cheia de graça...',
    # VOZ_EDGE     = 'pt-BR-FranciscaNeural',
)

groq     = GroqClient(api_key=userdata.get('GROQ_KEY'), nome_oracao=config.NOME_ORACAO)
pipeline = VideoPipeline(config, groq)
cp       = Checkpoint()

print(config.resumo())
print()
print(cp.resumo())
print(f'\n▶  Próxima fase: {cp.proxima_fase_pendente() or "(tudo concluído)"}')

# ╔══════════════════════════════════════════════════════════════════╗
# ║  🔍 VERIFICAÇÃO DO DRIVE                                       ║
# ╚══════════════════════════════════════════════════════════════════╝

from pathlib import Path

BASE = Path('/content/drive/MyDrive/pai_nosso_refatorado_v3/pipeline')

print("═" * 60)
print("📁 ESTRUTURA DO DRIVE")
print("═" * 60)

for rotulo, pasta in [
    ('modulos',   BASE / 'modulos'),
    ('correcoes', BASE / f'correcoes/{config.NOME_ORACAO}'),
    ('brutos',    BASE / f'brutos/{config.NOME_ORACAO}'),
]:
    print(f"\n📁 {pasta}")
    if pasta.exists():
        for f in sorted(pasta.iterdir()):
            print(f"   ✅ {f.name}  ({f.stat().st_size/1024:.1f} KB)")
    else:
        print("   (ainda não criada)")
print("═" * 60)

# ╔══════════════════════════════════════════════════════════════════╗
# ║  🧹 LIMPEZA SELETIVA                                           ║
# ╚══════════════════════════════════════════════════════════════════╝

from pathlib import Path
import shutil, sys

def limpeza_seletiva():
    print("═" * 65)
    print("🧹 LIMPEZA SELETIVA")
    print("═" * 65)
    print("  1  🎵 Áudios (.wav)")
    print("  2  📝 Legendas (.srt, .ass) [mantém yt_ref]")
    print("  3  🎬 Vídeos gerados")
    print("  4  📌 Checkpoint")
    print("  5  📁 Pastas temporárias")
    print("  6  📦 Cache Python")
    print("  7  🗑️ Cache FASE 3 (fase3_cache.json)")
    print("  8  🔥 TUDO local (1–7)")
    print("  0  Sair")
    print("═" * 65)
    opcoes = input("\nEscolha: ").strip()
    if opcoes == '0': return
    sel = [int(x) for x in opcoes.split(',')]
    cont = 0

    def rm(f):
        nonlocal cont; f.unlink(); cont += 1; print(f"   🗑️ {f.name}")
    def rmdir(d):
        nonlocal cont; shutil.rmtree(d); cont += 1; print(f"   🗑️ {d.name}/")

    if any(x in sel for x in [1, 8]):
        for f in Path('.').glob('*_audio.wav'): rm(f)
    if any(x in sel for x in [2, 8]):
        for f in Path('.').glob('*.srt'):
            if 'yt_ref' not in f.name: rm(f)
        for f in Path('.').glob('*.ass'): rm(f)
    if any(x in sel for x in [3, 8]):
        for pat in ['*_base.mp4','*_final.mp4','clipe_*.mp4','temp_*.mp4']:
            for f in Path('.').glob(pat): rm(f)
    if any(x in sel for x in [4, 8]):
        cp = Path('checkpoint.json')
        if cp.exists(): rm(cp)
    if any(x in sel for x in [5, 8]):
        for p in ['clipes_cortados','clipes_prontos','temp_raw','__pycache__']:
            pp = Path(p)
            if pp.exists(): rmdir(pp)
    if any(x in sel for x in [6, 8]):
        mods = ['groq_client','video_pipeline','config','ffmpeg_utils',
                'checkpoint','drive_utils','srt_utils','models','constants']
        for m in mods:
            if m in sys.modules:
                del sys.modules[m]; cont += 1; print(f"   🗑️ {m}")
    if any(x in sel for x in [7, 8]):
        f = Path('/content/fase3_cache.json')
        if f.exists(): rm(f)

    print(f"\n✅ {cont} item(ns) removido(s)")

limpeza_seletiva()

"""### 🔵 Célula B0 — Baixar legenda PT do YouTube (opcional)
Baixa a legenda oficial em PT para usar como **texto de referência** na Fase 3.
Se pular, a Fase 3 usa apenas o Whisper (texto menos preciso).
"""

# ╔══════════════════════════════════════════════════════════════════╗
# ║  CÉLULA B0 — Baixar legenda PT do YouTube (texto de referência)║
# ╚══════════════════════════════════════════════════════════════════╝

from pathlib import Path
import subprocess

print("═" * 60)
print("📺 BAIXANDO LEGENDA PT DO YOUTUBE")
print("═" * 60)

# ── Coloque a URL do vídeo com legenda PT abaixo ─────────────────────────────
URL_PT = 'https://www.youtube.com/watch?v=p5Vg7Vn2KeM'

cookies_flag = ['--cookies', 'cookies.txt'] if Path('cookies.txt').exists() else []
nome_ref = f'{config.NOME_ORACAO}_yt_ref_pt.srt'

print(f'⬇️  {URL_PT[:60]}')
cmd = [
    'yt-dlp', '--write-sub', '--sub-lang', 'pt', '--write-auto-sub',
    '--skip-download', '--sub-format', 'srt', '--convert-subs', 'srt',
    '--output', f'{config.NOME_ORACAO}_yt_ref', *cookies_flag, URL_PT
]
subprocess.run(cmd, capture_output=True, text=True)

encontrado = False
for c in Path('.').glob(f'{config.NOME_ORACAO}_yt_ref*.srt'):
    if c.name != nome_ref:
        c.rename(nome_ref)
    from srt_utils import ler_srt
    legs = ler_srt(Path(nome_ref))
    print(f'✅ {nome_ref} ({len(legs)} segmentos)')
    print(f'   Preview: {legs[0].texto[:70]}')
    encontrado = True
    break

if not encontrado:
    print('⚠️  Legenda PT não disponível — Fase 3 usará só o Whisper')

"""### ▶ Fase 1 — Áudio (Edge TTS)"""

# ── FASE 1 ────────────────────────────────────────────────────────────────────
audio = pipeline.fase1_gerar_audio()
print(f'✅ {audio}  ({audio.stat().st_size/1024:.0f} KB)')

"""### ▶ Fase 2 — Whisper (mestre de segmentação)
O Whisper é o **mestre de timestamps**: segmenta por pausas naturais do áudio,
produzindo frases completas — muito melhor que o YouTube para sincronização.
"""

# ╔══════════════════════════════════════════════════════════════════╗
# ║  FASE 2 — Whisper (MESTRE de segmentação e timestamps)         ║
# ╚══════════════════════════════════════════════════════════════════╝

from srt_utils import ler_srt

print("═" * 65)
print("🎙️ FASE 2 — TRANSCRIÇÃO WHISPER")
print("═" * 65)
print("O Whisper define os timestamps e os cortes de frase.")
print("O texto será aprimorado na Fase 3 com a referência do YouTube.")
print("═" * 65)

srt_bruto = pipeline.fase2_transcrever_whisper()

legendas_whisper = ler_srt(srt_bruto)
print(f'\n✅ Whisper: {len(legendas_whisper)} segmentos')
for leg in legendas_whisper:
    print(f'  [{leg.id:02d}]  {leg.inicio_str} → {leg.fim_str}  |  {leg.texto}')

"""### ▶ Fase 3 — Correção PT (texto YouTube + timestamps Whisper)"""

# ╔══════════════════════════════════════════════════════════════════╗
# ║  FASE 3 — Aprimorar texto PT (mantém segmentação do Whisper)   ║
# ╚══════════════════════════════════════════════════════════════════╝

from pathlib import Path
from srt_utils import ler_srt, salvar_srt
import json, time, re
from datetime import datetime
from openai import OpenAI
from google.colab import userdata

print("═" * 70)
print("📝 FASE 3 — TEXTO PT APRIMORADO (timestamps = Whisper)")
print("═" * 70)

srt_whisper = Path(f'{config.NOME_ORACAO}_pt_whisper.srt')
ref_path    = Path(f'{config.NOME_ORACAO}_yt_ref_pt.srt')

if not srt_whisper.exists():
    raise FileNotFoundError("SRT do Whisper não encontrado — execute a Fase 2 primeiro")

legendas = ler_srt(srt_whisper)

if ref_path.exists():
    ref_legs = ler_srt(ref_path)
    texto_referencia = " ".join(leg.texto for leg in ref_legs)
    print(f"✅ Referência YouTube encontrada ({len(ref_legs)} segmentos)")
    print(f"   Texto: {texto_referencia[:80]}...")
else:
    texto_referencia = ""
    print("⚠️  Referência YouTube não encontrada — corrigindo só com Groq")

DELAY = 10
DELAY_RL = 60
cache_path = Path('/content/fase3_cache.json')
cache = {}

if cache_path.exists():
    try:
        cache = json.loads(cache_path.read_text())
        print(f"📁 Cache: {len(cache)} legendas já corrigidas")
    except: pass

APIS = [
    {'nome': 'Groq',    'key': 'GROQ_KEY',    'url': 'https://api.groq.com/openai/v1',  'modelo': 'llama-3.3-70b-versatile'},
    {'nome': 'Mistral', 'key': 'MISTRAL_KEY',  'url': 'https://api.mistral.ai/v1',       'modelo': 'mistral-small-latest'},
]

clientes = []
for a in APIS:
    try:
        k = userdata.get(a['key'])
        if k: clientes.append({'nome': a['nome'], 'client': OpenAI(api_key=k, base_url=a['url']), 'modelo': a['modelo']})
    except: pass

idx_api = 0

def corrigir_legenda(leg):
    global idx_api
    prompt_ref = f"\n\nReferência do texto oficial: '{texto_referencia[:400]}'" if texto_referencia else ""
    prompt = (
        f"Corrija APENAS os erros de transcrição nesta legenda PT:\n"
        f"'{leg.texto}'"
        f"{prompt_ref}\n\n"
        f"REGRAS:\n"
        f"- Mantenha o MESMO número de palavras (não adicione nem remova)\n"
        f"- Corrija apenas erros óbvios de transcrição\n"
        f"- Retorne SOMENTE o texto corrigido, sem aspas nem explicações"
    )
    for _ in range(len(clientes) * 2):
        api = clientes[idx_api % len(clientes)]
        try:
            r = api['client'].chat.completions.create(
                model=api['modelo'],
                messages=[
                    {"role": "system", "content": "Corrija erros de transcrição. Responda apenas o texto."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1, max_tokens=200,
            )
            return r.choices[0].message.content.strip().strip('"').strip("'")
        except Exception as e:
            err = str(e).lower()
            if '429' in err or 'rate limit' in err:
                print(f"   ⚠️ Rate limit — aguardando {DELAY_RL}s...")
                time.sleep(DELAY_RL)
            idx_api += 1
    return leg.texto

inicio = datetime.now()
for i, leg in enumerate(legendas):
    chave = str(leg.id)
    if chave in cache:
        leg.texto = cache[chave]
        print(f"  [{i+1}/{len(legendas)}] ⏭️ cache — {leg.texto[:55]}")
        continue

    print(f"\n  [{i+1}/{len(legendas)}] Whisper: {leg.texto}")
    corrigido = corrigir_legenda(leg)
    leg.texto = corrigido
    cache[chave] = corrigido
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
    print(f"               ✅ Corrigido: {corrigido}")

    if i < len(legendas) - 1:
        for s in range(DELAY, 0, -2):
            print(f"  ⏳ {s}s...", end='\r')
            time.sleep(2)
        print()

from srt_utils import eliminar_gaps, salvar_srt
legendas = eliminar_gaps(legendas)
srt_pt = Path(config.NOME_SRT_PT)
salvar_srt(legendas, srt_pt)

tempo = (datetime.now() - inicio).seconds
print("\n" + "═" * 70)
print(f"✅ FASE 3 CONCLUÍDA! {tempo//60}min {tempo%60}s | {len(legendas)} legendas")
print("═" * 70)
print("\n📋 Resultado:")
for leg in legendas:
    print(f"  [{leg.id:02d}]  {leg.inicio_str} → {leg.fim_str}  |  {leg.texto}")

"""### ▶ Fase 4 — Traduções EN/ES/FR"""

# ── FASE 4 ────────────────────────────────────────────────────────────────────
from srt_utils import ler_srt

legendas_pt = ler_srt(config.NOME_SRT_PT)
pipeline.legendas_idiomas = pipeline.fase4_traduzir(legendas_pt)

print('Primeiras 2 legendas por idioma:')
for i in range(min(2, len(legendas_pt))):
    for lang in config.IDIOMAS:
        legs = pipeline.legendas_idiomas.get(lang, [])
        if i < len(legs):
            print(f'  {lang.upper()}: {legs[i].texto}')
    print()

"""### ▶ Fase 5 — Vídeo final (clipes + legendas coloridas)"""

# ╔══════════════════════════════════════════════════════════════════╗
# ║  FASE 5 — Clipes + Vídeo base + Legendas coloridas por idioma  ║
# ╚══════════════════════════════════════════════════════════════════╝

from pathlib import Path
from ffmpeg_utils import gerar_ass, queimar_legendas_ass
from srt_utils import ler_srt

print("═" * 65)
print("🎬 FASE 5 — VÍDEO FINAL")
print("═" * 65)

# Carregar traduções se pipeline.legendas_idiomas estiver vazio
if not pipeline.legendas_idiomas:
    legendas_pt = ler_srt(config.NOME_SRT_PT)
    pipeline.legendas_idiomas = pipeline._carregar_todos_srts(legendas_pt)

# Preview das cores
print("\n🎨 Cores por idioma:")
for lang, cores in config.CORES_IDIOMA.items():
    sigla = config.SIGLAS_IDIOMAS[lang]
    print(f"  {sigla}: texto={cores['texto']}  fundo={cores['fundo']}")

# Fase 6: clipes
print("\n📹 Baixando e cortando clipes...")
pipeline.fase6_baixar_clipes()

# Fase 7: vídeo base
print("\n🎵 Criando vídeo base (narração + trilha)...")
video_base = pipeline.fase7_criar_video_base()
print(f"✅ {video_base}")

# Fase 8: legendas coloridas
print("\n🖊️ Gerando legendas ASS coloridas por idioma...")
ass_path = gerar_ass(pipeline.legendas_idiomas, config)
print(f"✅ {ass_path}")

video_final = Path(f'{config.NOME_ORACAO}_v3_final.mp4')
queimar_legendas_ass(video_base, ass_path, video_final)

print("\n" + "═" * 65)
print(f"🎉 VÍDEO FINAL: {video_final}")
print(f"   Tamanho: {video_final.stat().st_size / 1_048_576:.1f} MB")
print("═" * 65)

from IPython.display import Video, display
display(Video(str(video_final), embed=True, width=800))

"""### 🚀 RUN ALL"""

# ╔══════════════════════════════════════════════════════════════════╗
# ║  RUN ALL — Pipeline completo                                   ║
# ╚══════════════════════════════════════════════════════════════════╝

resultado = pipeline.run()
if resultado:
    print(f'\n🎉 {resultado}')
    print(pipeline._cp.resumo())

"""### 🔧 Utilitários"""

# ╔══════════════════════════════════════════════════════════════════╗
# ║  UTILITÁRIOS                                                   ║
# ╚══════════════════════════════════════════════════════════════════╝

from checkpoint import Checkpoint
cp = Checkpoint()
print(cp.resumo())

# cp.resetar_tudo()
# cp.reiniciar_de('srt_pt_corrigido')
