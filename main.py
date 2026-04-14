"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   STUDIO PRO CREATOR AI — v6.0 (Timeline de Efeitos + Guia Interativo)      ║
║   Integração completa: Filtros • Vídeo • GIF • IA • Screenshot • TTS • ...  ║
║   + Edição segmentada por tempo + Ajuda contextual                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import subprocess
import warnings
import tempfile
import time
import io
import json
import math
import random
import re
import uuid
import shutil
import base64
import asyncio
import traceback
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional, Union
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass, field, asdict

warnings.filterwarnings("ignore")

# ==============================================================================
# VERIFICAÇÃO E INSTALAÇÃO DE DEPENDÊNCIAS
# ==============================================================================
def check_and_install_dependencies():
    """Verifica e instala pacotes essenciais."""
    required = {
        "streamlit": "streamlit",
        "PIL": "Pillow",
        "numpy": "numpy",
        "cv2": "opencv-python",
        "requests": "requests",
        "moviepy": "moviepy",
        "imageio_ffmpeg": "imageio-ffmpeg",
        "edge_tts": "edge-tts",
        "whisper": "openai-whisper",
    }
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Instalando pacotes faltantes: {missing}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet"] + missing)

check_and_install_dependencies()

# ==============================================================================
# IMPORTS DEFINITIVOS (com detecção aprimorada do MoviePy)
# ==============================================================================
import streamlit as st
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageOps, ImageColor, ImageFont
import numpy as np
import requests
import cv2

# ---------- MoviePy com fallback e configuração explícita do FFmpeg ----------
VIDEO_SUPPORT = False
VideoFileClip = None
concatenate_videoclips = None

try:
    # Tenta importar da forma antiga (MoviePy 1.x)
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    VIDEO_SUPPORT = True
except ImportError:
    try:
        # Tenta importar da forma nova (MoviePy 2.x)
        from moviepy.video.io.VideoFileClip import VideoFileClip
        # Procura a função de concatenação em locais conhecidos
        try:
            from moviepy.video.compositing.concatenate import concatenate_videoclips
        except ImportError:
            try:
                from moviepy.video.fx.concat import concatenate_videoclips
            except ImportError:
                # Fallback: usa a função nativa do pacote principal se existir
                try:
                    from moviepy import concatenate_videoclips
                except ImportError:
                    # Função dummy para evitar crash (edição segmentada ficará limitada)
                    def concatenate_videoclips(clips):
                        if not clips: return None
                        return clips[0]  # retorna o primeiro clipe
        VIDEO_SUPPORT = True
    except ImportError as e:
        st.error(f"❌ MoviePy não instalado: {e}")

if VIDEO_SUPPORT:
    # Configura explicitamente o FFmpeg usando imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
        # Para MoviePy 1.x
        try:
            from moviepy.config import change_settings
            change_settings({"FFMPEG_BINARY": ffmpeg_path})
        except ImportError:
            # Para MoviePy 2.x a configuração é via environment variable
            pass
        # Não exibe mensagem de sucesso para não poluir a interface (já temos o status na sidebar)
    except Exception as e:
        VIDEO_SUPPORT = False
        st.warning(f"⚠️ FFmpeg não configurado: {e}")
        
# edge-tts
try:
    import edge_tts
    TTS_SUPPORT = True
except ImportError:
    TTS_SUPPORT = False

# Whisper
try:
    import whisper
    WHISPER_SUPPORT = True
except ImportError:
    WHISPER_SUPPORT = False

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Studio Pro Creator AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# CSS PROFISSIONAL (Ajustado para evitar erros de DOM)
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
:root{
  --bg:#080b10; --card:#0f1622; --border:rgba(0,229,255,.18);
  --c1:#00e5ff; --c2:#ff4d6d; --c3:#a8ff3e; --gold:#ffd166;
  --txt:#e2e8f0; --dim:#6b7280;
  --glow:0 0 24px rgba(0,229,255,.28);
}
.stApp{background:var(--bg);font-family:'Rajdhani',sans-serif;}
.main{background:var(--bg);padding:0 1rem;}

.hdr{background:linear-gradient(135deg,#09111f,#0d1b2a,#071018);
  border:1px solid var(--c1);border-radius:16px;padding:2rem 2.2rem;
  margin-bottom:1.6rem;position:relative;overflow:hidden;
  box-shadow:var(--glow),inset 0 1px 0 rgba(0,229,255,.08);}
.hdr h1{font-family:'Rajdhani',sans-serif;font-size:2.8rem;font-weight:700;
  margin:0;color:var(--c1);
  text-shadow:0 0 28px rgba(0,229,255,.7),0 0 56px rgba(0,229,255,.2);
  letter-spacing:2px;}
.hdr p{font-family:'JetBrains Mono',monospace;font-size:.82rem;
  color:var(--dim);margin:.4rem 0 0;letter-spacing:.8px;}
.badge{display:inline-block;background:rgba(0,229,255,.09);
  border:1px solid var(--c1);border-radius:20px;padding:.15rem .8rem;
  font-size:.72rem;color:var(--c1);margin:.4rem .3rem 0 0;
  font-family:'JetBrains Mono',monospace;}
.badge-warn{border-color:var(--gold);color:var(--gold);background:rgba(255,209,102,.08);}
.badge-err {border-color:var(--c2);color:var(--c2);background:rgba(255,77,109,.08);}

.card{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:1.2rem;margin:.7rem 0;transition:all .25s;}
.card:hover{border-color:rgba(0,229,255,.4);box-shadow:var(--glow);transform:translateY(-2px);}
.cl{border-left:3px solid var(--c1);}
.cr{border-left:3px solid var(--c2);}
.cg{border-left:3px solid var(--c3);}
.co{border-left:3px solid var(--gold);}

.stitle{font-family:'Rajdhani',sans-serif;font-size:1.4rem;font-weight:700;
  color:var(--c1);letter-spacing:1px;text-transform:uppercase;
  border-bottom:1px solid var(--border);padding-bottom:.4rem;margin-bottom:.9rem;}

.vbox{background:var(--card);border:2px solid var(--c1);border-radius:14px;
  padding:1rem;box-shadow:var(--glow);}
.vbox video {
    max-width: 854px;
    max-height: 480px;
    width: 100%;
    height: auto;
    display: block;
    margin-left: auto;
    margin-right: auto;
}
.vbox-title{font-family:'Rajdhani',sans-serif;font-size:1.1rem;
  color:var(--c1);font-weight:700;margin-bottom:.5rem;letter-spacing:.5px;}

/* Padroniza TODOS os players de vídeo e imagens grandes */
.stVideo video, .stVideo iframe {
    max-width: 854px;
    max-height: 480px;
    width: auto !important;
    height: auto !important;
    display: block;
    margin-left: auto;
    margin-right: auto;
}

/* Centraliza containers de vídeo */
div[data-testid="stVideo"] {
    display: flex;
    justify-content: center;
}

/* Timeline */
.timeline-container {
    background: var(--card);
    border-radius: 12px;
    padding: 1rem;
    margin: 1rem 0;
    border: 1px solid var(--border);
}
.timeline-bar {
    display: flex;
    height: 40px;
    background: #1e2a3a;
    border-radius: 8px;
    overflow: hidden;
    margin: 0.5rem 0;
}
.timeline-segment {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 0.8rem;
    border-right: 1px solid var(--border);
    cursor: pointer;
    transition: filter 0.2s;
}
.timeline-segment:hover {
    filter: brightness(1.2);
}

.stTabs [data-baseweb="tab-list"]{gap:5px;background:var(--card);
  border-radius:12px;padding:.5rem;border:1px solid var(--border);}
.stTabs [data-baseweb="tab"]{background:rgba(255,255,255,.04)!important;
  border-radius:8px!important;border:1px solid rgba(255,255,255,.07)!important;
  padding:.65rem 1.3rem!important;font-family:'Rajdhani',sans-serif!important;
  font-weight:600!important;font-size:.9rem!important;
  color:var(--dim)!important;transition:all .25s!important;}
.stTabs [data-baseweb="tab"]:hover{background:rgba(0,229,255,.08)!important;
  color:var(--c1)!important;}
.stTabs [aria-selected="true"]{
  background:linear-gradient(135deg,rgba(0,229,255,.22),rgba(0,229,255,.07))!important;
  color:var(--c1)!important;border-color:var(--c1)!important;
  box-shadow:0 0 14px rgba(0,229,255,.25)!important;}

.stButton>button{font-family:'Rajdhani',sans-serif!important;
  font-weight:700!important;letter-spacing:.4px!important;
  border-radius:8px!important;transition:all .25s!important;}
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,var(--c1),#0090b8)!important;
  color:#000!important;border:none!important;
  box-shadow:0 4px 14px rgba(0,229,255,.35)!important;}
.stButton>button[kind="primary"]:hover{
  transform:translateY(-2px)!important;
  box-shadow:0 8px 24px rgba(0,229,255,.5)!important;}
.stButton>button[kind="secondary"]{
  background:rgba(255,255,255,.06)!important;
  color:var(--txt)!important;
  border:1px solid var(--border)!important;}
.stButton>button[kind="secondary"]:hover{
  background:rgba(0,229,255,.12)!important;
  border-color:var(--c1)!important;color:var(--c1)!important;}

[data-testid="metric-container"]{background:var(--card);
  border:1px solid var(--border);border-radius:10px;padding:.7rem;}
.stProgress>div>div>div{
  background:linear-gradient(90deg,var(--c1),var(--c3))!important;}
[data-testid="stSidebar"]{background:#0a0f1a!important;
  border-right:1px solid var(--border);}
.stTextInput>div>div>input,.stTextArea>div>div>textarea{
  background:var(--card)!important;border:1px solid var(--border)!important;
  color:var(--txt)!important;border-radius:8px!important;
  font-family:'JetBrains Mono',monospace!important;}
::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:linear-gradient(var(--c1),var(--c2));
  border-radius:10px;}
[data-testid="stFileUploadDropzone"]{background:var(--card)!important;
  border:1.5px dashed var(--border)!important;border-radius:10px!important;}
[data-testid="stFileUploadDropzone"]:hover{border-color:var(--c1)!important;}
.streamlit-expanderHeader{background:var(--card)!important;
  border-radius:8px!important;
  font-family:'Rajdhani',sans-serif!important;font-weight:600!important;}
