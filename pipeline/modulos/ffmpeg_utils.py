# -*- coding: utf-8 -*-
"""
ffmpeg_utils.py — v3: legendas por cor de idioma (sem morfologia).

Cada idioma aparece numa cor sólida — sem análise de palavras.
"""

import logging
import subprocess
from pathlib import Path

from models import Legenda

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    pass


def _escapar(texto: str) -> str:
    return (texto
            .replace("\\", "\\\\")
            .replace("{",  "\\{")
            .replace("}",  "\\}")
            .replace("\n", "\\N"))


def _ms_para_ass(ms: int) -> str:
    h  = ms // 3_600_000
    m  = (ms % 3_600_000) // 60_000
    s  = (ms % 60_000) // 1_000
    cs = (ms % 1_000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _html_para_ass(hex_str: str) -> str:
    """#RRGGBB → &H00BBGGRR (formato ASS)."""
    h = hex_str.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}"


_ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: {largura}
PlayResY: {altura}
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,{fonte},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

_DIALOGO = "Dialogue: 0,{inicio},{fim},Default,,0,0,0,,{texto}\n"


def cortar_video(entrada: str, saida: Path, duracao: float) -> Path:
    cmd = [
        "ffmpeg", "-y", "-i", str(entrada),
        "-t", str(duracao),
        "-c:v", "libx264", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(saida),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise FFmpegError(f"cortar_video: {r.stderr[-300:]}")
    return saida


def criar_video_base(
    clipes: list[Path],
    audio: Path,
    musica: Path | None,
    saida: Path,
    config,
) -> Path:
    """Concatena clipes + áudio narração + trilha opcional."""
    lista = Path("lista_clipes.txt")
    lista.write_text(
        "\n".join(f"file '{c.resolve()}'" for c in clipes), encoding="utf-8"
    )

    concat = Path("temp_concat.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(lista), "-c", "copy", str(concat)],
        check=True, capture_output=True,
    )

    if musica and musica.exists():
        cmd = [
            "ffmpeg", "-y",
            "-i", str(concat), "-i", str(audio), "-i", str(musica),
            "-filter_complex",
            "[1:a]volume=1.0[narr];[2:a]volume=0.15,aloop=loop=-1:size=2e+09[mus];"
            "[narr][mus]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(saida),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(concat), "-i", str(audio),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(saida),
        ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise FFmpegError(f"criar_video_base: {r.stderr[-300:]}")
    return saida


def gerar_ass(
    legendas_por_idioma: dict[str, list[Legenda]],
    config,
    caminho_saida: Path | None = None,
) -> Path:
    """
    Gera arquivo .ass com legendas coloridas por idioma (sem morfologia).

    Cada idioma: texto branco sobre box colorido sólido.
    Siglas (PT-BR, EN-US, etc.) ficam fixas à esquerda da legenda.
    """
    if caminho_saida is None:
        caminho_saida = Path(f"legendas_{config.NOME_ORACAO}.ass")

    linhas = [_ASS_HEADER.format(
        largura=config.LARGURA_TELA,
        altura=config.ALTURA_TELA,
        fonte=config.TAMANHO_FONTE_LEGENDA,
    )]

    for lang, legendas in legendas_por_idioma.items():
        if not legendas:
            continue

        cores     = config.CORES_IDIOMA[lang]
        cor_texto = _html_para_ass(cores["texto"])
        cor_fundo = _html_para_ass(cores["fundo"])
        borda     = config.BOX_BORDER

        sigla    = config.SIGLAS_IDIOMAS.get(lang, lang.upper())
        y_sigla  = config.POS_SIGLA_Y.get(lang, 65)
        y_texto  = config.POSICOES_Y.get(lang, 100)
        fim_ms   = max(leg.fim_ms for leg in legendas) + 500

        # ── Sigla fixa (branca com caixa cinza semitransparente) ──────────────
        linhas.append(_DIALOGO.format(
            inicio=_ms_para_ass(0),
            fim   =_ms_para_ass(fim_ms),
            texto =(
                f"{{\\an2\\pos({config.LARGURA_TELA // 2},{y_sigla})"
                f"\\1c&H00FFFFFF&\\3c&H80808080&\\bord8\\shad0"
                f"\\fs{config.TAMANHO_FONTE_SIGLA}}}{sigla}"
            ),
        ))

        # ── Linhas de legenda ─────────────────────────────────────────────────
        for leg in legendas:
            texto_safe = _escapar(leg.texto)
            texto_ass  = (
                f"{{\\an2\\pos({config.LARGURA_TELA // 2},{y_texto})"
                f"\\1c{cor_texto}\\3c{cor_fundo}\\bord{borda}\\shad0"
                f"\\fs{config.TAMANHO_FONTE_LEGENDA}}}{texto_safe}"
            )
            linhas.append(_DIALOGO.format(
                inicio=_ms_para_ass(leg.inicio_ms),
                fim   =_ms_para_ass(leg.fim_ms),
                texto =texto_ass,
            ))

    caminho_saida.write_text("".join(linhas), encoding="utf-8-sig")
    logger.info("gerar_ass: %s (%d linhas)", caminho_saida.name, len(linhas))
    return caminho_saida


def queimar_legendas_ass(
    video_entrada: Path | str,
    ass_path:      Path | str,
    saida:         Path | str,
) -> Path:
    saida = Path(saida)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_entrada),
        "-vf", f"ass={ass_path}",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "copy",
        str(saida),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise FFmpegError(f"queimar_legendas_ass: {r.stderr[-300:]}")
    logger.info("queimar_legendas_ass: %s", saida.name)
    return saida
