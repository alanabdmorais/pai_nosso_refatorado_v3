# -*- coding: utf-8 -*-
"""
constants.py — Constantes da v3 (sem classificação morfológica).
Cada idioma tem uma cor sólida para a legenda inteira.
"""

IDIOMAS: list[str] = ["pt", "en", "es", "fr"]

SIGLAS_IDIOMAS: dict[str, str] = {
    "pt": "PT-BR", "en": "EN-US", "es": "ES-ES", "fr": "FR-FR",
}

NOMES_IDIOMA: dict[str, str] = {
    "pt": "português", "en": "inglês", "es": "espanhol", "fr": "francês",
}

# Posições Y na tela (pixels, 1280×720)
POSICOES_Y:  dict[str, int] = {"pt": 100, "en": 180, "es": 260, "fr": 340}
POS_SIGLA_Y: dict[str, int] = {"pt":  65, "en": 145, "es": 225, "fr": 305}

LARGURA_TELA: int = 1280
ALTURA_TELA:  int = 720
CENTRO_X:     int = LARGURA_TELA // 2

TAMANHO_FONTE_LEGENDA: int = 26
TAMANHO_FONTE_SIGLA:   int = 20
BOX_BORDER:            int = 8

# Cor por idioma: texto branco sobre fundo colorido
CORES_IDIOMA: dict[str, dict[str, str]] = {
    "pt": {"texto": "#FFFFFF", "fundo": "#1a6b1a"},  # verde
    "en": {"texto": "#FFFFFF", "fundo": "#1a3a8f"},  # azul
    "es": {"texto": "#FFFFFF", "fundo": "#8f1a1a"},  # vermelho
    "fr": {"texto": "#FFFFFF", "fundo": "#6a1a8f"},  # roxo
}

FASES_PIPELINE: list[str] = [
    "audio_gerado", "srt_pt_bruto", "srt_pt_corrigido",
    "srt_traduzidos", "clipes_cortados",
    "video_base_criado", "legendas_queimadas",
]

PROMPT_SISTEMA_CORRECAO_PT = (
    "Você é um especialista em português e textos religiosos. "
    "Corrija APENAS erros de transcrição, mantendo a segmentação exata. "
    "Retorne SOMENTE um JSON válido. "
    'Formato: [{"id": 1, "texto": "frase corrigida"}, ...]'
)

PROMPT_SISTEMA_REDISTRIBUICAO = (
    "Você é um especialista em alinhamento de legendas multilíngues. "
    "Redistribua o texto em exatamente {N} segmentos seguindo os cortes do idioma de origem. "
    "Mantenha o sentido litúrgico e naturalidade no idioma de destino. "
    "Retorne SOMENTE um JSON válido. "
    'Formato: [{{"id": 1, "texto": "frase em {idioma}"}}]'
)