</style>
""", unsafe_allow_html=True)
# ==============================================================================
# CONSTANTES E BANCOS DE DADOS
# ==============================================================================
PHI = 1.618
MAX_PIX = 5000 * 5000

FILTER_DB: Dict[str, Dict] = {
    "Vintage":       {"icon":"🟤","desc":"Sépia + vinheta + granulação",
                      "params":{"intensidade":(0,100,70),"vinheta":(0,100,40),"granulacao":(0,50,10)}},
    "Azulado":       {"icon":"🔵","desc":"Tom frio cinematográfico",
                      "params":{"intensidade":(0,100,50),"brilho":(-20,20,0)}},
    "Esverdeado":    {"icon":"🟢","desc":"Mood Matrix / natureza",
                      "params":{"intensidade":(0,100,50),"contraste":(0.5,1.5,1.1)}},
    "Futurístico":   {"icon":"👾","desc":"Glow neon cyberpunk",
                      "params":{"glow":(0,100,30),"neon":(0,100,20),"scanlines":(0,50,0)}},
    "Realça Cores":  {"icon":"🌈","desc":"Saturação vibrante",
                      "params":{"intensidade":(0.5,3.0,1.5)}},
    "P&B":           {"icon":"⚫","desc":"Monocromático profissional",
                      "params":{"contraste":(0.5,2.0,1.2),"textura":(0,30,0)}},
    "Infravermelho": {"icon":"📡","desc":"Fotografia IV falsa",
                      "params":{"intensidade":(0,100,50)}},
    "Glitch":        {"icon":"📺","desc":"Distorção digital",
                      "params":{"intensidade":(1,20,5)}},
    "Vaporwave":     {"icon":"🌌","desc":"Pastel retrô 80s",
                      "params":{"intensidade":(0,100,80)}},
    "HDR":           {"icon":"✨","desc":"Alto alcance dinâmico",
                      "params":{"intensidade":(0,100,60)}},
    "Cinemático":    {"icon":"🎞️","desc":"Color grade cinematográfico",
                      "params":{"intensidade":(0,100,60),"contraste":(0.5,1.5,1.1)}},
    "Quente":        {"icon":"🔶","desc":"Tom quente aconchegante",
                      "params":{"intensidade":(0,100,60)}},
    "Frio":          {"icon":"🔷","desc":"Tom frio invernal",
                      "params":{"intensidade":(0,100,60)}},
}

FRAME_DB: Dict[str, Dict] = {
    "Nenhuma":     {"icon":"❌","desc":"Sem moldura"},
    "Neon":        {"icon":"💡","desc":"Brilho neon pulsante",  "cor":"#FF00FF","min":3, "max":30},
    "Janela":      {"icon":"🪟","desc":"Divisórias de janela",  "cor":"#FFFFFF","min":5, "max":50},
    "Câmera":      {"icon":"📷","desc":"Polaroid / DSLR",       "cor":"#C0C0C0","min":10,"max":80},
    "Smartphone":  {"icon":"📱","desc":"iPhone / Android",      "cor":"#000000","min":20,"max":120},
    "Portal":      {"icon":"🌀","desc":"Portal sci-fi",          "cor":"#00FFFF","min":10,"max":150},
    "Lupa":        {"icon":"🔍","desc":"Borda circular",         "cor":"#000000","min":15,"max":100},
    "Cinemascope": {"icon":"🎬","desc":"Barras cinema 2.39:1",   "cor":"#000000","min":5, "max":20},
    "Dupla":       {"icon":"🖼️","desc":"Borda dupla elegante",   "cor":"#DAA520","min":3, "max":15},
    "Glitch":      {"icon":"⚡","desc":"Moldura glitch digital",  "cor":"#00FF00","min":5, "max":20},
}

ANIMATION_DB: Dict[str, Dict] = {
    "Girar":       {"icon":"🔄","desc":"Rotação 360° contínua"},
    "Zoom":        {"icon":"🔍","desc":"Zoom in/out dinâmico"},
    "Deslizar":    {"icon":"↔️","desc":"Transição lateral"},
    "Piscar":      {"icon":"✨","desc":"Fade strobe"},
    "Pixelar":     {"icon":"🧊","desc":"Pixelização criativa"},
    "Glitch":      {"icon":"📺","desc":"Distorção digital"},
    "Pulsar":      {"icon":"💫","desc":"Pulsação suave"},
    "Balançar":    {"icon":"〰️","desc":"Oscilação horizontal"},
}

VOICE_PROFILES: Dict[str, Dict] = {
    "masculina_padrao":  {"name":"Antônio (Neural)","code":"pt-BR-AntonioNeural",  "speed":1.0},
    "feminina_suave":    {"name":"Francisca (Neural)","code":"pt-BR-FranciscaNeural","speed":0.9},
    "masculina_jovem":   {"name":"Julio (Neural)",   "code":"pt-BR-JulioNeural",   "speed":1.1},
    "feminina_calma":    {"name":"Manuela (Neural)",  "code":"pt-BR-ManuelaNeural", "speed":0.9},
    "narrador":          {"name":"Fábio (Notícias)",  "code":"pt-BR-FabioNeural",   "speed":1.0},
}

PERFIS_MUSICAIS: Dict[str, Dict] = {
    "MOTIVACIONAL":{"bpm":125,"emocao":"inspiração","cores":["#1E90FF","#FF8C00"]},
    "FELIZ":       {"bpm":130,"emocao":"alegria",   "cores":["#FFD700","#FF6B35"]},
    "TREINO":      {"bpm":150,"emocao":"força",     "cores":["#FF0000","#000000"]},
    "FILOSOFIA":   {"bpm":80, "emocao":"reflexão",  "cores":["#000080","#87CEEB"]},
    "FINANCEIRO":  {"bpm":120,"emocao":"confiança", "cores":["#006400","#D4AF37"]},
    "RELIGIOSO":   {"bpm":90, "emocao":"devoção",   "cores":["#8B0000","#DAA520"]},
}

THEME_KW = {
    "educação":      ["aprender","ensinar","escola","curso","conhecimento","aula"],
    "tecnologia":    ["software","app","código","digital","ia","algoritmo","sistema"],
    "marketing":     ["venda","campanha","cliente","conversão","roi","funil"],
    "motivacional":  ["superar","conquista","força","vitória","inspirar","sucesso"],
    "negócios":      ["empresa","negócio","lucro","investimento","mercado","startup"],
    "saúde":         ["médico","exercício","nutrição","bem-estar","fitness","treino"],
    "entretenimento":["filme","música","jogo","show","diversão","conteúdo"],
}

# ==============================================================================
# INICIALIZAÇÃO DO ESTADO DA SESSÃO
# ==============================================================================
def init_session_state():
    defaults = {
        "base_image": None,
        "video_clip": None,
        "video_path": None,
        "video_frame": None,
        "processed_image": None,
        "screenshot_data": None,
        "uploaded_file_id": None,
        "project_name": f"Projeto_{datetime.now().strftime('%Y%m%d_%H%M')}",
        "working_dir": tempfile.mkdtemp(prefix="studio_pro_"),
        "transcribed_text": "",
        "video_analysis": None,
        "video_analysis_complete": False,
        "enhanced_prompts": {},
        "tts_text": "",
        "_gif_data": None,
        "_preview_video": None,
        "_export_video": None,
        "_current_frame_sec": 0.0,
        "config": {
            "moldura": {"tipo": "Nenhuma"},
            "filtros": {},
            "animacao": {},
            "texto": "",
            "fonte": {"tamanho": 36, "cor": "#FFFFFF", "tipo": "Padrão"},
            "posicao": {"horizontal": "Centro", "vertical": "Base"},
            "contorno": {"ativo": False, "cor": "#000000", "espessura": 2},
        },
        "audio_path": None,
        "audio_info": {},
        "video_parts": [],
        "is_partitioned": False,
        "conversation_segments": [],
        "narrative_template": None,
        "narrative_acts": [],
        "effect_segments": [],
        "text_animation_segments": [],  # NOVO
        "tutorial_step": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ==============================================================================
# FUNÇÕES UTILITÁRIAS DE IMAGEM
# ==============================================================================
def resize_safe(img: Image.Image) -> Image.Image:
    if img.width * img.height > MAX_PIX:
        scale = (MAX_PIX / (img.width * img.height)) ** 0.5
        return img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
    return img

def img_to_bytes(img: Image.Image, fmt="PNG", quality=93) -> bytes:
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.convert("RGB").save(buf, format=fmt, quality=quality)
    else:
        img.save(buf, format=fmt)
    return buf.getvalue()

def apply_filters(image: Image.Image, cfg: Dict) -> Image.Image:
    """
    Aplica todos os filtros selecionados à imagem.
    Retorna SEMPRE uma imagem RGB.
    """
    # Garante que a entrada seja RGB
    img = image.convert("RGB")
    
    # ---- P&B ----
    if "P&B" in cfg:
        p = cfg["P&B"]
        img = ImageOps.grayscale(img).convert("RGB")
        img = ImageEnhance.Contrast(img).enhance(p.get("contraste", 1.2))
        if p.get("textura", 0) > 0:
            arr = np.array(img, dtype=np.float32)
            arr = np.clip(arr + np.random.normal(0, p["textura"] * 7, arr.shape), 0, 255)
            img = Image.fromarray(arr.astype(np.uint8))

    # ---- Vintage ----
    if "Vintage" in cfg:
        p = cfg["Vintage"]
        arr = np.array(img, dtype=np.float32) / 255.0
        fac = p.get("intensidade", 70) / 100.0
        sm = np.array([[.393, .769, .189],
                       [.349, .686, .168],
                       [.272, .534, .131]])
        sepia = np.dot(arr, sm.T)
        arr = np.clip(arr * (1 - fac) + sepia * fac, 0, 1)
        vig = p.get("vinheta", 40)
        if vig > 0:
            h, w = arr.shape[:2]
            X, Y = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
            mask = np.clip(1 - np.sqrt(X**2 + Y**2) * (vig / 100 * 1.5), 0, 1)[:, :, None]
            arr *= mask
        gr = p.get("granulacao", 10)
        if gr > 0:
            noise = np.random.randint(-gr, gr, arr.shape[:2] + (3,), dtype=np.int16)
            arr = np.clip((arr * 255 + noise), 0, 255) / 255.0
        img = Image.fromarray((arr * 255).astype(np.uint8))

    # ---- Azulado ----
    if "Azulado" in cfg:
        p = cfg["Azulado"]
        tint = Image.new("RGB", img.size, (135, 206, 250))
        img = Image.blend(img, tint, p.get("intensidade", 50) / 200)
        img = ImageEnhance.Brightness(img).enhance(1 + p.get("brilho", 0) / 100)

    # ---- Esverdeado ----
    if "Esverdeado" in cfg:
        p = cfg["Esverdeado"]
        tint = Image.new("RGB", img.size, (144, 238, 144))
        img = Image.blend(img, tint, p.get("intensidade", 50) / 200)
        img = ImageEnhance.Contrast(img).enhance(p.get("contraste", 1.1))

    # ---- Futurístico (CORRIGIDO) ----
    if "Futurístico" in cfg:
        p = cfg["Futurístico"]
        arr = np.array(img, dtype=np.float32)
        gv = p.get("glow", 30)
        if gv > 0:
            bl = cv2.GaussianBlur(arr, (0, 0), gv / 10)
            arr = cv2.addWeighted(arr, 1, bl, gv / 100, 0)
        nv = p.get("neon", 20)
        if nv > 0:
            # CORREÇÃO: Laplacian em imagem colorida sem conversões desnecessárias
            edges = cv2.Laplacian(arr, cv2.CV_32F, ksize=3)
            # Amplifica bordas e aplica cor neon (magenta)
            colored = np.abs(edges) * np.array([1, 0, 1], dtype=np.float32)
            arr = cv2.addWeighted(arr, 1, colored, nv / 100, 0)
        sv = p.get("scanlines", 0)
        if sv > 0:
            for y in range(0, int(arr.shape[0]), 2):
                arr[y:y+1, :] *= (1 - sv / 100)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # ---- Realça Cores ----
    if "Realça Cores" in cfg:
        img = ImageEnhance.Color(img).enhance(cfg["Realça Cores"].get("intensidade", 1.5))

    # ---- Infravermelho ----
    if "Infravermelho" in cfg:
        arr = np.array(img, dtype=np.float32)
        fac = 1 + cfg["Infravermelho"].get("intensidade", 50) / 100
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        arr[:, :, 0] = np.clip(r * fac + g * 0.2, 0, 255)
        arr[:, :, 1] = np.clip(g * 0.5, 0, 255)
        arr[:, :, 2] = np.clip(b * 0.3, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8))

    # ---- Glitch ----
    if "Glitch" in cfg:
        intens = int(cfg["Glitch"].get("intensidade", 5))
        arr = np.array(img)
        for _ in range(intens):
            y = random.randint(0, img.height - 1)
            shift = random.randint(-intens * 3, intens * 3)
            if shift:
                arr[y, :] = np.roll(arr[y, :], shift, axis=0)
        img = Image.fromarray(arr)

    # ---- Vaporwave ----
    if "Vaporwave" in cfg:
        arr = np.array(img, dtype=np.float32)
        fac = cfg["Vaporwave"].get("intensidade", 80) / 100
        arr[:, :, 0] = np.clip(arr[:, :, 0] * (1 + fac * 0.3), 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * (1 + fac * 0.4), 0, 255)
        img = Image.fromarray(arr.astype(np.uint8))
        img = ImageEnhance.Color(img).enhance(1 + fac * 0.5)

    # ---- HDR ----
    if "HDR" in cfg:
        fac = cfg["HDR"].get("intensidade", 60) / 100
        img = ImageEnhance.Contrast(img).enhance(1 + fac * 0.5)
        img = ImageEnhance.Color(img).enhance(1 + fac * 0.4)
        img = ImageEnhance.Sharpness(img).enhance(1 + fac * 0.3)

    # ---- Cinemático ----
    if "Cinemático" in cfg:
        p = cfg["Cinemático"]
        fac = p.get("intensidade", 60) / 100
        arr = np.array(img, dtype=np.float32)
        arr[:, :, 0] = np.clip(arr[:, :, 0] + fac * 30, 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] - fac * 20, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8))
        img = ImageEnhance.Contrast(img).enhance(p.get("contraste", 1.1))

    # ---- Quente ----
    if "Quente" in cfg:
        fac = cfg["Quente"].get("intensidade", 60) / 100
        arr = np.array(img, dtype=np.float32)
        arr[:, :, 0] = np.clip(arr[:, :, 0] * (1 + fac * 0.3), 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * (1 - fac * 0.2), 0, 255)
        img = Image.fromarray(arr.astype(np.uint8))

    # ---- Frio ----
    if "Frio" in cfg:
        fac = cfg["Frio"].get("intensidade", 60) / 100
        arr = np.array(img, dtype=np.float32)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * (1 + fac * 0.35), 0, 255)
        arr[:, :, 0] = np.clip(arr[:, :, 0] * (1 - fac * 0.2), 0, 255)
        img = Image.fromarray(arr.astype(np.uint8))

    # Garante que a saída seja RGB (remove canal alpha se existir)
    return img.convert("RGB")

def apply_frame(image: Image.Image, cfg: Dict) -> Image.Image:
    """
    Aplica moldura decorativa à imagem.
    Retorna SEMPRE uma imagem RGB.
    """
    ft = cfg.get("tipo", "Nenhuma")
    if ft == "Nenhuma":
        return image.convert("RGB")

    # Trabalha em RGBA para permitir transparências
    img = image.convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    col = cfg.get("cor", "#FFFFFF")
    thickness = max(1, cfg.get("espessura", 10))

    if ft == "Neon":
        for i in range(thickness, 0, -1):
            alpha = int(255 * (i / thickness) ** 0.5)
            neon_color = (*ImageColor.getrgb(col), alpha)
            draw.rectangle([(i, i), (w - i, h - i)], outline=neon_color, width=1)

    elif ft == "Janela":
        draw.rectangle([(0, 0), (w - 1, h - 1)], outline=col, width=thickness)
        draw.line([(w // 2, 0), (w // 2, h)], fill=col, width=max(1, thickness // 2))
        draw.line([(0, h // 2), (w, h // 2)], fill=col, width=max(1, thickness // 2))

    elif ft == "Câmera":
        draw.rectangle([(thickness//2, thickness//2), (w - thickness//2, h - thickness//2)],
                       outline=col, width=thickness)
        draw.rectangle([(0, h - thickness * 3), (w, h)], fill=col)

    elif ft == "Smartphone":
        r = min(w, h) // 8
        draw.rounded_rectangle([(thickness//2, thickness//2), (w - thickness//2, h - thickness//2)],
                               radius=r, outline=col, width=thickness)
        nw, nh = w // 5, thickness * 2
        draw.rectangle([(w//2 - nw//2, 0), (w//2 + nw//2, nh)], fill=col)

    elif ft == "Portal":
        cx, cy = w // 2, h // 2
        rad = min(w, h) // 2 - thickness
        for i in range(thickness, 0, -1):
            alpha = int(255 * (i / thickness) ** 0.5)
            portal_color = (*ImageColor.getrgb(col), alpha)
            draw.ellipse([(cx - rad - i, cy - rad - i),
                          (cx + rad + i, cy + rad + i)],
                         outline=portal_color, width=1)

    elif ft == "Lupa":
        cx, cy = w // 2, h // 2
        rad = min(w, h) // 2 - thickness
        draw.ellipse([(cx - rad, cy - rad), (cx + rad, cy + rad)], outline=col, width=thickness)
        handle_len = h // 3
        draw.rectangle([(cx - thickness, cy + rad), (cx + thickness, cy + rad + handle_len)], fill=col)

    elif ft == "Cinemascope":
        bar_h = int(h * 0.108)
        draw.rectangle([(0, 0), (w, bar_h)], fill=col)
        draw.rectangle([(0, h - bar_h), (w, h)], fill=col)

    elif ft == "Dupla":
        draw.rectangle([(0, 0), (w - 1, h - 1)], outline=col, width=thickness)
        inner = thickness * 3
        draw.rectangle([(inner, inner), (w - inner, h - inner)],
                       outline=col, width=max(1, thickness // 2))

    elif ft == "Glitch":
        for i in range(0, thickness * 2, 2):
            offset = random.randint(-4, 4)
            alpha = int(200 * (1 - i / (thickness * 2 + 1)))
            glitch_color = (*ImageColor.getrgb(col), alpha)
            draw.rectangle([(i + offset, i), (w - i + offset, h - i)],
                           outline=glitch_color, width=1)

    # Combina a moldura com a imagem original
    result = Image.alpha_composite(img, overlay)
    # Converte para RGB (remove transparência) para compatibilidade com vídeo
    return result.convert("RGB")

def apply_text(image: Image.Image, cfg: Dict) -> Image.Image:
    texto = cfg.get("texto","")
    if not texto: return image
    img = image.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except:
        font = None
    cor = cfg.get("fonte",{}).get("cor","#FFFFFF")
    pos = cfg.get("posicao",{})
    try:
        bbox = draw.textbbox((0,0), texto, font=font)
        tw, th_ = bbox[2]-bbox[0], bbox[3]-bbox[1]
    except:
        tw, th_ = len(texto)*8, 16
    hmap = {"Esquerda":20,"Centro":(img.width-tw)//2,"Direita":img.width-tw-20}
    vmap = {"Topo":20,"Meio":(img.height-th_)//2,"Base":img.height-th_-20}
    x = hmap.get(pos.get("horizontal","Centro"), (img.width-tw)//2)
    y = vmap.get(pos.get("vertical","Base"), img.height-th_-20)
    ctr = cfg.get("contorno",{})
    if ctr.get("ativo"):
        cw = ctr.get("espessura",2)
        cc = ctr.get("cor","#000000")
        for dx in range(-cw, cw+1):
            for dy in range(-cw, cw+1):
                if dx or dy:
                    draw.text((x+dx,y+dy), texto, fill=cc, font=font)
    draw.text((x,y), texto, fill=cor, font=font)
    return img

# ==============================================================================
# VÍDEO: CARREGAMENTO E OPERAÇÕES
# ==============================================================================
def load_video(uploaded_file) -> Tuple[Optional[Any], Optional[str]]:
    if not VIDEO_SUPPORT: return None, None
    try:
        suffix = "." + uploaded_file.name.split(".")[-1].lower()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix,
                                          dir=st.session_state.working_dir)
        tmp.write(uploaded_file.read())
        tmp.close()
        clip = VideoFileClip(tmp.name)
        if clip.duration > 120:  # Limite de 2 minutos para não travar
            clip = clip.subclip(0, 120)
        return clip, tmp.name
    except Exception as e:
        st.error(f"Erro ao carregar vídeo: {e}")
        return None, None

def extract_frame(clip, t: float) -> Optional[Image.Image]:
    try:
        t = max(0.0, min(t, clip.duration - 0.01))
        frame = clip.get_frame(t)
        return Image.fromarray(frame.astype(np.uint8))
    except Exception:
        return None

def clip_subclip(clip, start: float, end: float):
    try:
        return clip.subclipped(start, end)
    except AttributeError:
        return clip.subclip(start, end)

def clip_fl_image(clip, fn):
    try:
        return clip.image_transform(fn)
    except AttributeError:
        return clip.fl_image(fn)

def export_clip(clip, fps=24) -> Optional[bytes]:
    if not VIDEO_SUPPORT or clip is None: return None
    try:
        out = os.path.join(st.session_state.working_dir, f"exp_{uuid.uuid4().hex[:8]}.mp4")
        # Parâmetros para alta qualidade
        clip.write_videofile(
            out,
            codec="libx264",
            fps=fps,
            bitrate="8000k",          # Taxa de bits alta (ajuste conforme necessário)
            preset="medium",          # Equilíbrio entre qualidade e velocidade
            audio_codec="aac",
            audio_bitrate="192k",
            logger=None,
            temp_audiofile=None
        )
        with open(out, "rb") as f:
            data = f.read()
        try: os.unlink(out)
        except: pass
        return data
    except Exception as e:
        st.error(f"Erro ao exportar: {e}")
        return None
    
def apply_animation_to_frame(img_array, anim_name, params, progress):
    """Aplica um efeito de animação a um frame (numpy array) baseado no progresso (0 a 1)."""
    img = Image.fromarray(img_array.astype(np.uint8)).convert("RGBA")
    orig_size = img.size

    if anim_name == "Girar":
        angle = 360 * progress
        img = img.rotate(angle, resample=Image.BILINEAR, expand=False)
    elif anim_name == "Zoom":
        scale = 1 + 0.35 * math.sin(progress * math.pi * 2)
        nw, nh = int(orig_size[0]*scale), int(orig_size[1]*scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        dx, dy = (nw - orig_size[0])//2, (nh - orig_size[1])//2
        img = img.crop((dx, dy, dx + orig_size[0], dy + orig_size[1]))
    elif anim_name == "Deslizar":
        offset = int(orig_size[0] * 0.15 * math.sin(progress * math.pi * 2))
        tmp = Image.new("RGBA", orig_size, (0,0,0,0))
        tmp.paste(img, (offset, 0))
        img = tmp
    elif anim_name == "Piscar":
        alpha = int(255 * abs(math.sin(progress * math.pi * 3)))
        ov = Image.new("RGBA", img.size, (0,0,0,255-alpha))
        img = Image.alpha_composite(img, ov)
    elif anim_name == "Pixelar":
        px = max(1, int(20 * abs(math.sin(progress * math.pi))))
        if px > 1:
            small = img.resize((orig_size[0]//px, orig_size[1]//px), Image.NEAREST)
            img = small.resize(orig_size, Image.NEAREST)
    elif anim_name == "Glitch":
        arr = np.array(img)
        for _ in range(random.randint(2,5)):
            y = random.randint(0, img.height-1)
            shift = random.randint(-20,20)
            if shift: arr[y,:] = np.roll(arr[y,:], shift, axis=0)
        img = Image.fromarray(arr)
    elif anim_name == "Pulsar":
        scale = 1 + 0.08 * math.sin(progress * math.pi * 4)
        nw, nh = int(orig_size[0]*scale), int(orig_size[1]*scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        dx, dy = (nw - orig_size[0])//2, (nh - orig_size[1])//2
        img = img.crop((dx, dy, dx + orig_size[0], dy + orig_size[1]))
    elif anim_name == "Balançar":
        angle = 8 * math.sin(progress * math.pi * 4)
        img = img.rotate(angle, resample=Image.BILINEAR, center=(orig_size[0]//2, orig_size[1]))

    # Garantir que o resultado final tenha o tamanho original e seja RGB
    img = img.resize(orig_size, Image.LANCZOS).convert("RGB")
    return np.array(img)

# ==============================================================================
# NOVA FUNÇÃO: Aplicar efeitos segmentados ao clipe
# ==============================================================================
def apply_effects_to_clip(clip, segments):
    """
    Aplica efeitos segmentados (filtros, molduras, animações) a um clipe.
    Compatível com MoviePy 1.x e 2.x.
    Segmentos sobrepostos são compostos no mesmo trecho.
    """
    if not segments:
        return clip

    # Ordena por início
    segments = sorted(segments, key=lambda x: x["start"])
    
    # Agrupa segmentos por intervalo contínuo de tempo
    grouped_segments = []
    current_group = []
    current_end = 0.0
    
    for seg in segments:
        s, e = seg["start"], seg["end"]
        # Se este segmento começa antes do fim do grupo atual, eles se sobrepõem
        if s < current_end:
            current_group.append(seg)
            current_end = max(current_end, e)
        else:
            if current_group:
                grouped_segments.append((current_group, current_end))
            current_group = [seg]
            current_end = e
    if current_group:
        grouped_segments.append((current_group, current_end))

    processed_parts = []
    last_t = 0.0

    for group, group_end in grouped_segments:
        # Determina o início do grupo (primeiro segmento do grupo)
        group_start = min(seg["start"] for seg in group)
        
        # Adiciona parte sem efeitos antes do grupo
        if group_start > last_t:
            processed_parts.append(clip_subclip(clip, last_t, group_start))

        # Subclipe do trecho do grupo (do início ao fim do grupo)
        sub = clip_subclip(clip, group_start, group_end)

        # Aplica todos os efeitos do grupo **em sequência** sobre o mesmo subclip
        for seg in group:
            if seg["type"] == "Filtro":
                filtros = seg.get("params", {})
                if filtros:
                    sub = clip_fl_image(
                        sub,
                        lambda f, filtros=filtros: np.array(apply_filters(Image.fromarray(f), filtros))
                    )
            elif seg["type"] == "Moldura":
                moldura = seg.get("params", {})
                if moldura and moldura.get("tipo") != "Nenhuma":
                    sub = clip_fl_image(
                        sub,
                        lambda f, moldura=moldura: np.array(apply_frame(Image.fromarray(f), moldura))
                    )
            elif seg["type"] == "Animação":
                anim_params = seg.get("params", {})
                anim_name = anim_params.get("tipo")
                if anim_name and anim_name in ANIMATION_DB:
                    # Função que processa cada frame da animação com progresso
                    def make_frame_animation(get_frame, t, s=seg["start"], e=seg["end"],
                                             anim_name=anim_name, anim_params=anim_params):
                        frame = get_frame(t)
                        progress = (t - s) / (e - s) if e > s else 0.0
                        return apply_animation_to_frame(frame, anim_name, anim_params, progress)

                    try:
                        sub = sub.transform(make_frame_animation)
                    except AttributeError:
                        sub = sub.fl(make_frame_animation, keep_duration=True)

        processed_parts.append(sub)
        last_t = group_end

    # Adiciona o restante do vídeo após o último grupo
    if last_t < clip.duration:
        processed_parts.append(clip_subclip(clip, last_t, clip.duration))

    # Concatena todas as partes
    if processed_parts:
        return concatenate_videoclips(processed_parts)
    return clip

# ==============================================================================
# GIF ANIMADO
# ==============================================================================
def make_gif(image: Image.Image, anim_cfg: Dict, duration: float = 2.0) -> bytes:
    n = max(12, min(40, int(duration * 15)))
    frames = []
    orig_size = image.size
    for i in range(n):
        p = i / (n-1) if n > 1 else 0
        frame = image.copy().convert("RGBA")
        if "Girar" in anim_cfg:
            angle = 360 * p
            frame = frame.rotate(angle, resample=Image.BILINEAR, expand=False)
        if "Zoom" in anim_cfg:
            scale = 1 + 0.35 * math.sin(p * math.pi * 2)
            nw, nh = int(orig_size[0]*scale), int(orig_size[1]*scale)
            z = frame.resize((nw, nh), Image.LANCZOS)
            dx, dy = (nw-orig_size[0])//2, (nh-orig_size[1])//2
            frame = z.crop((dx, dy, dx+orig_size[0], dy+orig_size[1]))
        if "Pulsar" in anim_cfg:
            scale = 1 + 0.08 * math.sin(p * math.pi * 4)
            nw, nh = int(orig_size[0]*scale), int(orig_size[1]*scale)
            z = frame.resize((nw, nh), Image.LANCZOS)
            dx, dy = (nw-orig_size[0])//2, (nh-orig_size[1])//2
            frame = z.crop((dx, dy, dx+orig_size[0], dy+orig_size[1]))
            frame = frame.resize(orig_size, Image.LANCZOS)
        if "Deslizar" in anim_cfg:
            offset = int(orig_size[0] * 0.15 * math.sin(p * math.pi * 2))
            tmp = Image.new("RGBA", orig_size, (0,0,0,0))
            tmp.paste(frame, (offset, 0))
            frame = tmp
        if "Balançar" in anim_cfg:
            angle = 8 * math.sin(p * math.pi * 4)
            frame = frame.rotate(angle, resample=Image.BILINEAR, center=(orig_size[0]//2, orig_size[1]))
        if "Piscar" in anim_cfg:
            alpha = int(255 * abs(math.sin(p * math.pi * 3)))
            ov = Image.new("RGBA", frame.size, (0,0,0,255-alpha))
            frame = Image.alpha_composite(frame, ov)
        if "Pixelar" in anim_cfg:
            px = max(1, int(20 * abs(math.sin(p * math.pi))))
            if px > 1:
                small = frame.resize((orig_size[0]//px, orig_size[1]//px), Image.NEAREST)
                frame = small.resize(orig_size, Image.NEAREST)
        if "Glitch" in anim_cfg:
            arr = np.array(frame)
            for _ in range(random.randint(2,5)):
                y = random.randint(0, frame.height-1)
                shift = random.randint(-20,20)
                if shift: arr[y,:] = np.roll(arr[y,:], shift, axis=0)
            frame = Image.fromarray(arr)
        if frame.size != orig_size:
            frame = frame.resize(orig_size, Image.LANCZOS)
        frames.append(frame.convert("RGB"))
    buf = io.BytesIO()
    if frames:
        frames[0].save(buf, format="GIF",
                       append_images=frames[1:], save_all=True,
                       duration=int(duration*1000/n), loop=0,
                       optimize=True)
    return buf.getvalue()

# ==============================================================================
# TTS
# ==============================================================================
def tts_generate(text: str, voice_key: str, speed: float = 1.0) -> Tuple[bool, str]:
    if not TTS_SUPPORT:
        return False, "Instale: pip install edge-tts"
    try:
        vp = VOICE_PROFILES.get(voice_key, VOICE_PROFILES["masculina_padrao"])
        rate_pct = int((speed - 1.0) * 100)
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"
        out = os.path.join(st.session_state.working_dir, f"tts_{uuid.uuid4().hex[:8]}.mp3")
        comm = edge_tts.Communicate(text=text[:5000], voice=vp["code"], rate=rate_str)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(comm.save(out))
            loop.close()
        except Exception:
            asyncio.run(comm.save(out))
        return True, out
    except Exception as e:
        return False, str(e)

# ==============================================================================
# ANÁLISE DE CONTEÚDO
# ==============================================================================
def analyze_content(text: str) -> Dict:
    tl = text.lower()
    scores = {}
    for theme, kws in THEME_KW.items():
        sc = sum(tl.count(k) for k in kws)
        if sc > 0: scores[theme] = sc
    sorted_t = sorted(scores.items(), key=lambda x:x[1], reverse=True)
    primary = sorted_t[0][0] if sorted_t else "geral"
    wc = len(text.split())
    eng = min(100, 40 + wc//8 + text.count("?")*5 + text.count("!")*2)
    return {
        "primary": primary, "themes": dict(sorted_t[:4]),
        "word_count": wc, "engagement": eng,
        "reading_min": round(wc/150, 1),
    }

def gen_ai_prompts(theme: str, words: List[str], platform: str, tone: str) -> Dict:
    kw = ", ".join(words[:5]) if words else theme
    return {
        "🎨 Imagem/Visual":   f"Crie imagem {tone.lower()} sobre {kw}. Tema: {theme}. Plataforma: {platform}. Alta qualidade, composição impactante, cores que reflitam o tema.",
        "🔊 Áudio/Narração":  f"Narração {tone.lower()} sobre {kw}. Tema: {theme}. Duração 60s. Plataforma: {platform}. Gancho nos primeiros 5s + call-to-action final.",
        "🎬 Roteiro de Vídeo":f"Roteiro vídeo 60s sobre {kw}. Plataforma {platform}. Tom {tone}.\n0-5s: Hook visual\n5-50s: Desenvolvimento\n50-60s: CTA forte.",
        "📝 Texto/Legenda":   f"Texto {tone.lower()} otimizado para {platform} sobre {kw}. Tema {theme}. Inclua hashtags relevantes e call-to-action.",
        "📊 Storyboard":      f"Storyboard 8 cenas para vídeo sobre {kw}:\nCena 1: Hook (0-5s)\nCena 2-6: Conteúdo (5-50s)\nCena 7-8: CTA (50-60s)\nEstilo: {tone}.",
    }

# ==============================================================================
# INTERFACE: HEADER E SIDEBAR (COM ASSISTENTE)
# ==============================================================================
def render_header():
    def badge(text, kind="ok"):
        cls = "badge-warn" if kind == "warn" else ("badge-err" if kind == "err" else "badge")
        return f'<span class="{cls}">{text}</span>'
    b_vid = badge("🎬 VÍDEO ✅") if VIDEO_SUPPORT else badge("🎬 VÍDEO ❌","err")
    b_tts = badge("🗣️ TTS ✅")   if TTS_SUPPORT  else badge("🗣️ TTS ❌","warn")
    b_wsp = badge("🎧 WHISPER ✅") if WHISPER_SUPPORT else badge("🎧 WHISPER ❌","warn")
    st.markdown(f"""
    <div class="hdr">
      <h1>🎬 STUDIO PRO CREATOR AI v6.0</h1>
      <p>Filtros • Vídeo • GIF • IA • Screenshot • TTS • Montagem • Timeline</p>
      <div>
        {badge("v6.0")} {b_vid} {b_tts} {b_wsp}
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.markdown("### 🗂️ PROJETO")
        st.session_state.project_name = st.text_input(
            "Nome", value=st.session_state.project_name, key="proj_name",
            help="Dê um nome ao seu projeto para organizar as exportações."
        )

        st.markdown("---")
        st.markdown("### 📤 ENVIAR MÍDIA")
        ftypes = ["jpg","jpeg","png","webp"]
        if VIDEO_SUPPORT:
            ftypes += ["mp4","mov","avi","mkv","webm","mpeg4"]

        uploaded = st.file_uploader(
            "🖼️ Imagem ou 🎬 Vídeo",
            type=ftypes,
            key="main_uploader",
            help="Arraste ou clique para enviar. Formatos suportados: imagens (JPG,PNG,WEBP) e vídeos (MP4,MOV,AVI)."
        )

        if uploaded and uploaded.file_id != st.session_state.uploaded_file_id:
            with st.spinner("Carregando..."):
                if uploaded.type.startswith("video/") or \
                   uploaded.name.lower().split(".")[-1] in ["mp4","mov","avi","mkv","webm","mpeg4"]:
                    clip, path = load_video(uploaded)
                    if clip is not None:
                        st.session_state.video_clip = clip
                        st.session_state.video_path = path
                        frame0 = extract_frame(clip, 0.0)
                        if frame0:
                            st.session_state.video_frame = frame0
                            st.session_state.base_image = frame0
                        st.success(f"🎬 Vídeo: {clip.duration:.1f}s")
                    else:
                        st.error("Falha ao carregar vídeo.")
                else:
                    img = Image.open(uploaded)
                    img = resize_safe(img)
                    st.session_state.base_image = img
                    st.session_state.video_clip = None
                    st.session_state.video_frame = None
                    st.success("🖼️ Imagem carregada!")
            st.session_state.uploaded_file_id = uploaded.file_id

        aud_up = st.file_uploader(
            "🔊 Áudio",
            type=["mp3","wav","m4a","ogg"],
            key="aud_uploader",
            help="Envie um arquivo de áudio para usar como trilha sonora ou para transcrição."
        )
        if aud_up:
            ap = os.path.join(st.session_state.working_dir, "audio_in.mp3")
            with open(ap,"wb") as f: f.write(aud_up.read())
            st.session_state["audio_path"] = ap
            st.success("🔊 Áudio carregado!")

        st.markdown("---")
        st.markdown("### 👁️ PREVIEW")
        if st.session_state.video_clip is not None:
            st.markdown(f'<div class="badge">🎬 Vídeo: {st.session_state.video_clip.duration:.1f}s</div>',
                        unsafe_allow_html=True)
            if st.session_state.video_frame:
                st.image(st.session_state.video_frame,
                         caption="Frame atual", use_container_width=True)
        elif st.session_state.base_image:
            st.image(st.session_state.base_image,
                     caption="Imagem carregada", use_container_width=True)
        else:
            st.markdown('<div class="card cl">Nenhuma mídia carregada.</div>',
                        unsafe_allow_html=True)

        # --- ASSISTENTE RÁPIDO ---
        st.markdown("---")
        st.markdown("### 🧭 Assistente Rápido")
        if not st.session_state.get("video_clip") and not st.session_state.get("base_image"):
            st.info("👆 **Primeiro passo:** Envie uma imagem ou vídeo acima.")
        elif st.session_state.get("video_clip"):
            st.success("✅ Vídeo carregado!")
            st.markdown("""
            **Sugestões:**
            - Vá para **🎞️ Editor de Vídeo** para cortar ou aplicar efeitos por tempo.
            - Extraia um **frame** para editar como imagem na aba **🎨 Filtros**.
            """)
        elif st.session_state.get("base_image"):
            st.success("✅ Imagem carregada!")
            st.markdown("""
            **Sugestões:**
            - Use a aba **🎨 Filtros & Molduras** para aplicar efeitos.
            - Crie um **GIF animado** na aba **🎬 Animações**.
            """)

        st.markdown("---")
        st.markdown("### ⚙️ STATUS")
        for name, ok in [
            ("MoviePy (Vídeo)", VIDEO_SUPPORT),
            ("edge-tts (TTS)",  TTS_SUPPORT),
            ("Whisper (STT)",   WHISPER_SUPPORT),
            ("OpenCV",          True),
            ("Pillow",          True),
            ("NumPy",           True),
        ]:
            st.caption(("🟢 " if ok else "🔴 ") + name)

        if shutil.which("ffmpeg"):
            st.caption("🟢 FFmpeg")
        else:
            st.caption("🟡 FFmpeg (não no PATH)")

        st.markdown("---")
        if st.button("🔄 Reset Total", key="reset_btn", help="Apaga todos os dados do projeto e reinicia."):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.caption(f"Studio Pro v6.0 | φ={PHI}")

# ==============================================================================
# HELPER: OBTER IMAGEM DE TRABALHO
# ==============================================================================
def get_work_image() -> Optional[Image.Image]:
    return (st.session_state.processed_image
            or st.session_state.video_frame
            or st.session_state.base_image
            or st.session_state.screenshot_data)

def get_source_image() -> Optional[Image.Image]:
    return (st.session_state.video_frame
            or st.session_state.base_image
            or st.session_state.screenshot_data)

def tab_ajuda():
    st.markdown('<div class="stitle">📖 Ajuda & Tutoriais</div>', unsafe_allow_html=True)
    
    with st.expander("🚀 Primeiros Passos", expanded=True):
        st.markdown("""
        ### Bem-vindo ao Studio Pro Creator AI!
        Este é um estúdio completo para edição de imagens, vídeos, GIFs e muito mais, com inteligência artificial integrada.
        
        **Como começar:**
        1. **Carregue uma mídia** na barra lateral (imagem ou vídeo).
        2. **Escolha uma das abas** para editar:
           - 🎞️ **Editor de Vídeo**: corte, extraia frames e aplique efeitos em trechos específicos (timeline).
           - 🎨 **Filtros & Molduras**: adicione filtros de cor, molduras e texto sobre imagens/frames.
           - 🎬 **Animações & GIF**: crie GIFs animados a partir de uma imagem.
           - 📸 **Screenshot**: capture telas ou use a câmera.
           - 🤖 **IA & Áudio**: converta texto em fala (TTS), transcreva áudios e gere prompts para IAs.
           - 🎼 **Montagem**: organize imagens com áudio e gere roteiros sincronizados com legenda proporcional.
           - 📦 **Exportar**: baixe seus arquivos finais.
        3. **Exporte** o resultado quando estiver satisfeito.
        """)

    with st.expander("🎞️ Como editar um vídeo com a Timeline", expanded=False):
        st.markdown("""
        ### Edição segmentada por tempo (Timeline)
        A timeline permite aplicar diferentes efeitos em momentos específicos do vídeo.
        
        **Passo a passo:**
        1. Carregue um vídeo na barra lateral.
        2. Vá para a aba **🎞️ Editor de Vídeo**.
        3. Na seção **⏱️ EFEITOS POR TEMPO (TIMELINE)**:
           - Clique em **➕ Adicionar segmento de efeito**.
           - Defina o **Início** e **Fim** do trecho (em segundos).
           - Escolha o **Tipo de Efeito** (Filtro, Moldura ou Animação).
           - Configure os parâmetros do efeito (ex: selecione o filtro Vintage e ajuste a intensidade).
           - Clique em **Adicionar Segmento**.
        4. Repita para outros trechos. Você verá uma barra colorida representando cada segmento.
        5. Opcionalmente, use os controles de **Corte & Efeitos Globais** para aplicar um corte final ou filtros que afetam o vídeo inteiro.
        6. Clique em **💾 Exportar com Timeline + Filtros Globais** para gerar o vídeo final.
        
        **Dica:** Você pode remover um segmento clicando no **✖️** ao lado dele.
        """)

    with st.expander("🎨 Aplicando Filtros e Molduras em Imagens", expanded=False):
        st.markdown("""
        ### Edição de imagens e frames de vídeo
        - Após carregar uma imagem ou extrair um frame do vídeo, vá para **🎨 Filtros & Molduras**.
        - No painel esquerdo, expanda **🌈 FILTROS DE COR** e selecione um ou mais filtros. Ajuste os parâmetros conforme desejar.
        - Em **🖼️ MOLDURA**, escolha um estilo e configure cor/espessura.
        - Em **✍️ TEXTO NA IMAGEM**, adicione um texto personalizado com fonte, cor e contorno.
        - A **pré-visualização ao vivo** mostra as alterações em tempo real.
        - Ao final, use os botões **💾 PNG**, **💾 JPG** ou **💾 WEBP** para baixar a imagem editada.
        """)

    with st.expander("🤖 Usando a IA (TTS e Transcrição)", expanded=False):
        st.markdown("""
        ### Texto para Fala (TTS)
        1. Na aba **🤖 IA & Áudio**, sub-aba **🗣️ Texto → Áudio**.
        2. Digite ou cole o texto que deseja narrar.
        3. Selecione uma voz neural em português.
        4. Ajuste a velocidade e clique em **🔊 GERAR NARRAÇÃO**.
        5. Ouça o resultado e faça o download do MP3.
        
        ### Transcrição com Whisper
        1. Carregue um arquivo de áudio na barra lateral.
        2. Na sub-aba **🎧 Transcrição**, clique em **📝 TRANSCREVER**.
        3. Aguarde o processamento (pode levar alguns segundos). O texto aparecerá editável.
        4. Você pode baixar o TXT ou usá-lo para gerar prompts de IA na sub-aba **📊 Análise & Prompts**.
        """)

    with st.expander("🎬 Criando GIFs Animados", expanded=False):
        st.markdown("""
        ### Como criar um GIF a partir de uma imagem
        1. Tenha uma imagem carregada ou um frame extraído do vídeo.
        2. Vá para **🎬 Animações & GIF**.
        3. Selecione um ou mais efeitos de animação (Girar, Zoom, Glitch, etc.).
        4. Ajuste a duração e FPS do GIF.
        5. Clique em **🎬 GERAR GIF**.
        6. Visualize o resultado e faça o download.
        """)

    with st.expander("📸 Captura de Tela (Screenshot)", expanded=False):
        st.markdown("""
        - **Upload Manual**: envie um print já salvo no computador.
        - **URL via API**: use o ScreenshotMachine (necessário API key gratuita) para capturar páginas web.
        - **Câmera/Webcam**: tire uma foto diretamente pelo navegador.
        
        Após capturar, você pode aplicar uma edição rápida (brilho, contraste, filtro) e depois usar a imagem como base para as outras abas.
        """)

    # =========================================================================
    # SEÇÃO DETALHADA DA ABA MONTAGEM (NOVO CONTEÚDO)
    # =========================================================================
    with st.expander("🎼 Montagem Sincronizada com Legenda Proporcional", expanded=False):
        st.markdown("""
        ### 📌 O que faz a aba **🎼 Montagem**?
        Esta ferramenta cria um **vídeo a partir de várias imagens** (slides) e uma **trilha de áudio**, sincronizando automaticamente a exibição de **legendas** com o tempo de leitura (WPM – palavras por minuto).  
        É ideal para vídeos educacionais, poesias, citações, resumos ou qualquer conteúdo que combine imagens, música e texto.

        ---
        ### 🧩 Componentes da interface

        #### 1. **Envio de imagens e áudio**
        - **Imagens**: faça upload dos arquivos (PNG, JPG, WEBP) na ordem desejada. Cada imagem será um slide.
        - **Áudio**: envie um arquivo MP3, WAV ou M4A. A duração do áudio define o tempo total do vídeo.
        - *Sem áudio?* O sistema permite definir a duração manualmente (útil para testes ou roteiros).

        #### 2. **Duração e distribuição dos slides**
        - O sistema **divide o tempo total igualmente** entre as imagens.  
          Exemplo: 10 imagens + áudio de 60s → cada slide dura **6 segundos**.
        - Você vê as métricas: número de imagens, duração total, segundos por slide.

        #### 3. **Legenda sincronizada (proporcional ao tempo de leitura)**
        - **O que é WPM?**  
          Palavras Por Minuto (Words Per Minute). É a velocidade média de leitura.  
          Padrão: 150 WPM (leitura normal). Valores menores = leitura mais lenta; maiores = mais rápida.
        - **Como funciona a sincronia?**  
          Você cola um texto longo. O sistema:
          1. Conta o número de palavras.
          2. Calcula o tempo total de leitura: `(palavras / WPM) * 60` segundos.
          3. Compara com a duração da música.  
             - Se o texto for **mais longo** que a música, ele é **comprimido** (exibido mais rápido).  
             - Se for **mais curto**, o texto é **esticado** (exibido mais devagar) ou você pode adicionar pausas.
          4. Divide o texto em **blocos** cujo tempo de exibição é exatamente o tempo de leitura de cada bloco, respeitando a duração total da música.
        - **Exemplo prático:**  
          Música de 60s, WPM=150. Texto com 150 palavras → leitura ideal = 60s → perfeito.  
          Texto com 300 palavras → leitura ideal = 120s, mas só temos 60s → cada palavra será exibida em metade do tempo (WPM efetivo = 300). O sistema ajusta automaticamente.
        - **Controle deslizante de WPM:**  
          Você pode aumentar ou diminuir o WPM para tornar a legenda mais rápida ou mais lenta. O preview mostra quantos blocos serão gerados e se o texto cabe na música.

        #### 4. **Arte do texto (tipografia)**
        - **Família tipográfica:** Sans (sem serifa), Serif, Mono (monoespaçada).
        - **Tamanho:** ajuste em pixels (recomendado entre 36 e 72 para 1280×720).
        - **Cor e alinhamento:** horizontal (centro, esquerda, direita) e vertical (topo, centro, base).
        - **Sombreamento:** adiciona profundidade (cor e opacidade).
        - **Contorno (outline):** borda ao redor das letras, com espessura ajustável.
        - **Caixa de fundo:** um retângulo semi-transparente atrás do texto, melhora a legibilidade sobre imagens claras/escuras.
        - **Preview ao vivo:** mostra como ficará o texto com as configurações atuais.

        #### 5. **Animações da legenda**
        - **Estático:** texto fixo durante todo o slide.
        - **Rolagem (baixo → cima):** texto sobe continuamente, como créditos de filme.
        - **Fade In:** texto aparece gradualmente.
        - **Fade Out:** texto desaparece gradualmente.
        - **Typewriter (letra a letra):** as letras vão surgindo uma a uma.
        - **Palavra por palavra:** cada palavra aparece no ritmo do WPM.
        - **Slide lateral (direita → centro / esquerda → centro):** texto entra lateralmente com efeito ease-out.
        - **Zoom (cresce):** texto começa pequeno e aumenta até o tamanho normal.
        - **Pulso / Glow:** o texto pulsa em brilho (ideal para energia, frequências).

        #### 6. **Modos de exibição da legenda**
        - **Blocos proporcionais ao WPM (recomendado):**  
          O texto completo é dividido em blocos que aparecem nos momentos exatos calculados pelo WPM.  
          *Exemplo:* se o primeiro bloco deve ser lido em 2.3 segundos, ele aparece no slide correspondente e desaparece após esse tempo.
        - **Uma legenda por slide:**  
          Você digita um texto diferente para cada imagem. Não há divisão automática – cada slide mostra seu próprio texto estático (ou com animação, mas sem quebra temporal).
        - **Sem legenda:**  
          Apenas as imagens e o áudio, sem texto.

        #### 7. **Roteiro de montagem (TXT)**
        - Clique em **📄 Gerar Roteiro TXT** para baixar um arquivo com:
          - Sequência de slides (nome do arquivo, tempo de início/fim).
          - Blocos de legenda com timestamps.
          - Configurações tipográficas e de animação.
          - Instruções técnicas para edição manual (CapCut, Premiere, DaVinci).

        #### 8. **Geração do vídeo MP4**
        - Após configurar tudo, clique em **🚀 GERAR VÍDEO SINCRONIZADO**.
        - O processo:
          1. Redimensiona todas as imagens para 1280×720.
          2. Aplica as animações de texto escolhidas.
          3. Adiciona transição **dissolve** entre slides (número de frames configurável).
          4. Mistura o áudio de fundo.
          5. Exporta o vídeo final em H.264/AAC.
        - Um **progresso** é exibido. Ao final, você pode **assistir e baixar** o MP4.

        ---
        ### ⚙️ Como configurar a proporcionalidade (WPM) para o seu usuário?
        1. **Defina o público-alvo:**
           - Crianças ou leitores iniciantes → WPM baixo (80–100).
           - Adultos médios → WPM 150–180.
           - Leitura técnica/ rápida → WPM 200–250.
        2. **Ajuste o WPM no slider** enquanto observa o indicador "Tempo de leitura estimado" vs "Duração da música".
        3. **Teste com um texto pequeno** para ver a divisão em blocos (expansão "Preview dos blocos de legenda").
        4. **Use a animação "Palavra por palavra"** para reforçar o ritmo de leitura – cada palavra aparece exatamente no momento em que deveria ser lida.
        5. **Se o texto for muito longo para a música**, o sistema automaticamente comprime (aumenta o WPM efetivo). Você pode evitar isso encurtando o texto ou aumentando a duração da música.

        ---
        ### 💡 Dicas avançadas
        - **Combine com a aba IA:** Use a transcrição (Whisper) para obter o texto a partir de um áudio falado, depois cole na legenda.
        - **Gere prompts musicais:** Na sub-aba **🎵 Prompts para IAs de Áudio**, crie prompts prontos para Suno AI ou Udio baseados no tema do seu vídeo.
        - **Exporte o roteiro** antes de gerar o vídeo – útil para revisão ou edição manual em softwares profissionais.
        - **Evite textos muito longos** (acima de 500 palavras) para não sobrecarregar a legenda; prefira dividir em vários vídeos.

        ---
    """)
        
# ==============================================================================
# ABAS PRINCIPAIS (COM TOOLTIPS MELHORADOS)
# ==============================================================================

def tab_video():
    st.markdown('<div class="stitle">🎞️ EDITOR DE VÍDEO</div>', unsafe_allow_html=True)

    clip = st.session_state.video_clip

    if clip is None:
        st.markdown(f"""
        <div class="card cl">
        <b>🎬 Envie um vídeo</b> pela barra lateral para usar o editor.<br>
        Formatos: MP4, MOV, AVI, MKV, WEBM<br>
        Suporte: <b>{'✅ MoviePy ativo' if VIDEO_SUPPORT else '❌ instale: pip install moviepy imageio-ffmpeg'}</b>
        </div>
        """, unsafe_allow_html=True)
        st.info("💡 **Dica:** Você também pode começar com uma imagem. A edição de vídeo só aparece após o upload.")
        return

    dur = float(clip.duration)

# --- Substituição do Player Original e Frames ---
    st.markdown('<div class="vbox">', unsafe_allow_html=True)
    st.markdown('<div class="vbox-title">▶️ PLAYER DO VÍDEO ORIGINAL</div>', unsafe_allow_html=True)
    
    # Colunas para centralizar o player de vídeo
    col_v1, col_v2, col_v3 = st.columns([1, 2, 1])
    with col_v2:
        if st.session_state.video_path and os.path.exists(st.session_state.video_path):
            with open(st.session_state.video_path, "rb") as f:
                vbytes_orig = f.read()
            st.video(vbytes_orig) 
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🎯 NAVEGAÇÃO DE FRAMES")
    st.caption("Extraia um frame específico para editar como imagem (útil para thumbnails ou efeitos pontuais).")
    
    col_fr1, col_fr2, col_fr3 = st.columns([2,1,1])
    with col_fr1:
        t_frame = st.slider("Segundo do frame:", 0.0, dur-0.1,
                             st.session_state._current_frame_sec, 0.1, key="frame_slider",
                             help="Deslize para escolher o instante exato do frame.")
    with col_fr2:
        if st.button("📷 Extrair Frame", type="primary", key="extract_frame_btn",
                     help="Clique para extrair o frame selecionado e usá-lo nas abas de imagem."):
            frame = extract_frame(clip, t_frame)
            if frame:
                st.session_state.video_frame = frame
                st.session_state.base_image = frame
                st.session_state._current_frame_sec = t_frame
                st.session_state.processed_image = None
                st.success(f"Frame em {t_frame:.1f}s extraído!")
    with col_fr3:
        st.metric("Duração total", f"{dur:.1f}s")

    if st.session_state.video_frame:
        col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
        with col_img2:
            st.image(st.session_state.video_frame,
                    caption=f"Frame em {st.session_state._current_frame_sec:.1f}s — use na aba Filtros!",
                    use_container_width=False)
        st.markdown("<br>", unsafe_allow_html=True)  # <-- Adicionar esta linha

    st.markdown("---")
    st.markdown("### ⏱️ EFEITOS POR TEMPO (TIMELINE)")
    st.caption("Adicione segmentos de tempo e configure filtros/molduras que serão aplicados apenas nesses trechos.")

    segments = st.session_state.effect_segments
    
    # Exibir timeline visual
    if segments:
        st.markdown("**Segmentos ativos:**")
        cols = st.columns(20)
        for i, col in enumerate(cols):
            t = i * dur / 20
            col.markdown(f"<small>{t:.0f}s</small>", unsafe_allow_html=True)
        timeline_html = '<div class="timeline-bar">'
        for seg in sorted(segments, key=lambda x: x["start"]):
            left = (seg["start"] / dur) * 100
            width = ((seg["end"] - seg["start"]) / dur) * 100
            color = "#00e5ff" if seg["type"] == "Filtro" else ("#ff4d6d" if seg["type"] == "Moldura" else "#a8ff3e")
            timeline_html += f'<div class="timeline-segment" style="width:{width}%; left:{left}%; background:{color};" title="{seg["type"]}: {seg["start"]:.1f}s-{seg["end"]:.1f}s">{seg["type"][0]}</div>'
        timeline_html += '</div>'
        st.markdown(timeline_html, unsafe_allow_html=True)

        # Lista de segmentos com opção de remover
        for i, seg in enumerate(segments):
            cols = st.columns([2,1,1,1])
            cols[0].write(f"{seg['start']:.1f}s → {seg['end']:.1f}s")
            cols[1].write(seg['type'])
            if seg['type'] == 'Filtro':
                filtros = list(seg.get('params',{}).keys())
                cols[2].write(f"Filtros: {', '.join(filtros)}")
            elif seg['type'] == 'Moldura':
                cols[2].write(f"Moldura: {seg['params'].get('tipo','N/A')}")
            if cols[3].button("✖️", key=f"del_seg_{i}", help="Remover este segmento"):
                segments.pop(i)
                st.rerun()
    else:
        st.info("👆 Nenhum segmento de efeito definido. Adicione abaixo para começar a edição por tempo.")

    # Adicionar novo segmento
    with st.expander("➕ Adicionar segmento de efeito", expanded=True):
        c1, c2 = st.columns(2)
        start = c1.number_input("Início (s)", 0.0, dur, 0.0, 0.5, key="seg_start",
                                help="Momento em que o efeito começa.")
        end = c2.number_input("Fim (s)", 0.0, dur, min(dur, start+2.0), 0.5, key="seg_end",
                              help="Momento em que o efeito termina.")
        etype = st.selectbox("Tipo de Efeito", ["Filtro", "Moldura", "Animação"], key="seg_type",
                             help="Escolha qual categoria de efeito aplicar.")
        params = {}
        if etype == "Filtro":
            sels = st.multiselect("Selecione os filtros:", list(FILTER_DB.keys()), key="seg_filtros",
                                  help="Escolha um ou mais filtros para este trecho.")
            filtro_cfg = {}
            for fn in sels:
                with st.expander(f"Configurar {fn}"):
                    filtro_cfg[fn] = {}
                    for pname, (pmin, pmax, pdef) in FILTER_DB[fn]["params"].items():
                        filtro_cfg[fn][pname] = st.slider(pname, pmin, pmax, pdef, key=f"seg_f_{fn}_{pname}",
                                                          help=f"Ajuste a intensidade de {pname}.")
            params = filtro_cfg
        elif etype == "Moldura":
            fsel = st.selectbox("Escolha a moldura:", list(FRAME_DB.keys()), key="seg_frame")
            params = {
                "tipo": fsel,
                "cor": st.color_picker("Cor", FRAME_DB[fsel].get("cor","#FFFFFF"), key="seg_fcor"),
                "espessura": st.slider("Espessura", FRAME_DB[fsel].get("min",3), FRAME_DB[fsel].get("max",50), 15, key="seg_fesp")
            }
        else:  # Animação
            anim_sel = st.selectbox("Animação", list(ANIMATION_DB.keys()), key="seg_anim")
            params = {"tipo": anim_sel}
            # Parâmetros adicionais podem ser incluídos aqui se desejar controle fino
            # Por enquanto, usamos os valores padrão da animação (já aplicados em apply_animation_to_frame)
        if st.button("Adicionar Segmento", key="add_seg_btn",
                     help="Clique para incluir este trecho na timeline."):
            segments.append({"start": start, "end": end, "type": etype, "params": params})
            st.rerun()

    st.markdown("---")
    st.markdown("### ✂️ CORTE & EFEITOS GLOBAIS (opcional)")
    st.caption("Aplicam-se ao vídeo inteiro ou ao corte definido, além dos efeitos da timeline.")

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        t_start = st.number_input("▶ Início (s)", 0.0, dur-0.1, 0.0, 0.5, key="v_start",
                                  help="Define o ponto de corte inicial (0 = início do vídeo).")
        t_end   = st.number_input("⏹ Fim (s)",   0.1, dur,     dur,  0.5, key="v_end",
                                  help="Define o ponto de corte final.")
    with col_e2:
        sels_vf = st.multiselect("🎨 Filtros visuais globais:",
                                 list(FILTER_DB.keys()),
                                 format_func=lambda x: f"{FILTER_DB[x]['icon']} {x}",
                                 key="vid_flt_sel",
                                 help="Filtros aplicados ao vídeo todo (após a timeline).")
        vid_filter_cfg = {}
        for fn in sels_vf:
            vid_filter_cfg[fn] = {p: float(pdef) for p,(_,_,pdef) in FILTER_DB[fn].get("params",{}).items()}

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        if st.button("▶️ Preview (5s)", type="secondary", key="v_prev5",
                     help="Gera uma prévia de 5 segundos a partir do início do corte, já com todos os efeitos aplicados."):
            with st.spinner("Processando preview 5s..."):
                # 1. Aplica os segmentos de efeito (timeline)
                processed = apply_effects_to_clip(clip, segments)
                # 2. Aplica filtros globais (se selecionados)
                if sels_vf:
                    processed = clip_fl_image(
                        processed,
                        lambda f: np.array(apply_filters(Image.fromarray(f), vid_filter_cfg))
                    )
                # 3. Aplica corte de 5 segundos
                pclip = clip_subclip(processed, t_start, min(t_start + 5, t_end))
                # 4. Exporta para preview
                data = export_clip(pclip)
                if data:
                    st.session_state._preview_video = data
                    st.success("Preview pronto!")

    with col_b2:
        if st.button("📐 Corte Simples", type="secondary", key="v_cut_only",
                     help="Exporta apenas o trecho cortado, sem efeitos da timeline ou globais."):
            with st.spinner("Cortando vídeo..."):
                exp_clip = clip_subclip(clip, t_start, t_end)
                data = export_clip(exp_clip)
                if data:
                    st.session_state._export_video = data
                    st.success("Corte exportado!")

    with col_b3:
        if st.button("💾 Exportar Completo", type="primary", key="v_exp_full",
                     help="Renderiza o vídeo final com timeline, filtros globais e corte."):
            with st.spinner(f"Exportando vídeo com todos os efeitos..."):
                # 1. Aplica segmentos da timeline
                processed = apply_effects_to_clip(clip, segments)
                # 2. Aplica filtros globais
                if sels_vf:
                    processed = clip_fl_image(
                        processed,
                        lambda f: np.array(apply_filters(Image.fromarray(f), vid_filter_cfg))
                    )
                # 3. Aplica corte final
                if t_start > 0 or t_end < dur:
                    processed = clip_subclip(processed, t_start, t_end)
                # 4. Exporta
                data = export_clip(processed)
                if data:
                    st.session_state._export_video = data
                    st.success("Exportado com sucesso!")
                    
# --- Substituição do Preview e Download Final ---
    if st.session_state._preview_video:
        st.markdown("---")
        st.markdown('<div class="vbox" style="border-color: var(--c2);">', unsafe_allow_html=True)
        st.markdown('<div class="vbox-title" style="color: var(--c2);">👁️ PREVIEW DO CORTE + FILTROS (5s)</div>', unsafe_allow_html=True)
        
        # Centralização do vídeo de preview
        col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
        with col_p2:
            st.video(st.session_state._preview_video)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state._export_video:
        st.markdown("---")
        st.success("✅ Vídeo pronto para download!")
        st.download_button(
            "⬇️ BAIXAR MP4 EDITADO",
            st.session_state._export_video,
            f"{st.session_state.project_name}_editado.mp4",
            "video/mp4",
            use_container_width=True,
            key="dl_mp4_final"
        )
        
def tab_filtros():
    st.markdown('<div class="stitle">🎨 FILTROS & MOLDURAS & TEXTO</div>', unsafe_allow_html=True)

    source = get_source_image()
    if source is None:
        st.markdown("""
        <div class="card cl">
        📂 <b>Nenhuma mídia carregada.</b><br>
        • Envie uma <b>imagem</b> pela barra lateral, ou<br>
        • Envie um <b>vídeo</b> e extraia um frame na aba "Editor de Vídeo"
        </div>
        """, unsafe_allow_html=True)
        st.info("💡 **Dica:** Você pode editar frames do vídeo! Vá em Editor de Vídeo > Extrair Frame.")
        return

    if st.session_state.video_clip is not None and st.session_state.video_frame is not None:
        st.markdown(f"""
        <div class="card co">
        🎬 Editando <b>frame do vídeo</b> em {st.session_state._current_frame_sec:.1f}s.
        Mude o frame na aba "Editor de Vídeo" e clique "Extrair Frame".
        </div>
        """, unsafe_allow_html=True)

    cfg = st.session_state.config
    col_ctrl, col_prev = st.columns([1, 1], gap="medium")

    with col_ctrl:
        with st.expander("🌈 FILTROS DE COR", expanded=True):
            st.caption("Selecione e ajuste os filtros. As alterações aparecem à direita.")
            sels = st.multiselect(
                "Selecione filtros:",
                list(FILTER_DB.keys()),
                format_func=lambda x: f"{FILTER_DB[x]['icon']} {x}",
                key="filter_sel",
                help="Escolha um ou mais filtros para aplicar à imagem."
            )
            cfg["filtros"] = {}
            for fn in sels:
                fi = FILTER_DB[fn]
                with st.expander(f"{fi['icon']} {fn} — {fi['desc']}", expanded=True):
                    cfg["filtros"][fn] = {}
                    for pname, (pmin, pmax, pdef) in fi.get("params",{}).items():
                        val = st.slider(
                            pname.capitalize(),
                            float(pmin), float(pmax), float(pdef),
                            key=f"fp_{fn}_{pname}",
                            help=f"Ajuste a intensidade de {pname}."
                        )
                        cfg["filtros"][fn][pname] = val

        with st.expander("⚙️ AJUSTES BÁSICOS", expanded=False):
            st.caption("Brilho, contraste, saturação e nitidez.")
            bright   = st.slider("☀️ Brilho",    0.3, 2.5, 1.0, 0.05, key="adj_bright")
            contrast = st.slider("◑ Contraste",  0.3, 2.5, 1.0, 0.05, key="adj_contrast")
            color    = st.slider("🎨 Saturação",  0.0, 3.0, 1.0, 0.05, key="adj_color")
            sharp    = st.slider("🔍 Nitidez",    0.0, 3.0, 1.0, 0.05, key="adj_sharp")
            cfg["ajustes"] = {"bright":bright,"contrast":contrast,"color":color,"sharp":sharp}

        with st.expander("🖼️ MOLDURA", expanded=False):
            st.caption("Adicione uma borda decorativa.")
            sel_frame = st.selectbox(
                "Tipo de moldura:",
                list(FRAME_DB.keys()),
                format_func=lambda x: f"{FRAME_DB[x]['icon']} {x}",
                key="frame_sel"
            )
            cfg["moldura"] = {"tipo": sel_frame}
            if sel_frame != "Nenhuma":
                fi = FRAME_DB[sel_frame]
                cfg["moldura"]["cor"] = st.color_picker(
                    "Cor", fi.get("cor","#FFFFFF"), key="frame_cor")
                cfg["moldura"]["espessura"] = st.slider(
                    "Espessura",
                    fi.get("min",3), fi.get("max",50),
                    fi.get("min",3) + (fi.get("max",50)-fi.get("min",3))//3,
                    key="frame_esp"
                )

        with st.expander("✍️ TEXTO NA IMAGEM", expanded=False):
            st.caption("Insira um texto personalizado.")
            cfg["texto"] = st.text_input("Texto:", placeholder="Seu texto aqui...", key="text_inp")
            if cfg["texto"]:
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    cfg["fonte"] = {
                        "tamanho": st.slider("Tamanho", 10, 200, 42, key="fnt_sz"),
                        "cor": st.color_picker("Cor", "#FFFFFF", key="fnt_cor"),
                        "tipo": "Padrão"
                    }
                with col_t2:
                    cfg["posicao"] = {
                        "horizontal": st.selectbox("Horizontal:",
                            ["Esquerda","Centro","Direita"], index=1, key="pos_h"),
                        "vertical": st.selectbox("Vertical:",
                            ["Topo","Meio","Base"], index=2, key="pos_v"),
                    }
                    cfg["contorno"] = {
                        "ativo": st.checkbox("Contorno", value=True, key="ctr_on"),
                        "cor": st.color_picker("Cor contorno", "#000000", key="ctr_cor"),
                        "espessura": st.slider("Espessura contorno", 1, 6, 2, key="ctr_esp"),
                    }

    with col_prev:
        st.markdown("### 👁️ PREVIEW AO VIVO")
        processed = source.copy()
        adj = cfg.get("ajustes", {})
        if adj.get("bright",1.0) != 1.0:
            processed = ImageEnhance.Brightness(processed).enhance(adj["bright"])
        if adj.get("contrast",1.0) != 1.0:
            processed = ImageEnhance.Contrast(processed).enhance(adj["contrast"])
        if adj.get("color",1.0) != 1.0:
            processed = ImageEnhance.Color(processed).enhance(adj["color"])
        if adj.get("sharp",1.0) != 1.0:
            processed = ImageEnhance.Sharpness(processed).enhance(adj["sharp"])
        if cfg.get("filtros"):
            processed = apply_filters(processed, cfg["filtros"])
        if cfg.get("moldura",{}).get("tipo","Nenhuma") != "Nenhuma":
            processed = apply_frame(processed, cfg["moldura"])
        if cfg.get("texto"):
            processed = apply_text(processed, cfg)
        st.session_state.processed_image = processed

        col_ba, col_dp = st.columns(2)
        with col_ba:
            st.image(source, caption="📷 Original", use_container_width=True)
        with col_dp:
            st.image(processed, caption="✨ Com Efeitos", use_container_width=True)

        st.markdown("---")
        st.markdown("**📥 EXPORTAR IMAGEM:**")
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            st.download_button("💾 PNG",
                img_to_bytes(processed,"PNG"),
                f"{st.session_state.project_name}.png","image/png",
                use_container_width=True, key="dl_png")
        with col_e2:
            st.download_button("💾 JPG",
                img_to_bytes(processed,"JPEG",93),
                f"{st.session_state.project_name}.jpg","image/jpeg",
                use_container_width=True, key="dl_jpg")
        with col_e3:
            st.download_button("💾 WEBP",
                img_to_bytes(processed,"WEBP",90),
                f"{st.session_state.project_name}.webp","image/webp",
                use_container_width=True, key="dl_webp")

def tab_animacoes():
    st.markdown('<div class="stitle">🎬 ANIMAÇÕES & GIF ANIMADO</div>', unsafe_allow_html=True)

    base = get_work_image()
    if base is None:
        st.markdown("""
        <div class="card cl">
        🎬 <b>Para criar animações:</b><br>
        • Envie uma <b>imagem</b> pela barra lateral, ou<br>
        • Extraia um <b>frame do vídeo</b> na aba "Editor de Vídeo"<br>
        • Depois aplique filtros na aba "Filtros" (opcional)
        </div>
        """, unsafe_allow_html=True)
        return

    col_c, col_p = st.columns([1, 1], gap="medium")

    with col_c:
        st.markdown("### 🎭 CONFIGURAR ANIMAÇÃO")
        sels = st.multiselect(
            "Escolha os efeitos de animação:",
            list(ANIMATION_DB.keys()),
            format_func=lambda x: f"{ANIMATION_DB[x]['icon']} {x} — {ANIMATION_DB[x]['desc']}",
            key="anim_sel",
            help="Selecione um ou mais efeitos que serão combinados."
        )
        st.markdown("#### ⚙️ Configurações Gerais")
        duracao  = st.slider("⏱️ Duração (segundos)", 0.5, 8.0, 2.0, 0.5, key="anim_dur",
                             help="Tempo total da animação.")
        fps_gif  = st.slider("🎞️ FPS do GIF", 8, 30, 15, 1, key="anim_fps",
                             help="Quadros por segundo. Valores maiores = animação mais suave.")
        loop_gif = st.selectbox("🔁 Loop", ["Infinito","1x","3x"], key="anim_loop",
                                help="Define quantas vezes o GIF se repetirá.")

        if sels:
            st.markdown("#### 📋 Efeitos selecionados:")
            for s in sels:
                ai = ANIMATION_DB[s]
                st.markdown(f"• {ai['icon']} **{s}** — {ai['desc']}")

        col_gb1, col_gb2 = st.columns(2)
        with col_gb1:
            gen_btn = st.button("🎬 GERAR GIF", type="primary",
                                key="gen_gif_btn", use_container_width=True,
                                help="Clique para criar o GIF com as configurações atuais.")
        with col_gb2:
            prev_btn = st.button("👁️ Preview Frame", type="secondary",
                                 key="prev_frame_btn", use_container_width=True,
                                 help="Mostra uma prévia estática do meio da animação.")

        if prev_btn:
            p = 0.5
            test_frame = base.copy().convert("RGBA")
            if "Girar" in sels:
                test_frame = test_frame.rotate(180, resample=Image.BILINEAR)
            if "Glitch" in sels:
                arr = np.array(test_frame)
                for _ in range(5):
                    y = random.randint(0,test_frame.height-1)
                    arr[y,:] = np.roll(arr[y,:], random.randint(-15,15), axis=0)
                test_frame = Image.fromarray(arr)
            st.image(test_frame.convert("RGB"), caption="Preview frame do meio", use_container_width=True)

        if gen_btn:
            if not sels:
                st.warning("⚠️ Selecione ao menos um efeito de animação.")
            else:
                anim_cfg = {s:{} for s in sels}
                with st.spinner(f"Gerando GIF ({duracao}s, ~{int(duracao*fps_gif)} frames)..."):
                    gif_data = make_gif(base, anim_cfg, duracao)
                    st.session_state._gif_data = gif_data
                    st.success(f"✅ GIF gerado! ({len(gif_data)//1024} KB)")

    with col_p:
        st.markdown("### 🖼️ RESULTADO")
        if st.session_state._gif_data:
            b64 = base64.b64encode(st.session_state._gif_data).decode()
            st.markdown(
                f'<img src="data:image/gif;base64,{b64}" '
                f'style="max-width:100%;border-radius:12px;'
                f'border:2px solid rgba(0,229,255,.4);'
                f'box-shadow:0 0 20px rgba(0,229,255,.2);"/>',
                unsafe_allow_html=True
            )
            st.markdown(f"**Tamanho:** {len(st.session_state._gif_data)//1024} KB")
            st.download_button(
                "⬇️ BAIXAR GIF",
                st.session_state._gif_data,
                f"{st.session_state.project_name}_animacao.gif",
                "image/gif",
                use_container_width=True,
                key="dl_gif_final"
            )
        else:
            st.image(base, caption="Imagem base — aguardando geração do GIF",
                     use_container_width=True)
            st.markdown("""
            <div class="card cg">
            💡 <b>Dica:</b> Você pode combinar múltiplos efeitos!<br>
            Ex: Zoom + Glitch + Piscar = efeito cinematográfico único.
            </div>
            """, unsafe_allow_html=True)

def tab_screenshot():
    st.markdown('<div class="stitle">📸 CAPTURA DE TELA</div>', unsafe_allow_html=True)

    modo = st.radio("Modo:", ["📁 Upload Manual", "🌐 URL via API", "📷 Câmera/Webcam"],
                    horizontal=True, key="ss_modo",
                    help="Escolha como deseja obter a imagem.")

    if modo == "📁 Upload Manual":
        st.markdown("""
        <div class="card co">
        💡 Faça uma captura de tela no seu sistema e envie abaixo.
        </div>
        """, unsafe_allow_html=True)
        f = st.file_uploader("Envie seu screenshot:", type=["png","jpg","jpeg","webp"],
                             key="ss_upload")
        if f:
            img = Image.open(f)
            st.session_state.screenshot_data = img
            st.session_state.base_image = img
            st.success("✅ Screenshot carregado! Disponível em Filtros & Animações.")
            st.image(img, use_container_width=True)

    elif modo == "🌐 URL via API":
        st.markdown("""
        <div class="card cl">
        Use a API do <b>ScreenshotMachine</b> ou similar.
        </div>
        """, unsafe_allow_html=True)
        api_key = st.text_input("🔑 API Key:", type="password", key="ss_api",
                                help="Obtenha uma chave gratuita em screenshotmachine.com")
        url_in  = st.text_input("🌐 URL da página:", placeholder="https://exemplo.com", key="ss_url")
        col_w, col_h = st.columns(2)
        with col_w: sw = st.selectbox("Largura:", [1280,1920,1024,800], key="ss_w")
        with col_h: sh = st.selectbox("Altura:",  [720,1080,768,600],  key="ss_h")

        if st.button("📸 Capturar", type="primary", key="ss_cap"):
            if url_in and api_key:
                with st.spinner("Capturando screenshot..."):
                    try:
                        api = (f"https://api.screenshotmachine.com"
                               f"?key={api_key}&url={url_in}"
                               f"&dimension={sw}x{sh}&format=png&cacheLimit=0")
                        r = requests.get(api, timeout=30)
                        if r.status_code == 200 and "image" in r.headers.get("content-type",""):
                            img = Image.open(BytesIO(r.content))
                            st.session_state.screenshot_data = img
                            st.session_state.base_image = img
                            st.success("✅ Screenshot capturado!")
                            st.image(img, use_container_width=True)
                        else:
                            st.error("API retornou erro. Verifique a chave.")
                    except Exception as e:
                        st.error(f"Erro: {e}")
            elif not api_key:
                st.warning("Informe a API Key.")
            elif not url_in:
                st.warning("Informe a URL.")

    else:
        st.markdown("""
        <div class="card cg">
        📷 Tire uma foto da sua tela com a câmera.
        </div>
        """, unsafe_allow_html=True)
        cam = st.camera_input("Tire uma foto:", key="ss_cam")
        if cam:
            img = Image.open(cam)
            st.session_state.screenshot_data = img
            st.session_state.base_image = img
            st.success("✅ Foto capturada! Disponível em Filtros & Animações.")

    if st.session_state.screenshot_data:
        st.markdown("---")
        st.markdown('<div class="stitle">🎨 EDIÇÃO RÁPIDA DO SCREENSHOT</div>', unsafe_allow_html=True)
        img = st.session_state.screenshot_data

        col_q, col_pv = st.columns([1, 2])
        with col_q:
            qf = st.selectbox("Filtro rápido:", ["Nenhum"] + list(FILTER_DB.keys()), key="ss_qf")
            bright   = st.slider("☀️ Brilho",   0.3, 2.5, 1.0, 0.05, key="ss_bright")
            contrast = st.slider("◑ Contraste", 0.3, 2.5, 1.0, 0.05, key="ss_contrast")
            sharp    = st.slider("🔍 Nitidez",   0.3, 3.0, 1.0, 0.05, key="ss_sharp")
            annot    = st.text_input("📝 Anotação:", placeholder="Adicione texto...", key="ss_annot")
            acor     = st.color_picker("Cor da anotação:", "#FF2244", key="ss_acor")
            apos_h   = st.selectbox("Posição H:", ["Esquerda","Centro","Direita"], index=1, key="ss_ah")
            apos_v   = st.selectbox("Posição V:", ["Topo","Meio","Base"], index=2, key="ss_av")

        with col_pv:
            edited = img.copy()
            edited = ImageEnhance.Brightness(edited).enhance(bright)
            edited = ImageEnhance.Contrast(edited).enhance(contrast)
            edited = ImageEnhance.Sharpness(edited).enhance(sharp)
            if qf != "Nenhum":
                fc = {p: float(pdef) for p,(_,_,pdef) in FILTER_DB[qf].get("params",{}).items()}
                edited = apply_filters(edited, {qf: fc})
            if annot:
                edited = apply_text(edited, {
                    "texto": annot,
                    "fonte": {"tamanho":32,"cor":acor,"tipo":"Padrão"},
                    "posicao": {"horizontal":apos_h,"vertical":apos_v},
                    "contorno": {"ativo":True,"cor":"#000000","espessura":2},
                })
            st.image(edited, caption="Screenshot editado", use_container_width=True)

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("⬇️ PNG",
                    img_to_bytes(edited,"PNG"),
                    "screenshot_editado.png","image/png",
                    use_container_width=True, key="dl_ss_png")
            with col_dl2:
                if st.button("📋 Usar como base p/ Filtros", key="ss_to_base",
                             help="Define esta imagem como a imagem base para as outras abas."):
                    st.session_state.base_image = edited
                    st.session_state.processed_image = None
                    st.success("✅ Screenshot definido como imagem base!")

def tab_ia_audio():
    st.markdown('<div class="stitle">🤖 IA & ÁUDIO</div>', unsafe_allow_html=True)
    sub1, sub2, sub3 = st.tabs(["🗣️ Texto → Áudio (TTS)", "🎧 Transcrição", "📊 Análise & Prompts"])

    with sub1:
        st.markdown("**Converta texto em narração neural PT-BR com edge-tts**")
        if not TTS_SUPPORT:
            st.error("❌ edge-tts não instalado. Execute: `pip install edge-tts`")
            return

        col_tv, col_ts = st.columns([2,1])
        with col_tv:
            tts_text = st.text_area("Texto para narrar:", height=180,
                                    placeholder="Digite ou cole o texto aqui...",
                                    key="tts_ta",
                                    help="Insira o texto que será convertido em fala.")
        with col_ts:
            vk = st.selectbox("Voz:", list(VOICE_PROFILES.keys()),
                              format_func=lambda x: VOICE_PROFILES[x]["name"],
                              key="tts_vk",
                              help="Escolha entre diferentes vozes neurais.")
            speed  = st.slider("Velocidade:", 0.5, 2.0, 1.0, 0.05, key="tts_spd",
                               help="Ajuste a velocidade da fala.")
            st.markdown(f"**Código:** `{VOICE_PROFILES[vk]['code']}`")

        if st.button("🔊 GERAR NARRAÇÃO", type="primary", key="gen_tts",
                     use_container_width=True,
                     help="Clique para gerar o arquivo de áudio."):
            if tts_text and tts_text.strip():
                with st.spinner("Gerando narração neural..."):
                    ok, result = tts_generate(tts_text.strip(), vk, speed)
                    if ok:
                        with open(result,"rb") as f:
                            abytes = f.read()
                        st.audio(abytes, format="audio/mp3")
                        st.download_button("⬇️ Baixar MP3",
                            abytes,
                            f"narracao_{st.session_state.project_name}.mp3",
                            "audio/mp3",
                            use_container_width=True, key="dl_tts_mp3")
                        st.success("✅ Narração gerada!")
                    else:
                        st.error(f"Falha: {result}")
            else:
                st.warning("Digite um texto.")

    with sub2:
        st.markdown("**Transcreva áudio/vídeo para texto com Whisper AI (offline)**")
        if not WHISPER_SUPPORT:
            st.error("❌ Whisper não instalado. Execute: `pip install openai-whisper`")
        else:
            ap = st.session_state.get("audio_path")
            if ap and os.path.exists(ap):
                with open(ap,"rb") as f:
                    st.audio(f.read(), format="audio/mp3")
                if st.button("📝 TRANSCREVER", type="primary", key="do_transcribe",
                             help="Inicia a transcrição. Pode levar alguns segundos."):
                    with st.spinner("Transcrevendo com Whisper (aguarde)..."):
                        try:
                            model = whisper.load_model("base")
                            result = model.transcribe(ap, language="pt", fp16=False)
                            st.session_state.transcribed_text = result["text"]
                            st.success("✅ Transcrição concluída!")
                        except Exception as e:
                            st.error(f"Erro: {e}")
            else:
                st.info("Envie um arquivo de áudio (MP3/WAV) pela barra lateral.")

        if st.session_state.transcribed_text:
            st.markdown("---")
            edited = st.text_area("Texto transcrito (editável):",
                                  value=st.session_state.transcribed_text,
                                  height=250, key="transcr_edit",
                                  help="Você pode editar o texto antes de baixar ou usar em outras ferramentas.")
            st.session_state.transcribed_text = edited
            wc = len(edited.split())
            c1,c2,c3 = st.columns(3)
            c1.metric("Palavras",   wc)
            c2.metric("Caracteres", len(edited))
            c3.metric("Leitura",    f"{round(wc/150,1)} min")
            st.download_button("⬇️ Baixar TXT",
                edited.encode("utf-8"),
                f"transcricao_{st.session_state.project_name}.txt",
                "text/plain", key="dl_txt")

    with sub3:
        st.markdown("**Analise seu conteúdo e gere prompts prontos para ChatGPT, Midjourney, Suno...**")
        text_in = st.text_area("Texto para analisar:",
                               value=st.session_state.transcribed_text or "",
                               height=120, key="an_text",
                               help="Cole ou use o texto transcrito para análise.")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            platform = st.selectbox("Plataforma:",
                ["YouTube","TikTok/Reels","Instagram","LinkedIn","Site/Blog"], key="plat",
                help="Para qual plataforma o conteúdo será otimizado?")
        with col_p2:
            tone = st.selectbox("Tom:",
                ["Inspirador","Informativo","Persuasivo","Divertido","Emocional"], key="tone",
                help="Qual o tom desejado para o conteúdo?")
        with col_p3:
            complexity = st.slider("Complexidade:", 1, 5, 3, key="cplx",
                                   help="Nível de detalhamento dos prompts.")

        if st.button("🔍 ANALISAR & GERAR PROMPTS", type="primary",
                     key="do_analyze", use_container_width=True,
                     help="Analisa o texto e gera prompts prontos para IAs."):
            if text_in.strip():
                with st.spinner("Analisando..."):
                    an = analyze_content(text_in.strip())
                    kws = [w for w in text_in.lower().split() if len(w)>4][:8]
                    prompts = gen_ai_prompts(an["primary"], kws, platform, tone)
                    st.session_state.video_analysis = an
                    st.session_state.enhanced_prompts = prompts
                    st.session_state.video_analysis_complete = True
                    st.success("✅ Análise concluída!")
            else:
                st.warning("Digite um texto.")

        if st.session_state.video_analysis_complete and st.session_state.video_analysis:
            an = st.session_state.video_analysis
            st.markdown("---")
            st.markdown("**📊 Análise do Conteúdo:**")
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Tema Principal", an["primary"].upper())
            c2.metric("Palavras",       an["word_count"])
            c3.metric("Engajamento",    f"{an['engagement']}%")
            c4.metric("Leitura",        f"{an['reading_min']} min")

            for th, sc in an.get("themes",{}).items():
                st.progress(min(sc*10,100)/100, text=f"  {th.title()}")

            if st.session_state.enhanced_prompts:
                st.markdown("---")
                st.markdown("**✨ Prompts para IA — copie e use em qualquer ferramenta:**")
                for ptype, pcontent in st.session_state.enhanced_prompts.items():
                    with st.expander(f"📋 {ptype}", expanded=False):
                        st.code(pcontent, language="text")

def _get_audio_duration_seconds(audio_bytes: bytes, ext: str) -> float:
    """Retorna duração do áudio em segundos usando ffprobe ou fallback."""
    try:
        import subprocess, tempfile, json as _json
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
            f.write(audio_bytes)
            tmp = f.name
        result = subprocess.run(
            ["ffprobe","-v","quiet","-print_format","json","-show_streams", tmp],
            capture_output=True, text=True, timeout=15
        )
        data = _json.loads(result.stdout)
        for s in data.get("streams", []):
            if "duration" in s:
                return float(s["duration"])
    except Exception:
        pass
    # fallback: estima pelo tamanho (128kbps MP3 ≈ 16000 bytes/s)
    return len(audio_bytes) / 16000.0


def _calc_wpm_duration(text: str, wpm: int) -> float:
    """Retorna duração de leitura em segundos para o texto dado o WPM."""
    words = len(text.split())
    return (words / max(wpm, 1)) * 60.0

def _get_animation_type_at_time(segments: List[Dict], time_sec: float) -> str:
    """Retorna o tipo de animação ativo no tempo `time_sec` (em segundos). Se nenhum segmento cobrir o tempo, retorna 'Estático'."""
    for seg in segments:
        if seg["start"] <= time_sec <= seg["end"]:
            return seg["type"]
    return "Estático"

def _split_text_by_time(text: str, total_duration: float, wpm: int) -> list:
    """
    Divide o texto em blocos proporcionais ao tempo de leitura.
    Retorna lista de (texto_bloco, inicio_s, fim_s).
    """
    words = text.split()
    if not words:
        return []
    total_words = len(words)
    secs_per_word = total_duration / max(total_words, 1)
    # agrupa palavras em blocos de ~wpm/4 palavras (chunk de ~15s)
    chunk_words = max(1, wpm // 4)
    blocks = []
    t = 0.0
    for i in range(0, total_words, chunk_words):
        chunk = words[i:i+chunk_words]
        dur = len(chunk) * secs_per_word
        blocks.append((" ".join(chunk), round(t, 2), round(t + dur, 2)))
        t += dur
    return blocks


def _render_text_on_image(
    img: Image.Image,
    text: str,
    font_size: int,
    font_color: str,
    font_name: str,          # nome amigável da fonte
    font_path: str,          # caminho real do arquivo .ttf/.otf
    h_align: str,
    v_align: str,
    shadow: bool,
    shadow_color: str,
    bold: bool,
    italic: bool,
    outline: bool,
    outline_color: str,
    outline_w: int,
    bg_box: bool,
    bg_box_color: str,
    bg_box_alpha: int,
    margin_pct: float = 0.05,
) -> Image.Image:
    """Renderiza texto sobre imagem com todas as opções de arte tipográfica."""
    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    # Carrega a fonte especificada
    font = None
    if font_path and os.path.exists(font_path):
        try:
            # Tenta aplicar variações de estilo (se a fonte suportar)
            # Muitas fontes têm arquivos separados para bold/italic. Vamos usar o mesmo arquivo
            # e simular negrito/itálico com transformações do PIL? Infelizmente não é trivial.
            # Para simplificar, usamos a fonte base e confiamos que o usuário escolha uma fonte que já tenha o estilo desejado.
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()

    # Wrap text
    margin_px = int(W * margin_pct)
    max_w = W - 2 * margin_px
    lines = []
    for paragraph in text.split("\n"):
        words_p = paragraph.split()
        line = ""
        for word in words_p:
            test = (line + " " + word).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)

    # Total height
    line_h = font_size + int(font_size * 0.3)
    total_h = len(lines) * line_h

    # Vertical position
    if v_align == "Topo":
        y_start = margin_px
    elif v_align == "Centro":
        y_start = (H - total_h) // 2
    else:  # Base
        y_start = H - total_h - margin_px

    # Background box
    if bg_box and lines:
        pad = int(font_size * 0.4)
        box_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
        box_draw = ImageDraw.Draw(box_img)
        try:
            bc = ImageColor.getrgb(bg_box_color) + (int(bg_box_alpha * 2.55),)
        except Exception:
            bc = (0, 0, 0, int(bg_box_alpha * 2.55))
        box_draw.rectangle(
            [margin_px - pad, y_start - pad,
             W - margin_px + pad, y_start + total_h + pad],
            fill=bc
        )
        img = Image.alpha_composite(img, box_img)
        draw = ImageDraw.Draw(img)

    # Draw lines
    try:
        fc = ImageColor.getrgb(font_color)
    except Exception:
        fc = (255, 255, 255)
    try:
        sc = ImageColor.getrgb(shadow_color)
    except Exception:
        sc = (0, 0, 0)
    try:
        oc = ImageColor.getrgb(outline_color)
    except Exception:
        oc = (0, 0, 0)

    y = y_start
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        if h_align == "Centro":
            x = (W - lw) // 2
        elif h_align == "Direita":
            x = W - lw - margin_px
        else:
            x = margin_px

        # Simular negrito (opcional: usar ImageFont com variação bold se disponível)
        if bold:
            # Desenha o texto deslocado para simular negrito (imperfeito, mas funcional)
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                draw.text((x+dx, y+dy), line, font=font, fill=fc)
        # Simular itálico (inclinação) – não implementado aqui por simplicidade

        # Shadow
        if shadow:
            sd = max(2, font_size // 14)
            draw.text((x + sd, y + sd), line, font=font, fill=sc)

        # Outline
        if outline:
            for dx in range(-outline_w, outline_w + 1):
                for dy in range(-outline_w, outline_w + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), line, font=font, fill=oc)

        # Main text (se bold já foi desenhado, pode pular para evitar duplicidade)
        if not bold:
            draw.text((x, y), line, font=font, fill=fc)
        y += line_h

    return img.convert("RGB")

def _render_text_layer(text: str, W: int, H: int, tcfg: dict) -> Image.Image:
    """
    Renderiza apenas a camada de texto (RGBA transparente) para composição animada.
    Suporta font_path, tamanho, cor, sombra, contorno, caixa de fundo.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not text or not text.strip():
        return layer

    font_size = tcfg.get("font_size", 48)
    font_color = tcfg.get("font_color", "#FFFFFF")
    font_path = tcfg.get("font_path", "")
    h_align = tcfg.get("h_align", "Centro")
    v_align = tcfg.get("v_align", "Base")
    shadow = tcfg.get("shadow", True)
    shadow_color = tcfg.get("shadow_color", "#000000")
    outline = tcfg.get("outline", False)
    outline_color = tcfg.get("outline_color", "#000000")
    outline_w = tcfg.get("outline_w", 2)
    bg_box = tcfg.get("bg_box", False)
    bg_box_color = tcfg.get("bg_box_color", "#000000")
    bg_box_alpha = tcfg.get("bg_box_alpha", 60)
    margin_pct = 0.05

    # Carrega a fonte
    font = None
    if font_path and os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
    else:
        # Fallback para fontes comuns do sistema
        fallback_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:\\Windows\\Fonts\\Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc"
        ]
        for fb in fallback_fonts:
            if os.path.exists(fb):
                try:
                    font = ImageFont.truetype(fb, font_size)
                    break
                except:
                    pass
        if font is None:
            font = ImageFont.load_default()

    draw = ImageDraw.Draw(layer)
    margin_px = int(W * margin_pct)
    max_w = W - 2 * margin_px

    # Quebra de linha
    lines = []
    for paragraph in text.split("\n"):
        words_p = paragraph.split()
        line = ""
        for word in words_p:
            test = (line + " " + word).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)

    if not lines:
        return layer

    line_h = font_size + int(font_size * 0.3)
    total_h = len(lines) * line_h

    if v_align == "Topo":
        y_start = margin_px
    elif v_align == "Centro":
        y_start = (H - total_h) // 2
    else:
        y_start = H - total_h - margin_px

    # Caixa de fundo
    if bg_box:
        pad = int(font_size * 0.4)
        try:
            bc = ImageColor.getrgb(bg_box_color) + (int(bg_box_alpha * 2.55),)
        except Exception:
            bc = (0, 0, 0, int(bg_box_alpha * 2.55))
        draw.rectangle(
            [margin_px - pad, y_start - pad,
             W - margin_px + pad, y_start + total_h + pad],
            fill=bc
        )

    try:
        fc = ImageColor.getrgb(font_color) + (255,)
    except Exception:
        fc = (255, 255, 255, 255)
    try:
        sc = ImageColor.getrgb(shadow_color) + (180,)
    except Exception:
        sc = (0, 0, 0, 180)
    try:
        oc = ImageColor.getrgb(outline_color) + (255,)
    except Exception:
        oc = (0, 0, 0, 255)

    y = y_start
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        if h_align == "Centro":
            x = (W - lw) // 2
        elif h_align == "Direita":
            x = W - lw - margin_px
        else:
            x = margin_px

        if shadow:
            sd = max(2, font_size // 14)
            draw.text((x + sd, y + sd), line, font=font, fill=sc)
        if outline:
            for dx in range(-outline_w, outline_w + 1):
                for dy in range(-outline_w, outline_w + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), line, font=font, fill=oc)
        draw.text((x, y), line, font=font, fill=fc)
        y += line_h

    return layer

def _apply_text_animation(
    base_bgr: np.ndarray,
    text_layer: Image.Image,
    anim_type: str,
    frame_i: int,
    n_frames: int,
    fps: int,
    text: str,
    tcfg: dict,
    interval_progress: float = None,
) -> np.ndarray:
    W = base_bgr.shape[1]
    H = base_bgr.shape[0]
    
    # Se não houver texto ou se estivermos fora do intervalo de legenda (interval_progress None)
    # e não houver texto, retorna apenas o frame base (sem legenda)
    if not text or not text.strip():
        return cv2.cvtColor(base_bgr, cv2.COLOR_BGR2RGB)  # sem texto

    # Se estiver fora do intervalo (interval_progress é None) e o texto não deve aparecer,
    # retorna o frame base.
    if interval_progress is None:
        return cv2.cvtColor(base_bgr, cv2.COLOR_BGR2RGB)

    # Agora estamos dentro do intervalo: usa interval_progress (0..1) para animação
    t = interval_progress

    base_pil = Image.fromarray(cv2.cvtColor(base_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")

    if anim_type == "Estático" or not text or not text.strip():
        result = Image.alpha_composite(base_pil, text_layer)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    elif anim_type == "Rolagem (baixo→cima)":
        offset_y = int(H - t * (H + H))
        shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shifted.paste(text_layer, (0, offset_y))
        result = Image.alpha_composite(base_pil, shifted)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    elif anim_type == "Fade In":
        alpha_val = int(min(t * 2, 1.0) * 255)
        faded = text_layer.copy()
        r, g, b, a = faded.split()
        a = a.point(lambda x: int(x * alpha_val / 255))
        faded = Image.merge("RGBA", (r, g, b, a))
        result = Image.alpha_composite(base_pil, faded)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    elif anim_type == "Fade Out":
        alpha_val = int(max(1.0 - t * 2, 0.0) * 255)
        faded = text_layer.copy()
        r, g, b, a = faded.split()
        a = a.point(lambda x: int(x * alpha_val / 255))
        faded = Image.merge("RGBA", (r, g, b, a))
        result = Image.alpha_composite(base_pil, faded)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    elif anim_type == "Typewriter (letra a letra)":
        total_chars = len(text)
        chars_to_show = max(1, int(t * total_chars))
        partial_text = text[:chars_to_show]
        partial_layer = _render_text_layer(partial_text, W, H, tcfg)
        result = Image.alpha_composite(base_pil, partial_layer)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    elif anim_type == "Palavra por Palavra":
        words = text.split()
        total_words = len(words)
        words_to_show = max(1, int(t * total_words))
        partial_text = " ".join(words[:words_to_show])
        partial_layer = _render_text_layer(partial_text, W, H, tcfg)
        result = Image.alpha_composite(base_pil, partial_layer)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    elif anim_type == "Slide Lateral (direita→centro)":
        ease = 1 - (1 - min(t * 1.5, 1.0)) ** 3
        offset_x = int((1 - ease) * W)
        shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shifted.paste(text_layer, (offset_x, 0))
        result = Image.alpha_composite(base_pil, shifted)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    elif anim_type == "Slide Lateral (esquerda→centro)":
        ease = 1 - (1 - min(t * 1.5, 1.0)) ** 3
        offset_x = int(-(1 - ease) * W)
        shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shifted.paste(text_layer, (offset_x, 0))
        result = Image.alpha_composite(base_pil, shifted)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    elif anim_type == "Zoom (cresce)":
        scale = 0.3 + 0.7 * min(t * 1.5, 1.0)
        new_w = max(1, int(W * scale))
        new_h = max(1, int(H * scale))
        resized = text_layer.resize((new_w, new_h), Image.LANCZOS)
        zoomed = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        paste_x = (W - new_w) // 2
        paste_y = (H - new_h) // 2
        zoomed.paste(resized, (paste_x, paste_y))
        result = Image.alpha_composite(base_pil, zoomed)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    elif anim_type == "Pulso / Glow":
        pulse = 0.6 + 0.4 * math.sin(t * math.pi * 4)
        alpha_val = int(pulse * 255)
        faded = text_layer.copy()
        r, g, b, a = faded.split()
        a = a.point(lambda x: int(x * alpha_val / 255))
        faded = Image.merge("RGBA", (r, g, b, a))
        result = Image.alpha_composite(base_pil, faded)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)

    else:
        result = Image.alpha_composite(base_pil, text_layer)
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)
        
def _build_video_from_slides(
    slides: list,
    audio_bytes: bytes,
    audio_ext: str,
    fps: int,
    transition_frames: int,
    output_path: str,
    progress_cb=None,
    animation_segments: List[Dict] = None,
    default_anim_type: str = "Estático",
    legenda_interval_start: float = 0.0,   # NOVO
    legenda_interval_end: float = 0.0,     # NOVO
) -> str:
    import subprocess, tempfile

    if animation_segments is None:
        animation_segments = []

    W, H = 1280, 720
    tmp_dir = tempfile.mkdtemp(prefix="mont_vid_")

    frame_idx = 0
    total_slides = len(slides)
    global_time = 0.0

    for si, (pil_img, dur_s, text, tcfg) in enumerate(slides):
        if progress_cb:
            progress_cb((si + 0.5) / total_slides * 0.8)

        slide_img = pil_img.convert("RGB").resize((W, H), Image.LANCZOS)
        base_bgr = cv2.cvtColor(np.array(slide_img), cv2.COLOR_RGB2BGR)
        n_frames = max(1, int(dur_s * fps))
        text_layer = _render_text_layer(text or "", W, H, tcfg)

        # Transição dissolve
        if si > 0 and transition_frames > 0:
            for tf in range(transition_frames):
                alpha = tf / transition_frames
                blended_base = cv2.addWeighted(np.zeros_like(base_bgr), 1 - alpha, base_bgr, alpha, 0)
                t_global = global_time + (tf / fps)
                anim_type = _get_animation_type_at_time(animation_segments, t_global)
                if anim_type == "Estático" and not animation_segments:
                    anim_type = default_anim_type

                # Calcula progresso específico para o intervalo de legenda
                if legenda_interval_end > legenda_interval_start and legenda_interval_start <= t_global <= legenda_interval_end:
                    # Progresso linear dentro do intervalo
                    interval_progress = (t_global - legenda_interval_start) / (legenda_interval_end - legenda_interval_start)
                else:
                    interval_progress = None  # usa o progresso padrão do slide

                final_frame = _apply_text_animation(
                    blended_base, text_layer, anim_type, tf, n_frames, fps, text or "", tcfg,
                    interval_progress=interval_progress  # NOVO parâmetro
                )
                fname = os.path.join(tmp_dir, f"frame_{frame_idx:06d}.jpg")
                cv2.imwrite(fname, final_frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                frame_idx += 1
            global_time += transition_frames / fps

        # Frames principais
        for fi in range(n_frames):
            t_global = global_time + (fi / fps)
            anim_type = _get_animation_type_at_time(animation_segments, t_global)
            if anim_type == "Estático" and not animation_segments:
                anim_type = default_anim_type

            if legenda_interval_end > legenda_interval_start and legenda_interval_start <= t_global <= legenda_interval_end:
                interval_progress = (t_global - legenda_interval_start) / (legenda_interval_end - legenda_interval_start)
            else:
                interval_progress = None

            final_frame = _apply_text_animation(
                base_bgr, text_layer, anim_type, fi, n_frames, fps, text or "", tcfg,
                interval_progress=interval_progress
            )
            fname = os.path.join(tmp_dir, f"frame_{frame_idx:06d}.jpg")
            cv2.imwrite(fname, final_frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            frame_idx += 1

        global_time += dur_s

    if progress_cb:
        progress_cb(0.85)

    # Áudio e FFmpeg...
    audio_tmp = os.path.join(tmp_dir, f"audio.{audio_ext}")
    with open(audio_tmp, "wb") as f:
        f.write(audio_bytes)

    pattern = os.path.join(tmp_dir, "frame_%06d.jpg")
    total_vid_dur = sum(s[1] for s in slides)

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", pattern,
        "-i", audio_tmp,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-t", str(total_vid_dur),
        output_path
    ]
    subprocess.run(cmd, capture_output=True, timeout=300)

    if progress_cb:
        progress_cb(1.0)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return output_path

def get_available_fonts():
    """
    Retorna uma tupla: (lista_de_nomes_de_fontes, dicionario_nome->caminho)
    Detecta fontes nos principais sistemas operacionais.
    """
    font_paths = []
    if sys.platform == "win32":
        possible_dirs = [
            "C:\\Windows\\Fonts",
            os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\Fonts"),
        ]
    elif sys.platform == "darwin":
        possible_dirs = [
            "/System/Library/Fonts",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ]
    else:
        possible_dirs = [
            "/usr/share/fonts/truetype",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts"),
        ]

    for d in possible_dirs:
        if os.path.exists(d):
            for root, dirs, files in os.walk(d):
                for f in files:
                    if f.lower().endswith((".ttf", ".otf")):
                        font_paths.append(os.path.join(root, f))

    fonts = {}
    for path in font_paths:
        name = os.path.basename(path).replace(".ttf", "").replace(".otf", "").replace("-", " ")
        name = re.sub(r'\s*(Regular|Bold|Italic|Light|Medium|Black)\s*$', '', name, flags=re.I)
        fonts[name] = path

    sorted_names = sorted(fonts.keys())
    if not sorted_names:
        # Fallback
        common_fonts = ["Arial", "Times New Roman", "Courier New", "Verdana", "Impact"]
        fonts = {name: "" for name in common_fonts}
        return list(fonts.keys()), fonts

    return sorted_names, fonts

def format_legenda_com_timestamps(blocks_abs: List[Tuple[str, float, float]]) -> str:
    """Converte blocos (texto, start, end) em uma string com timestamps no formato '[start] texto'."""
    lines = []
    for txt, start, end in blocks_abs:
        lines.append(f"[{start:.1f}] {txt}")
    return "\n".join(lines)


def tab_montagem():
    st.markdown('<div class="stitle">🎼 MONTAGEM SINCRONIZADA + PROMPTS MUSICAIS</div>', unsafe_allow_html=True)
    sub_a, sub_b = st.tabs(["🎵 Prompts para IAs de Áudio", "🎬 Montagem Sincronizada com Legenda"])

    # =========================================================================
    # ABA PROMPTS MUSICAIS (inalterada)
    # =========================================================================
    with sub_a:
        st.markdown("**Gere prompts para Suno AI, Udio, ElevenLabs, MusicGen...**")
        col_t, col_p = st.columns(2)
        with col_t:
            tema = st.selectbox("Tema visual:", list(PERFIS_MUSICAIS.keys()), key="mt_tema",
                                help="Escolha o perfil emocional da música.")
            conceito = st.text_input("Conceito principal:", "superação e conquista", key="mt_conceito",
                                     help="Descreva brevemente o tema central.")
            duracao = st.slider("Duração da trilha (s):", 15, 300, 60, key="mt_dur",
                                help="Duração desejada para a trilha sonora.")
        with col_p:
            pi = PERFIS_MUSICAIS[tema]
            st.markdown(f"""
            <div class="card co">
            <b>Perfil {tema}</b><br>
            🎵 BPM: {pi['bpm']}<br>
            😊 Emoção: {pi['emocao']}<br>
            🎨 Cores: {' • '.join(pi['cores'])}
            </div>
            """, unsafe_allow_html=True)

        if st.button("✨ GERAR PROMPTS", type="primary", key="gen_mp", use_container_width=True,
                     help="Gera prompts prontos para ferramentas de IA de áudio e imagem."):
            prompts = {
                "🎨 Prompt Imagem": (f"Crie imagem {tema.lower()} sobre '{conceito}'. "
                                     f"Paleta: {' e '.join(pi['cores'])}. Emoção: {pi['emocao']}. "
                                     f"Alta qualidade, composição impactante, formato 16:9."),
                "🎵 Prompt Trilha Sonora": (f"Trilha sonora {tema.lower()} para vídeo.\n"
                                            f"Duração: {duracao}s | BPM: {pi['bpm']} | Emoção: {pi['emocao']}\n"
                                            f"Conceito: {conceito}\n"
                                            f"Progressão: intro → build → clímax → resolução.\n"
                                            f"Sem vocal. Formato MP3."),
                "📝 Prompt Texto/Roteiro": (f"Escreva roteiro {tema.lower()} com emoção {pi['emocao']} sobre '{conceito}'.\n"
                                            f"Estrutura: gancho (20 palavras) → desenvolvimento (150p) → CTA (30p).\n"
                                            f"Tom: {pi['emocao']}."),
                "🤖 Prompt ChatGPT": (f"Você é um especialista em criação de conteúdo {tema.lower()}. "
                                      f"Crie um roteiro completo sobre '{conceito}' com duração de {duracao//60} minutos. "
                                      f"Tom: {pi['emocao']}. Inclua: gancho inicial, 3 pontos principais, conclusão e CTA."),
            }
            st.session_state["_music_prompts"] = {"prompts": prompts, "tema": tema, "bpm": pi["bpm"]}

        if st.session_state.get("_music_prompts"):
            mp = st.session_state["_music_prompts"]
            for pk, pv in mp["prompts"].items():
                with st.expander(f"📋 {pk}", expanded=True):
                    st.code(pv, language="text")
            pkg = json.dumps(mp["prompts"], ensure_ascii=False, indent=2)
            st.download_button("⬇️ Baixar Pacote de Prompts (JSON)",
                               pkg.encode("utf-8"),
                               f"prompts_{mp['tema']}.json",
                               "application/json", key="dl_mp_json")

    # =========================================================================
    # ABA MONTAGEM SINCRONIZADA (com todas as melhorias)
    # =========================================================================
    with sub_b:
        # ---- Definições iniciais ----
        ANIM_OPTIONS = {
            "Estático": "Texto fixo, sem movimento.",
            "Rolagem (baixo→cima)": "Texto sobe continuamente como créditos de filme.",
            "Fade In": "Texto aparece gradualmente do transparente ao sólido.",
            "Fade Out": "Texto some gradualmente ao longo do slide.",
            "Typewriter (letra a letra)": "Texto digita-se letra por letra da esquerda para direita.",
            "Palavra por Palavra": "Cada palavra aparece no ritmo do WPM configurado.",
            "Slide Lateral (direita→centro)": "Texto entra pela direita com ease-out suave.",
            "Slide Lateral (esquerda→centro)": "Texto entra pela esquerda com ease-out suave.",
            "Zoom (cresce)": "Texto começa pequeno e cresce até tamanho normal.",
            "Pulso / Glow": "Texto pulsa em brilho — ideal para frequências e energia.",
        }

        st.markdown("""
        <div class="card cl">
        <b>🎬 Montagem Sincronizada com Legenda Inteligente</b><br>
        Envie imagens + áudio → a plataforma distribui os slides proporcionalmente
        à duração da música e sincroniza a legenda pelo tempo de leitura (WPM).
        </div>
        """, unsafe_allow_html=True)

        # ---- Upload de imagens e áudio ----
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            imgs_up = st.file_uploader(
                "📁 Imagens (ordem = ordem dos slides):",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True, key="mont_imgs",
                help="Selecione as imagens na ordem desejada de exibição."
            )
        with col_up2:
            audio_up = st.file_uploader(
                "🔊 Áudio da trilha (MP3/WAV/M4A):",
                type=["mp3", "wav", "m4a"], key="mont_audio",
                help="A duração deste áudio define o tempo total do vídeo."
            )

        if not imgs_up:
            st.info("👆 Envie pelo menos uma imagem para começar.")
            return

        # ---- Duração total e distribuição dos slides ----
        audio_bytes = None
        audio_ext = "mp3"
        dur_total = 0.0
        if audio_up:
            audio_bytes = audio_up.read()
            audio_ext = audio_up.name.rsplit(".", 1)[-1].lower()
            dur_total = _get_audio_duration_seconds(audio_bytes, audio_ext)
            st.success(f"🎵 Áudio detectado: **{dur_total:.1f}s** ({audio_up.name})")
        else:
            dur_total = st.number_input(
                "⏱️ Duração total do vídeo (s) — sem áudio:",
                min_value=5.0, max_value=600.0, value=60.0, step=5.0, key="mont_dur_manual"
            )

        n_imgs = len(imgs_up)
        secs_each = dur_total / n_imgs

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("🖼️ Imagens", n_imgs)
        mc2.metric("⏱️ Duração total", f"{dur_total:.1f}s")
        mc3.metric("📐 Seg/slide", f"{secs_each:.1f}s")
        mc4.metric("🎞️ FPS saída", "24")

        st.markdown("**📽️ Preview da sequência:**")
        thumb_cols = st.columns(min(6, n_imgs))
        for i, (col, f) in enumerate(zip(thumb_cols, imgs_up[:6])):
            img = Image.open(f)
            img.thumbnail((200, 113))
            col.image(img, caption=f"Slide {i+1}\n{secs_each:.1f}s", use_container_width=True)
        if n_imgs > 6:
            st.caption(f"... e mais {n_imgs - 6} imagem(ns).")

        st.markdown("---")

        # ---- Legenda sincronizada e intervalo personalizado ----
        st.markdown("### ✍️ Legenda Sincronizada")
        st.markdown("""
        <div class="card co" style="font-size:.88rem;">
        O texto abaixo será distribuído <b>proporcionalmente ao tempo de leitura</b>
        dentro do intervalo de tempo que você escolher (início e fim).
        </div>
        """, unsafe_allow_html=True)

        legenda_texto = st.text_area(
            "📝 Texto da legenda completa:",
            placeholder="Cole aqui o texto (pode conter timestamps como [10.0] frase) ...",
            height=150, key="mont_legenda",
            help="Se usar timestamps no formato '[inicio] texto', o sistema ignora WPM e usa esses tempos exatos."
        )

        col_wpm, col_vel = st.columns(2)
        with col_wpm:
            wpm = st.slider(
                "📖 Velocidade de leitura (WPM):",
                min_value=80, max_value=300, value=150, step=10, key="mont_wpm",
                help="Palavras por minuto. 150 = leitura normal. 100 = lenta. 200 = rápida. Ignorado se usar timestamps."
            )
        with col_vel:
            vel_label = "🐢 Lenta" if wpm < 110 else ("⚡ Rápida" if wpm > 190 else "🚶 Normal")
            st.markdown(f"<br><div class='card cg' style='text-align:center;padding:.6rem;'>"
                        f"<b>{vel_label}</b><br>{wpm} WPM</div>", unsafe_allow_html=True)

        st.markdown("#### ⏱️ Intervalo de exibição da legenda")
        col_int1, col_int2 = st.columns(2)
        with col_int1:
            legenda_start = st.number_input(
                "Início (s):", min_value=0.0, max_value=dur_total, value=0.0, step=0.5, key="leg_start",
                help="Momento em que a legenda começa a aparecer."
            )
        with col_int2:
            legenda_end = st.number_input(
                "Fim (s):", min_value=0.0, max_value=dur_total, value=dur_total, step=0.5, key="leg_end",
                help="Momento em que a legenda para de aparecer."
            )
        if legenda_start >= legenda_end:
            st.warning("⚠️ O início deve ser menor que o fim.")
            legenda_end = legenda_start + 1.0
        legenda_duration = legenda_end - legenda_start

        # ---- Processamento da legenda: timestamps ou WPM ----
        legenda_blocks_abs = []
        timestamp_pattern = re.compile(r'^\[\s*(\d+(?:\.\d+)?)\s*\]\s*(.*)$')
        lines = legenda_texto.strip().split('\n')
        has_timestamps = any(timestamp_pattern.match(line) for line in lines)

        if has_timestamps and legenda_texto.strip():
            # Modo manual: usar timestamps fornecidos pelo usuário
            blocks_raw = []
            for line in lines:
                match = timestamp_pattern.match(line)
                if match:
                    start = float(match.group(1))
                    text = match.group(2).strip()
                    if text:
                        blocks_raw.append((text, start, None))
            # Calcular fins: cada bloco vai até o próximo início ou até legenda_end
            for i in range(len(blocks_raw)):
                txt, start, _ = blocks_raw[i]
                end = blocks_raw[i+1][1] if i+1 < len(blocks_raw) else legenda_end
                if start < legenda_end:
                    legenda_blocks_abs.append((txt, start, min(end, legenda_end)))
            st.info(f"📌 Modo manual: {len(legenda_blocks_abs)} blocos com timestamps.")
        else:
            # Modo automático: divisão proporcional pelo WPM
            if legenda_texto.strip():
                blocks_rel = _split_text_by_time(legenda_texto.strip(), legenda_duration, wpm)
                legenda_blocks_abs = [(txt, legenda_start + t0, legenda_start + t1) for (txt, t0, t1) in blocks_rel]
                read_time = _calc_wpm_duration(legenda_texto.strip(), wpm)
                n_words = len(legenda_texto.split())
                st.markdown(f"""
                <div class="card cl" style="font-size:.85rem;margin:.5rem 0;">
                📊 <b>{n_words} palavras</b> → tempo de leitura estimado: <b>{read_time:.1f}s</b>
                &nbsp;|&nbsp; Distribuídas em <b>{len(legenda_blocks_abs)} blocos</b>
                &nbsp;|&nbsp; Intervalo escolhido: <b>{legenda_start:.1f}s → {legenda_end:.1f}s</b>
                {'&nbsp;⚠️ <b>Texto mais longo que o intervalo — será comprimido.</b>' if read_time > legenda_duration else '&nbsp;✅ Sincronização viável.'}
                </div>
                """, unsafe_allow_html=True)
            else:
                legenda_blocks_abs = []

        if legenda_blocks_abs:
            with st.expander("👁️ Preview dos blocos de legenda (primeiros 5)", expanded=False):
                for i, (blk, t0, t1) in enumerate(legenda_blocks_abs[:5]):
                    st.markdown(f"`{t0:.1f}s → {t1:.1f}s` — {blk}")
                if len(legenda_blocks_abs) > 5:
                    st.caption(f"... e mais {len(legenda_blocks_abs)-5} blocos.")

        st.markdown("---")

        # ---- Arte do texto (tipografia) e preview ao vivo ----
        st.markdown("### 🎨 Arte do Texto — Configuração Tipográfica")
        st.markdown("Abaixo, configure todos os aspectos da legenda. O preview é atualizado instantaneamente sobre a primeira imagem carregada.")

        font_names, font_paths = get_available_fonts()
        if not font_names:
            font_names = ["Padrão"]
            font_paths = {"Padrão": ""}

        with st.expander("🖋️ Fonte, Tamanho & Cor", expanded=True):
            tf_c1, tf_c2, tf_c3 = st.columns(3)
            with tf_c1:
                font_size = st.slider("Tamanho da fonte (px):", 18, 200, 48, key="tf_size",
                                      help="Tamanho em pixels. Recomendado entre 36 e 72 para 1280x720.")
                font_choice = st.selectbox("Fonte:", font_names, key="tf_font_choice")
                font_path = font_paths.get(font_choice, "")
            with tf_c2:
                font_color = st.color_picker("Cor do texto:", "#FFFFFF", key="tf_color")
                font_bold = st.checkbox("Negrito (simulado)", value=True, key="tf_bold")
                font_italic = st.checkbox("Itálico (não implementado)", value=False, key="tf_italic", disabled=True)
            with tf_c3:
                h_align = st.selectbox("Alinhamento horizontal:", ["Centro", "Esquerda", "Direita"], key="tf_halign")
                v_align = st.selectbox("Posição vertical:", ["Base", "Centro", "Topo"], key="tf_valign")

        with st.expander("🌑 Sombreamento & Contorno", expanded=True):
            sh_c1, sh_c2 = st.columns(2)
            with sh_c1:
                shadow = st.checkbox("✅ Sombra no texto", value=True, key="tf_shadow")
                shadow_color = st.color_picker("Cor da sombra:", "#000000", key="tf_shadow_color")
            with sh_c2:
                outline = st.checkbox("Contorno (outline)", value=False, key="tf_outline")
                outline_color = st.color_picker("Cor do contorno:", "#000000", key="tf_outline_color")
                outline_w = st.slider("Espessura do contorno:", 1, 12, 2, key="tf_outline_w")

        with st.expander("🟦 Caixa de fundo (legibilidade)", expanded=False):
            bg_c1, bg_c2 = st.columns(2)
            with bg_c1:
                bg_box = st.checkbox("Ativar caixa de fundo", value=False, key="tf_bgbox")
                bg_box_color = st.color_picker("Cor da caixa:", "#000000", key="tf_bgbox_color")
            with bg_c2:
                bg_box_alpha = st.slider("Opacidade da caixa (%):", 10, 100, 60, key="tf_bgbox_alpha",
                                         help="100 = totalmente opaco, 0 = transparente.")

        st.markdown("---")
        st.markdown("### 👁️ Preview ao Vivo (como ficará no vídeo)")
        preview_img = None
        if imgs_up:
            preview_img = Image.open(imgs_up[0]).convert("RGB")
            preview_img.thumbnail((640, 360), Image.LANCZOS)
            st.caption(f"Preview sobre a primeira imagem: **{imgs_up[0].name}** (redimensionado)")
        else:
            preview_img = Image.new("RGB", (640, 360), color=(30, 30, 50))
            st.caption("Nenhuma imagem carregada. Preview genérico.")

        texto_exemplo = legenda_texto.strip() if legenda_texto.strip() else "Texto de exemplo\nAqui você pode ver como ficará a legenda."
        if len(texto_exemplo) > 200:
            texto_exemplo = texto_exemplo[:200] + "..."

        try:
            preview_result = _render_text_on_image(
                preview_img.copy(),
                texto_exemplo,
                font_size=font_size,
                font_color=font_color,
                font_name=font_choice,
                font_path=font_path,
                h_align=h_align,
                v_align=v_align,
                shadow=shadow,
                shadow_color=shadow_color,
                bold=font_bold,
                italic=font_italic,
                outline=outline,
                outline_color=outline_color,
                outline_w=outline_w,
                bg_box=bg_box,
                bg_box_color=bg_box_color,
                bg_box_alpha=bg_box_alpha,
            )
            st.image(preview_result, caption="Preview estático (não animado) - resultado final similar", use_container_width=True)
        except Exception as e:
            st.error(f"Erro no preview: {e}")

        st.markdown("---")

        # ---- Timeline de animação da legenda (segmentos) ----
        st.markdown("### ⏱️ Timeline da Animação da Legenda")
        st.markdown("Defina intervalos de tempo onde a legenda será animada. Fora deles, a legenda fica estática.")

        if "text_animation_segments" not in st.session_state:
            st.session_state.text_animation_segments = []
        segments = st.session_state.text_animation_segments

        if segments:
            st.markdown("**Segmentos ativos:**")
            timeline_html = '<div class="timeline-bar" style="margin-bottom:10px;">'
            for seg in sorted(segments, key=lambda x: x["start"]):
                left = (seg["start"] / dur_total) * 100
                width = ((seg["end"] - seg["start"]) / dur_total) * 100
                timeline_html += f'<div class="timeline-segment" style="width:{width}%; left:{left}%; background:#a8ff3e;" title="{seg["type"]}: {seg["start"]:.1f}s-{seg["end"]:.1f}s">{seg["type"][0]}</div>'
            timeline_html += '</div>'
            st.markdown(timeline_html, unsafe_allow_html=True)

            for i, seg in enumerate(segments):
                cols = st.columns([2, 2, 1])
                cols[0].write(f"{seg['start']:.1f}s → {seg['end']:.1f}s")
                cols[1].write(seg['type'])
                if cols[2].button("✖️", key=f"del_anim_seg_{i}", help="Remover este segmento"):
                    segments.pop(i)
                    st.rerun()
        else:
            st.info("Nenhum segmento de animação definido. A legenda ficará estática durante todo o vídeo.")

        with st.expander("➕ Adicionar intervalo de animação", expanded=False):
            c1, c2 = st.columns(2)
            start = c1.number_input("Início (s)", 0.0, dur_total, 0.0, 0.5, key="anim_start",
                                    help="Momento em que a animação começa.")
            end = c2.number_input("Fim (s)", 0.0, dur_total, min(dur_total, start + 2.0), 0.5, key="anim_end",
                                  help="Momento em que a animação termina.")
            anim_choice = st.selectbox("Tipo de animação:", list(ANIM_OPTIONS.keys()), key="anim_type_choice")
            if st.button("Adicionar Segmento", key="add_anim_seg"):
                if start < end:
                    segments.append({"start": start, "end": end, "type": anim_choice})
                    st.rerun()
                else:
                    st.warning("O fim deve ser maior que o início.")

        # ---- Configurações gerais de vídeo ----
        st.markdown("### ⚙️ Configurações de Vídeo")
        st.markdown("#### 🎭 Animação da Legenda")
        anim_c1, anim_c2 = st.columns([2, 1])
        with anim_c1:
            anim_type = st.selectbox(
                "Tipo de animação (padrão se não houver segmentos):",
                list(ANIM_OPTIONS.keys()),
                key="mont_anim",
                help="Define como a legenda se move durante cada slide."
            )
        with anim_c2:
            st.markdown(f"<br><div class='card cl' style='font-size:.82rem;padding:.6rem;'>"
                        f"ℹ️ {ANIM_OPTIONS[anim_type]}</div>", unsafe_allow_html=True)

        st.markdown("---")
        vc1, vc2 = st.columns(2)
        with vc1:
            transition_frames = st.slider(
                "Frames de transição entre slides:", 0, 24, 8, key="mont_trans",
                help="0 = corte seco. 8-12 = dissolve suave. 24 = dissolve lento."
            )
        with vc2:
            modo_legenda = st.selectbox(
                "Modo de legenda:",
                ["Blocos proporcionais ao WPM", "Uma legenda por slide", "Sem legenda"],
                key="mont_modo_leg",
                help="Blocos WPM = legenda muda no tempo de leitura. Por slide = texto fixo por imagem."
            )

        slide_texts = []
        if modo_legenda == "Uma legenda por slide" and imgs_up:
            st.markdown("**📝 Texto por slide (opcional):**")
            for i in range(n_imgs):
                slide_texts.append(
                    st.text_input(f"Slide {i+1}:", key=f"slide_txt_{i}",
                                  placeholder=f"Legenda do slide {i+1}...")
                )

        # ---- Roteiro de montagem (TXT + texto com timestamps para copiar) ----
        st.markdown("---")
        st.markdown("### 📄 Roteiro de Montagem")

        if st.button("📄 Gerar Roteiro TXT", key="gen_rot", use_container_width=True,
                     help="Cria arquivo TXT com sequência, tempos e blocos de legenda."):
            rot = f"ROTEIRO DE MONTAGEM SINCRONIZADA — {st.session_state.project_name}\n"
            rot += f"Gerado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            rot += "=" * 65 + "\n\n"
            rot += f"Total imagens : {n_imgs}\n"
            rot += f"Duração total : {dur_total:.1f}s\n"
            rot += f"Seg/slide     : {secs_each:.1f}s\n"
            rot += f"WPM leitura   : {wpm}\n"
            rot += f"Intervalo legenda: {legenda_start:.1f}s → {legenda_end:.1f}s\n"
            rot += f"Transição     : {transition_frames} frames dissolve\n\n"
            rot += "SEQUÊNCIA DE SLIDES:\n" + "-" * 40 + "\n"
            t = 0.0
            for i, f in enumerate(imgs_up):
                rot += f"  Slide {i+1:02d}: {t:.1f}s → {t+secs_each:.1f}s | {f.name}\n"
                t += secs_each
            if legenda_blocks_abs and modo_legenda == "Blocos proporcionais ao WPM":
                rot += "\nBLOCOS DE LEGENDA (WPM sincronizado):\n" + "-" * 40 + "\n"
                for blk, t0, t1 in legenda_blocks_abs:
                    rot += f"  {t0:.1f}s → {t1:.1f}s : {blk}\n"
            rot += "\nCONFIGURAÇÃO TIPOGRÁFICA:\n" + "-" * 40 + "\n"
            rot += f"  Fonte: {font_choice} | Tamanho: {font_size}px | Cor: {font_color}\n"
            rot += f"  Alinhamento: {h_align} | Posição: {v_align}\n"
            rot += f"  Sombra: {'Sim' if shadow else 'Não'} | Contorno: {'Sim' if outline else 'Não'}\n"
            rot += f"  Caixa fundo: {'Sim' if bg_box else 'Não'}\n"
            rot += "\nINSTRUÇÕES EXPORTAÇÃO:\n" + "-" * 40 + "\n"
            rot += "  Resolução: 1280×720 (HD)\n"
            rot += "  Codec vídeo: H.264 | Codec áudio: AAC 192kbps\n"
            rot += "  Formato: MP4\n"

            st.download_button(
                "⬇️ Baixar Roteiro TXT", rot.encode("utf-8"),
                f"roteiro_{st.session_state.project_name}.txt",
                "text/plain", use_container_width=True, key="dl_rot"
            )
            st.success("✅ Roteiro gerado!")

        # Exibir texto com timestamps para copiar e colar (apenas se houver blocos e modo automático)
        if legenda_blocks_abs and modo_legenda == "Blocos proporcionais ao WPM" and not has_timestamps:
            st.markdown("#### 📋 Texto com timestamps (copie e cole no campo '📝 Texto da legenda completa')")
            texto_timestamp = format_legenda_com_timestamps(legenda_blocks_abs)
            st.text_area("Texto pronto para copiar:", value=texto_timestamp, height=150, key="timestamp_text")
            st.caption("Cole este texto no campo '📝 Texto da legenda completa' para usar os tempos manualmente (substitui o WPM).")

        # ---- Geração do vídeo final ----
        st.markdown("---")
        st.markdown("### 🎬 Gerar Vídeo MP4")

        if not audio_up:
            st.warning("⚠️ Para gerar o vídeo, envie um áudio acima. Sem áudio, apenas o roteiro TXT está disponível.")
        else:
            if st.button("🚀 GERAR VÍDEO SINCRONIZADO", type="primary",
                         key="gen_vid", use_container_width=True,
                         help="Processa imagens + legenda + áudio e exporta MP4."):

                text_cfg = {
                    "font_size": font_size,
                    "font_color": font_color,
                    "font_path": font_path,
                    "h_align": h_align,
                    "v_align": v_align,
                    "shadow": shadow,
                    "shadow_color": shadow_color,
                    "outline": outline,
                    "outline_color": outline_color,
                    "outline_w": outline_w,
                    "bg_box": bg_box,
                    "bg_box_color": bg_box_color,
                    "bg_box_alpha": bg_box_alpha,
                }

                slides_data = []
                if modo_legenda == "Blocos proporcionais ao WPM" and legenda_blocks_abs:
                    for i, f in enumerate(imgs_up):
                        t_slide_start = i * secs_each
                        t_slide_end = t_slide_start + secs_each
                        blks = [b[0] for b in legenda_blocks_abs if b[1] < t_slide_end and b[2] > t_slide_start]
                        txt = "\n".join(blks) if blks else ""
                        pil = Image.open(f)
                        slides_data.append((pil, secs_each, txt, text_cfg))
                elif modo_legenda == "Uma legenda por slide":
                    for i, f in enumerate(imgs_up):
                        pil = Image.open(f)
                        txt = slide_texts[i] if i < len(slide_texts) else ""
                        slides_data.append((pil, secs_each, txt, text_cfg))
                else:  # Sem legenda
                    for f in imgs_up:
                        pil = Image.open(f)
                        slides_data.append((pil, secs_each, "", text_cfg))

                out_path = os.path.join(st.session_state.working_dir, f"montagem_{st.session_state.project_name}.mp4")
                prog_bar = st.progress(0.0, text="Processando slides...")
                def progress_cb(v):
                    prog_bar.progress(min(v, 1.0), text=f"Renderizando... {int(v*100)}%")

                try:
                    with st.spinner("🎬 Gerando vídeo — pode levar alguns minutos..."):
                        _build_video_from_slides(
                            slides_data, audio_bytes, audio_ext,
                            fps=24, transition_frames=transition_frames,
                            output_path=out_path, progress_cb=progress_cb,
                            animation_segments=st.session_state.text_animation_segments,
                            default_anim_type=anim_type,
                            legenda_interval_start=legenda_start,
                            legenda_interval_end=legenda_end,
                        )

                    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                        prog_bar.progress(1.0, text="✅ Concluído!")
                        with open(out_path, "rb") as vf:
                            vid_bytes = vf.read()
                        st.session_state["_export_video"] = vid_bytes
                        st.success("🎉 Vídeo gerado com sucesso!")
                        st.video(vid_bytes)
                        st.download_button(
                            "⬇️ Baixar MP4",
                            vid_bytes,
                            f"montagem_{st.session_state.project_name}.mp4",
                            "video/mp4",
                            use_container_width=True, key="dl_vid_mont"
                        )
                    else:
                        st.error("❌ Falha ao gerar vídeo. Verifique se o FFmpeg está instalado.")
                        st.code("pip install imageio-ffmpeg", language="bash")

                except Exception as e:
                    st.error(f"❌ Erro durante geração: {e}")
                    st.code(traceback.format_exc(), language="python")
                                                    
def tab_export():
    st.markdown('<div class="stitle">📦 EXPORTAÇÃO & STATUS</div>', unsafe_allow_html=True)
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**📂 Arquivos disponíveis:**")
        items = []
        if st.session_state.processed_image:   items.append("✅ Imagem com efeitos aplicados")
        if st.session_state.base_image:         items.append("✅ Imagem / Frame base")
        if st.session_state.video_frame:         items.append("✅ Frame extraído do vídeo")
        if st.session_state.video_clip:          items.append(f"✅ Vídeo ({st.session_state.video_clip.duration:.1f}s)")
        if st.session_state.screenshot_data:     items.append("✅ Screenshot capturado")
        if st.session_state.transcribed_text:    items.append("✅ Transcrição de texto")
        if st.session_state.enhanced_prompts:    items.append("✅ Prompts de IA")
        if st.session_state._gif_data:           items.append("✅ GIF animado")
        if st.session_state._export_video:       items.append("✅ Vídeo exportado")
        for it in items:
            st.markdown(f"• {it}")
        if not items:
            st.info("Use as abas acima para criar conteúdo.")

    with col_r:
        st.markdown("**💾 Downloads rápidos:**")
        if st.session_state.processed_image:
            img = st.session_state.processed_image
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button("⬇️ PNG (alta qualidade)",
                    img_to_bytes(img,"PNG"),
                    f"{st.session_state.project_name}.png","image/png",
                    use_container_width=True, key="exp_png")
            with col_d2:
                st.download_button("⬇️ JPG (web)",
                    img_to_bytes(img,"JPEG",92),
                    f"{st.session_state.project_name}.jpg","image/jpeg",
                    use_container_width=True, key="exp_jpg")
        if st.session_state._gif_data:
            st.download_button("⬇️ GIF Animado",
                st.session_state._gif_data,
                f"{st.session_state.project_name}_anim.gif","image/gif",
                use_container_width=True, key="exp_gif")
        if st.session_state._export_video:
            st.download_button("⬇️ MP4 Editado",
                st.session_state._export_video,
                f"{st.session_state.project_name}_editado.mp4","video/mp4",
                use_container_width=True, key="exp_mp4")
        if st.session_state.transcribed_text:
            st.download_button("⬇️ Transcrição (TXT)",
                st.session_state.transcribed_text.encode("utf-8"),
                f"transcricao_{st.session_state.project_name}.txt","text/plain",
                use_container_width=True, key="exp_txt")
        if st.session_state.enhanced_prompts:
            st.download_button("⬇️ Prompts de IA (JSON)",
                json.dumps(st.session_state.enhanced_prompts, ensure_ascii=False, indent=2).encode(),
                f"prompts_{st.session_state.project_name}.json","application/json",
                use_container_width=True, key="exp_json")

    st.markdown("---")
    st.markdown("**📋 Status detalhado do sistema:**")
    status_items = [
        ("Versão",               "6.0 (Timeline + Guia)"),
        ("MoviePy (Vídeo)",      "✅ Ativo" if VIDEO_SUPPORT else "❌ pip install moviepy imageio-ffmpeg"),
        ("edge-tts (TTS)",       "✅ Ativo" if TTS_SUPPORT else "❌ pip install edge-tts"),
        ("Whisper (Transcrição)","✅ Ativo" if WHISPER_SUPPORT else "❌ pip install openai-whisper"),
        ("FFmpeg",               "✅ no PATH" if shutil.which("ffmpeg") else "⚠️ Não no PATH"),
        ("OpenCV",               "✅"),
        ("Pillow",               "✅"),
        ("NumPy",                "✅"),
    ]
    col_s1, col_s2 = st.columns(2)
    half = len(status_items)//2
    for i,(k,v) in enumerate(status_items):
        (col_s1 if i < half else col_s2).markdown(f"**{k}:** {v}")

    st.markdown("""
    <div class="card cg" style="margin-top:1rem;">
    <b>⚡ Instalação completa:</b><br>
    <code>pip install streamlit pillow numpy opencv-python requests moviepy imageio-ffmpeg edge-tts openai-whisper</code>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    render_header()
    render_sidebar()

    tabs = st.tabs([
        "🎞️ Editor de Vídeo",
        "🎨 Filtros & Molduras",
        "🎬 Animações & GIF",
        "📸 Screenshot",
        "🤖 IA & Áudio",
        "🎼 Montagem",
        "📦 Exportar",
        "📖 Ajuda",  # Nova aba de ajuda
    ])

    with tabs[0]: tab_video()
    with tabs[1]: tab_filtros()
    with tabs[2]: tab_animacoes()
    with tabs[3]: tab_screenshot()
    with tabs[4]: tab_ia_audio()
    with tabs[5]: tab_montagem()
    with tabs[6]: tab_export()
    with tabs[7]: tab_ajuda()  # Renderiza a nova aba de ajuda

    st.markdown("""
    <div style="text-align:center;padding:1.5rem;margin-top:2rem;
                border-top:1px solid rgba(0,229,255,.12);
                font-family:'JetBrains Mono',monospace;font-size:.72rem;
                color:rgba(107,114,128,.6);">
      STUDIO PRO CREATOR AI v6.0 • φ=1.618 • MARC=0.54 • JUBILO=0.45 •
      <i>Não sou o Nada e não sou o Tudo. Sou o Trajeto.</i>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
