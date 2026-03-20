import streamlit as st
import streamlit.components.v1 as components
import subprocess
import os
import json
import tempfile
import numpy as np
from datetime import datetime, timedelta
import base64
import time
import warnings
from PIL import Image
import io
import sys
import wave
import struct
from typing import Optional, Dict, List, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
import re
import math
import shutil
from pathlib import Path
import threading
import queue
import uuid
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

warnings.filterwarnings('ignore')

# ==========================
# CLASSES E ESTRUTURAS DE DADOS COMPLETAS
# ==========================
@dataclass
class VoiceProfile:
    """Perfil de voz para TTS com edge-tts"""
    name: str
    language: str
    voice_code: str
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    voice_type: str = "neural"
    
    def to_dict(self):
        return asdict(self)

@dataclass
class VideoPart:
    """Partição de vídeo para processamento em partes"""
    part_id: int
    input_path: str
    output_path: str
    start_time: float
    end_time: float
    duration: float
    size_mb: float
    status: str = "pending"
    edited: bool = False
    audio_path: str = ""
    text_transcript: str = ""
    ai_prompts: Dict[str, str] = field(default_factory=dict)
    effects: List[str] = field(default_factory=list)
    thumbnail: str = ""
    
    def get_info(self):
        return {
            'id': self.part_id,
            'duration': self.duration,
            'start': self.start_time,
            'end': self.end_time,
            'status': self.status
        }

@dataclass
class AudioSegmentData:
    """Segmento de áudio para análise"""
    id: str
    start_time: float
    end_time: float
    duration: float
    text: str = ""
    theme: str = ""
    keywords: List[str] = field(default_factory=list)
    sentiment: str = ""
    volume_level: float = 0.0
    prompts: Dict[str, str] = field(default_factory=dict)

@dataclass
class VideoAnalysis:
    """Análise completa do vídeo - VERSÃO ESTENDIDA"""
    themes: List[str]
    key_moments: List[Dict]
    improvement_suggestions: List[str]
    ai_prompts: Dict[str, str]
    transcript_summary: str
    mood: str = "neutral"
    # Atributos estendidos para análise aprimorada
    target_audience: Dict[str, Any] = field(default_factory=dict)
    optimized_keywords: List[str] = field(default_factory=list)
    sentiment_scores: Dict[str, float] = field(default_factory=dict)
    estimated_engagement: int = 0
    narrative_structure: Dict[str, Any] = field(default_factory=dict)
    theme_scores: Dict[str, float] = field(default_factory=dict)

# ==========================
# NOVAS CLASSES PARA ESTRUTURA NARRATIVA
# ==========================
@dataclass
class NarrativeAct:
    """Representa um ato da narrativa"""
    number: int
    title: str
    description: str
    emotional_tone: str  # ex: "misterioso", "energético", "reflexivo"
    visual_style: str    # ex: "dark", "vibrante", "suave"
    target_duration: float  # duração desejada em segundos (opcional)
    text_content: str = ""  # roteiro do ato
    audio_path: str = ""
    video_path: str = ""
    prompts: Dict[str, str] = field(default_factory=dict)  # prompts gerados
    analysis: Optional[VideoAnalysis] = None

@dataclass
class NarrativeTemplate:
    """Template de estrutura narrativa (ex: 4 atos)"""
    name: str
    acts: List[NarrativeAct]
    total_duration: float = 0.0
    description: str = ""

# ==========================
# CONFIGURAÇÕES E CONSTANTES
# ==========================
# Perfis de voz atualizados com edge-tts
DEFAULT_VOICE_PROFILES = {
    "masculina_padrao": VoiceProfile("Masculina Padrão", "pt-BR", "pt-BR-AntonioNeural", 1.0, 1.0, 1.0, "neural"),
    "feminina_suave": VoiceProfile("Feminina Suave", "pt-BR", "pt-BR-FranciscaNeural", 0.9, 1.2, 0.9, "neural"),
    "masculina_profunda": VoiceProfile("Masculina Profunda", "pt-BR", "pt-BR-DonatoNeural", 0.8, 0.8, 1.1, "neural"),
    "feminina_energica": VoiceProfile("Feminina Energética", "pt-BR", "pt-BR-BrendaNeural", 1.2, 1.1, 1.0, "neural"),
    "narrador_noticias": VoiceProfile("Narrador Notícias", "pt-BR", "pt-BR-FabioNeural", 1.0, 1.0, 1.0, "neural"),
    "crianca_animada": VoiceProfile("Criança Animada", "pt-BR", "pt-BR-LeilaNeural", 1.3, 1.5, 0.8, "neural"),
    "masculina_young": VoiceProfile("Masculina Jovem", "pt-BR", "pt-BR-JulioNeural", 1.1, 1.1, 1.0, "neural"),
    "feminina_calm": VoiceProfile("Feminina Calma", "pt-BR", "pt-BR-ManuelaNeural", 0.9, 1.0, 0.9, "neural"),
}

VOICE_FALLBACK_MAPPING = {
    "pt-BR-DonatoNeural": "pt-BR-AntonioNeural",  # Masculina Profunda -> Masculina Padrão
    "pt-BR-BrendaNeural": "pt-BR-FranciscaNeural", # Feminina Energética -> Feminina Suave
    "pt-BR-FabioNeural": "pt-BR-AntonioNeural",    # Narrador Notícias -> Masculina Padrão
    "pt-BR-LeilaNeural": "pt-BR-FranciscaNeural",  # Criança Animada -> Feminina Suave
    "pt-BR-JulioNeural": "pt-BR-AntonioNeural",    # Masculina Jovem -> Masculina Padrão
    "pt-BR-ManuelaNeural": "pt-BR-FranciscaNeural" # Feminina Calma -> Feminina Suave
}

# Efeitos de áudio aprimorados
AUDIO_EFFECTS = {
    "eco": {
        "name": "Eco",
        "description": "Adiciona efeito de eco",
        "params": {"intensity": 0.3, "delay": 0.15, "feedback": 0.4}
    },
    "reverb": {
        "name": "Reverberação",
        "description": "Simula ambientes acústicos",
        "params": {"room_size": 0.5, "damping": 0.5, "wet_level": 0.3}
    },
    "equalizador": {
        "name": "Equalizador",
        "description": "Ajusta frequências específicas",
        "params": {"bass": 1.0, "mid": 1.0, "treble": 1.0}
    },
    "compressor": {
        "name": "Compressor",
        "description": "Normaliza volumes altos e baixos",
        "params": {"threshold": -20, "ratio": 4.0, "attack": 5, "release": 50}
    },
    "noise_reduction": {
        "name": "Redução de Ruído",
        "description": "Remove ruído de fundo",
        "params": {"intensity": 0.7, "sensitivity": 0.5}
    },
    "chorus": {
        "name": "Coro",
        "description": "Cria efeito de múltiplas vozes",
        "params": {"depth": 0.5, "rate": 1.0, "mix": 0.5}
    }
}

# Efeitos de vídeo
VIDEO_EFFECTS = {
    "normal": {"name": "Normal", "filter": "null"},
    "preto_e_branco": {"name": "Preto e Branco", "filter": "colorchannelmixer=.299:.587:.114"},
    "sepia": {"name": "Sépia", "filter": "colorchannelmixer=.393:.769:.189:.349:.686:.168:.272:.534:.131"},
    "vintage": {"name": "Vintage", "filter": "curves=preset=vintage"},
    "alto_contraste": {"name": "Alto Contraste", "filter": "eq=contrast=1.5:brightness=-0.05"},
    "blur_suave": {"name": "Blur Suave", "filter": "boxblur=5:1"},
    "sharpen": {"name": "Nitidez", "filter": "unsharp=5:5:1.0"},
    "hdr": {"name": "HDR", "filter": "eq=gamma=1.5:contrast=1.2:saturation=1.3"},
    "cinematic": {"name": "Cinematográfico", "filter": "colorbalance=rs=0.3:gs=0.2:bs=0.1"},
    "glitch": {"name": "Glitch", "filter": "glitch=amount=10"},
    "vignette": {"name": "Vignette", "filter": "vignette=angle=30:strength=0.5"}
}

# Temas para IA
THEMES_FOR_IA = {
    "educacao": {
        "name": "Educação",
        "prompt_templates": {
            "imagem": "Crie uma imagem educativa sobre {topic} com cores vibrantes",
            "audio": "Narração educativa clara sobre {topic}",
            "texto": "Texto explicativo sobre {topic} para aprendizado",
            "video": "Vídeo educativo sobre {topic} com animações explicativas",
            "storyboard": "Sequência visual educativa sobre {topic}"
        }
    },
    "marketing": {
        "name": "Marketing",
        "prompt_templates": {
            "imagem": "Imagem impactante para campanha de marketing sobre {topic}",
            "audio": "Narração persuasiva para comercial sobre {topic}",
            "texto": "Texto persuasivo para campanha de marketing sobre {topic}",
            "video": "Vídeo promocional sobre {topic} com call-to-action",
            "storyboard": "Storyboard para comercial sobre {topic}"
        }
    },
    "entretenimento": {
        "name": "Entretenimento",
        "prompt_templates": {
            "imagem": "Cena divertida e envolvente sobre {topic}",
            "audio": "Narração animada e divertida sobre {topic}",
            "texto": "Texto entretenimento sobre {topic} com humor",
            "video": "Vídeo de entretenimento sobre {topic} com ritmo dinâmico",
            "storyboard": "Sequência divertida sobre {topic}"
        }
    },
    "noticias": {
        "name": "Notícias",
        "prompt_templates": {
            "imagem": "Imagem séria e informativa sobre {topic}",
            "audio": "Narração jornalística sobre {topic}",
            "texto": "Texto informativo sobre {topic} em estilo jornalístico",
            "video": "Vídeo informativo sobre {topic} com gráficos explicativos",
            "storyboard": "Storyboard jornalístico sobre {topic}"
        }
    },
    "tecnologia": {
        "name": "Tecnologia",
        "prompt_templates": {
            "imagem": "Imagem futurista sobre {topic} com elementos tech",
            "audio": "Narração tecnológica sobre {topic} com efeitos sonoros modernos",
            "texto": "Texto técnico explicativo sobre {topic}",
            "video": "Vídeo tecnológico sobre {topic} com animações 3D",
            "storyboard": "Sequência tecnológica sobre {topic}"
        }
    }
}

# Templates narrativos pré-definidos
NARRATIVE_TEMPLATES = {
    "4_atos_alma_fluxo": NarrativeTemplate(
        name="Jornada do Observador (4 Atos)",
        acts=[
            NarrativeAct(1, "O Convite", "Apresentação pessoal e visão", "misterioso", "dark", 120),
            NarrativeAct(2, "As Ferramentas", "Demonstração dos módulos", "energético", "vibrante", 300),
            NarrativeAct(3, "O Coração", "Filosofia e propósito", "reflexivo", "suave", 240),
            NarrativeAct(4, "A Realidade", "Transparência e chamada para ação", "íntimo", "clean", 120),
        ],
        description="Estrutura em 4 atos usada no lançamento da Alma Fluxo"
    ),
    "3_atos_classico": NarrativeTemplate(
        name="Clássico (3 Atos)",
        acts=[
            NarrativeAct(1, "Introdução", "Apresentação do problema", "informativo", "neutro", 60),
            NarrativeAct(2, "Desenvolvimento", "Solução e benefícios", "entusiasmado", "dinâmico", 180),
            NarrativeAct(3, "Conclusão", "Resumo e CTA", "convincente", "clean", 60),
        ],
        description="Estrutura narrativa tradicional"
    )
}

# Mapeamento tom -> chave do perfil de voz
TONE_TO_VOICE = {
    "Informativo": "masculina_padrao",
    "Inspirador": "feminina_suave",
    "Empolgante": "masculina_profunda",
    "Urgente": "narrador_noticias",
    "Misterioso": "masculina_profunda",
    "Reflexivo": "feminina_calm",
    "Íntimo": "feminina_suave",
    "Convincente": "narrador_noticias",
    "Entusiasmado": "feminina_energica",
    # Adicie outros conforme necessário
}

# Biblioteca de músicas (caminhos para arquivos MP3)
MUSIC_LIBRARY = {
    "Informativo": "assets/music/informativo.mp3",
    "Inspirador": "assets/music/inspirador.mp3",
    "Empolgante": "assets/music/empolgante.mp3",
    "Urgente": "assets/music/urgente.mp3",
    "Misterioso": "assets/music/misterioso.mp3",
    "Reflexivo": "assets/music/reflexivo.mp3",
    "default": "assets/music/default.mp3",
}

# ==========================
# SISTEMA DE DEPENDÊNCIAS
# ==========================
def check_and_install_dependencies():
    """Verifica e instala todas as dependências necessárias"""
    dependencies = {
        "ffmpeg": False,
        "edge_tts": False,
        "whisper": False,
        "pydub": False,
        "moviepy": False,
        "speech_recognition": False,
    }
    
    # Verifica FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        dependencies["ffmpeg"] = True
    except:
        st.warning("FFmpeg não encontrado. Algumas funcionalidades serão limitadas.")
    
    # Instala pacotes Python
    packages_to_install = []
    
    try:
        import edge_tts
        dependencies["edge_tts"] = True
    except ImportError:
        packages_to_install.append("edge-tts")
    
    try:
        import whisper
        dependencies["whisper"] = True
    except ImportError:
        packages_to_install.append("openai-whisper")
    
    try:
        from pydub import AudioSegment
        dependencies["pydub"] = True
    except ImportError:
        packages_to_install.append("pydub")
    
    try:
        import moviepy.editor as mp
        dependencies["moviepy"] = True
    except ImportError:
        packages_to_install.append("moviepy")
    
    try:
        import speech_recognition as sr
        dependencies["speech_recognition"] = True
    except ImportError:
        packages_to_install.append("SpeechRecognition")
    
    # Tenta instalar pacotes faltantes
    if packages_to_install:
        with st.spinner("Instalando dependências necessárias..."):
            for package in packages_to_install:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
                    dependencies[package.split("-")[0] if "-" in package else package] = True
                except:
                    st.warning(f"Não foi possível instalar {package}")
    
    return dependencies

# ==========================
# CONFIGURAÇÃO DO STREAMLIT
# ==========================
st.set_page_config(
    page_title="Studio Pro Editor AI - Edição Completa",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Personalizado Completo (mantido igual ao original)
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        border-left: 5px solid #4cc9f0;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        text-shadow: 0 2px 10px rgba(76,201,240,0.3);
    }
    .main-header p {
        color: #a0a0a0;
        margin: 0.5rem 0 0;
        font-size: 1rem;
    }
    .status-indicator {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .status-ready {
        background: #00b894;
        color: white;
    }
    .status-processing {
        background: #fdcb6e;
        color: #2d3436;
    }
    .status-missing {
        background: #d63031;
        color: white;
    }
    .timeline-container {
        background: #0f0f1a;
        border-radius: 12px;
        padding: 2rem 1rem;
        margin: 1rem 0;
        position: relative;
        height: 100px;
        border: 1px solid #2d2d3a;
    }
    .timeline-segment {
        position: absolute;
        height: 60px;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        cursor: pointer;
        transition: transform 0.2s;
        border: 1px solid rgba(255,255,255,0.2);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .timeline-segment:hover {
        transform: translateY(-5px);
        z-index: 10;
    }
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(76,201,240,0.3);
    }
    div[data-testid="stExpander"] {
        background: linear-gradient(135deg, #1e1e2e 0%, #1a1a2a 100%);
        border: 1px solid #2d2d3a;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #0f0f1a;
        padding: 0.5rem;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        background: transparent;
        color: #a0a0a0;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #4cc9f0 0%, #4361ee 100%);
        color: white !important;
    }
    .stProgress > div > div {
        background: linear-gradient(90deg, #4cc9f0, #4361ee);
        border-radius: 4px;
    }
    .stSelectbox label, .stMultiselect label {
        color: #a0a0a0 !important;
    }
    .stTextArea textarea {
        background: #1e1e2e;
        color: white;
        border: 1px solid #2d2d3a;
        border-radius: 8px;
    }
    .stTextInput input {
        background: #1e1e2e;
        color: white;
        border: 1px solid #2d2d3a;
        border-radius: 8px;
    }
    .stSlider div[data-baseweb="slider"] {
        background: #2d2d3a;
    }
    .stSlider div[role="slider"] {
        background: #4cc9f0;
    }
    hr {
        border-color: #2d2d3a;
    }
    .stAlert {
        background: rgba(76,201,240,0.1);
        border: 1px solid rgba(76,201,240,0.2);
        border-radius: 8px;
        color: white;
    }
    .stAlert [data-baseweb="notification"] {
        background: transparent;
    }
    .stInfo {
        background: rgba(76,201,240,0.15);
        border-left: 4px solid #4cc9f0;
    }
    .stWarning {
        background: rgba(253,203,110,0.15);
        border-left: 4px solid #fdcb6e;
    }
    .stError {
        background: rgba(214,48,49,0.15);
        border-left: 4px solid #d63031;
    }
    .stSuccess {
        background: rgba(0,184,148,0.15);
        border-left: 4px solid #00b894;
    }
</style>
""", unsafe_allow_html=True)

# ==========================
# INICIALIZAÇÃO DO ESTADO
# ==========================
def initialize_state():
    """Inicializa todos os estados da sessão"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        
        # Estados principais
        defaults = {
            # Projeto
            'project_name': f'Projeto_{datetime.now().strftime("%Y%m%d_%H%M")}',
            'project_id': str(uuid.uuid4()),
            
            # Arquivos
            'uploaded_video': None,
            'uploaded_audio': None,
            'video_path': '',
            'audio_path': '',
            'working_dir': tempfile.mkdtemp(prefix='studio_pro_'),
            
            # Informações de mídia
            'video_info': {},
            'audio_info': {},
            
            # Partições
            'video_parts': [],
            'selected_part_index': 0,
            'is_partitioned': False,
            
            # Transcrição e textos
            'transcribed_text': '',
            'text_segments': [],
            'tts_text': '',
            
            # Configurações
            'selected_voice': 'masculina_padrao',
            'voice_settings': {'speed': 1.0, 'pitch': 1.0, 'volume': 1.0},
            'audio_effects': [],
            'video_effects': [],
            
            # IA e análise
            'video_analysis': None,
            'ai_prompts': {},
            'selected_themes': [],
            
            # Processamento
            'processing': {
                'status': 'idle',
                'progress': 0,
                'message': '',
                'current_task': '',
                'total_tasks': 0
            },
            
            # Dependências
            'dependencies': check_and_install_dependencies(),
            
            # Interface
            'current_tab': 'upload',
            'show_help': True,
            'auto_mode': True,
            
            # Exportação
            'export_queue': [],
            'export_preset': 'youtube_1080p',
            
            # Análise de vídeo
            'video_analysis_complete': False,
            'enhanced_prompts': {},
            
            # Narrativa (novo)
            'narrative_template': None,
            'narrative_acts': [],
            'conversation_segments': [],
        }
        
        # Inicializa todos os estados
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

# ==========================
# FUNÇÕES DE PROCESSAMENTO DE VÍDEO (mantidas)
# ==========================
def get_media_info(file_path: str, media_type: str = 'video') -> Dict:
    try:
        if not os.path.exists(file_path):
            return {}
            
        if media_type == 'video':
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
        else:  # audio
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                file_path
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {}
        
        info = json.loads(result.stdout)
        
        if media_type == 'video':
            video_stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video'), {})
            audio_stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'audio'), {})
            
            duration = float(info.get('format', {}).get('duration', 0))
            size = int(info.get('format', {}).get('size', 0))
            
            return {
                'duration': duration,
                'size_bytes': size,
                'size_mb': size / (1024 * 1024),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'resolution': f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                'video_codec': video_stream.get('codec_name', 'unknown'),
                'audio_codec': audio_stream.get('codec_name', 'unknown'),
                'bitrate': info.get('format', {}).get('bit_rate', '0'),
                'format': info.get('format', {}).get('format_name', 'unknown')
            }
        else:
            duration = float(info.get('format', {}).get('duration', 0))
            size = int(info.get('format', {}).get('size', 0))
            
            return {
                'duration': duration,
                'size_bytes': size,
                'size_mb': size / (1024 * 1024),
                'bitrate': info.get('format', {}).get('bit_rate', '0'),
                'format': info.get('format', {}).get('format_name', 'unknown'),
                'sample_rate': next((s.get('sample_rate', '0') for s in info.get('streams', []) if s.get('codec_type') == 'audio'), '0')
            }
    
    except Exception as e:
        st.error(f"Erro ao obter informações: {str(e)}")
        return {}

def split_video_into_parts(video_path: str, part_duration: int = 60) -> List[VideoPart]:
    try:
        info = get_media_info(video_path, 'video')
        if not info or info['duration'] == 0:
            return []
        
        total_duration = info['duration']
        num_parts = math.ceil(total_duration / part_duration)
        parts = []
        
        st.session_state.processing['total_tasks'] = num_parts
        st.session_state.processing['current_task'] = "Dividindo vídeo"
        st.session_state.processing['status'] = 'processing'
        
        with st.spinner(f'Dividindo vídeo em {num_parts} partes...'):
            progress_bar = st.progress(0)
            
            for i in range(num_parts):
                start_time = i * part_duration
                end_time = min((i + 1) * part_duration, total_duration)
                duration = end_time - start_time
                
                part_output_path = os.path.join(st.session_state.working_dir, f"part_{i+1:03d}.mp4")
                
                cmd = [
                    'ffmpeg', '-i', video_path,
                    '-ss', str(start_time),
                    '-to', str(end_time),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-strict', 'experimental',
                    part_output_path,
                    '-y'
                ]
                
                try:
                    subprocess.run(cmd, capture_output=True, check=True)
                    
                    part = VideoPart(
                        part_id=i + 1,
                        input_path=video_path,
                        output_path=part_output_path,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        size_mb=(duration / total_duration) * info['size_mb']
                    )
                    parts.append(part)
                    
                except subprocess.CalledProcessError as e:
                    st.warning(f"Erro ao criar parte {i+1}: {e.stderr[:200]}")
                    part = VideoPart(
                        part_id=i + 1,
                        input_path=video_path,
                        output_path='',
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        size_mb=0,
                        status='error'
                    )
                    parts.append(part)
                
                progress = (i + 1) / num_parts
                progress_bar.progress(progress)
                st.session_state.processing['progress'] = progress * 100
        
        progress_bar.empty()
        st.session_state.processing['status'] = 'completed'
        st.session_state.processing['message'] = f'Vídeo dividido em {num_parts} partes'
        
        return parts
    
    except Exception as e:
        st.error(f"Erro ao dividir vídeo: {str(e)}")
        traceback.print_exc()
        return []

def extract_audio_from_video(video_path: str, output_path: str = None) -> str:
    try:
        if not os.path.exists(video_path):
            st.error("Vídeo não encontrado")
            return ""
        
        if output_path is None:
            output_path = os.path.join(st.session_state.working_dir, "extracted_audio.mp3")
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-q:a', '0', '-map', 'a',
            output_path, '-y'
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode == 0:
            return output_path
        else:
            st.error(f"Erro ao extrair áudio: {process.stderr[:200]}")
            return ""
    
    except Exception as e:
        st.error(f"Erro: {str(e)}")
        traceback.print_exc()
        return ""

def apply_video_effect(input_path: str, effect_name: str, output_path: str = None) -> str:
    try:
        if not os.path.exists(input_path):
            return input_path
            
        if output_path is None:
            output_path = os.path.join(st.session_state.working_dir, f"effected_{os.path.basename(input_path)}")
        
        effect = VIDEO_EFFECTS.get(effect_name, VIDEO_EFFECTS['normal'])
        filter_complex = effect['filter']
        
        if filter_complex == 'null':
            shutil.copy2(input_path, output_path)
        else:
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', filter_complex,
                '-c:a', 'copy',
                output_path, '-y'
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
        
        return output_path
    
    except Exception as e:
        st.error(f"Erro ao aplicar efeito: {str(e)}")
        traceback.print_exc()
        return input_path

# ==========================
# FUNÇÕES DE ÁUDIO E TEXTO (mantidas)
# ==========================
def transcribe_audio_with_whisper(audio_path: str) -> str:
    try:
        if not os.path.exists(audio_path):
            return "❌ Arquivo de áudio não encontrado"
        
        try:
            import whisper
        except ImportError:
            st.warning("Whisper não está disponível. Tentando instalar...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "openai-whisper", "--quiet"])
                import whisper
            except:
                return "❌ Não foi possível instalar Whisper. Use: pip install openai-whisper"
        
        st.session_state.processing['status'] = 'processing'
        st.session_state.processing['message'] = 'Transcrevendo áudio...'
        
        with st.spinner("Transcrevendo áudio com Whisper..."):
            progress_bar = st.progress(0)
            
            try:
                model = whisper.load_model("base")
                progress_bar.progress(0.3)
                
                result = model.transcribe(audio_path, language='pt', fp16=False)
                progress_bar.progress(1.0)
                
                st.session_state.processing['status'] = 'completed'
                st.session_state.processing['message'] = 'Transcrição concluída!'
                
                return result['text']
                
            except Exception as e:
                return f"❌ Erro na transcrição: {str(e)}"
            finally:
                progress_bar.empty()
    
    except Exception as e:
        return f"❌ Erro: {str(e)}"

def text_to_speech_edge(text: str, voice_profile: VoiceProfile, output_path: str = None) -> Tuple[bool, str]:
    try:
        if output_path is None:
            output_path = os.path.join(st.session_state.working_dir, f"tts_{uuid.uuid4().hex[:8]}.mp3")
        
        text = re.sub(r'\s+', ' ', text.strip())
        if not text:
            return False, "Texto vazio"
        
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        try:
            import edge_tts
            import asyncio
            
            original_voice = voice_profile.voice_code
            voice = original_voice
            
            if original_voice in VOICE_FALLBACK_MAPPING:
                voice_to_try = [original_voice, VOICE_FALLBACK_MAPPING[original_voice]]
            else:
                voice_to_try = [original_voice]
            
            speed = float(voice_profile.speed)
            rate_percent = int((speed - 1.0) * 100)
            rate_percent = max(-50, min(100, rate_percent))
            
            rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"
            
            success = False
            last_error = None
            
            for current_voice in voice_to_try:
                try:
                    communicate = edge_tts.Communicate(
                        text=text,
                        voice=current_voice,
                        rate=rate_str
                    )
                    
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(communicate.save(output_path))
                        loop.close()
                    except RuntimeError:
                        import nest_asyncio
                        nest_asyncio.apply()
                        asyncio.run(communicate.save(output_path))
                    
                    success = True
                    
                    if current_voice != original_voice:
                        st.info(f"Voz '{voice_profile.name}' não disponível. Usando voz alternativa.")
                    
                    break
                    
                except Exception as voice_error:
                    last_error = voice_error
                    continue
            
            if not success:
                return False, f"Todas as vozes falharam: {str(last_error)}"
            
            temp_path = output_path
            
            if voice_profile.volume != 1.0:
                adjusted_path = output_path.replace('.mp3', '_vol.mp3')
                if adjust_audio_volume(temp_path, adjusted_path, voice_profile.volume):
                    temp_path = adjusted_path
            
            if voice_profile.pitch != 1.0:
                final_path = output_path.replace('.mp3', '_final.mp3')
                if adjust_audio_pitch(temp_path, final_path, voice_profile.pitch):
                    output_path = final_path
                elif temp_path != output_path:
                    shutil.copy2(temp_path, output_path)
            elif temp_path != output_path:
                shutil.copy2(temp_path, output_path)
            
            if os.path.exists(temp_path) and temp_path != output_path:
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            return True, output_path
            
        except ImportError:
            try:
                from gtts import gTTS
                
                st.info("Usando gTTS como fallback...")
                
                slow = speed < 0.8
                tts = gTTS(text=text, lang='pt', slow=slow)
                tts.save(output_path)
                
                if voice_profile.volume != 1.0:
                    adjust_audio_volume(output_path, output_path, voice_profile.volume)
                
                return True, output_path
                
            except ImportError:
                return False, "Instale edge-tts: pip install edge-tts"
            
        except Exception as e:
            error_msg = str(e)
            if "rate" in error_msg.lower():
                try:
                    import edge_tts
                    import asyncio
                    
                    communicate = edge_tts.Communicate(
                        text=text,
                        voice=voice_profile.voice_code
                    )
                    
                    asyncio.run(communicate.save(output_path))
                    return True, output_path
                except:
                    return False, f"Erro ajustado: {error_msg[:100]}"
            return False, f"Erro no TTS: {error_msg[:100]}"
    
    except Exception as e:
        return False, f"Erro geral: {str(e)}"

def adjust_audio_pitch(input_path: str, output_path: str, pitch: float) -> bool:
    try:
        if pitch == 1.0:
            if input_path != output_path:
                shutil.copy2(input_path, output_path)
            return True
        
        if not os.path.exists(input_path):
            return False
        
        atempo = 1.0 / pitch
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-filter:a', f'atempo={atempo:.2f},asetrate=44100*{pitch:.2f},aresample=44100',
            output_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    except Exception as e:
        st.error(f"Erro ao ajustar pitch: {str(e)}")
        return False

def test_all_voices():
    test_text = "Olá, este é um teste de voz."
    working_voices = []
    non_working_voices = []
    
    st.info("Testando todas as vozes...")
    
    for voice_id, voice_profile in DEFAULT_VOICE_PROFILES.items():
        try:
            success, result = text_to_speech_edge(test_text, voice_profile)
            if success:
                working_voices.append(voice_profile.name)
                st.success(f"✅ {voice_profile.name} - FUNCIONA")
            else:
                non_working_voices.append(voice_profile.name)
                st.warning(f"❌ {voice_profile.name} - NÃO FUNCIONA: {result[:50]}")
        except Exception as e:
            non_working_voices.append(voice_profile.name)
            st.warning(f"❌ {voice_profile.name} - ERRO: {str(e)[:50]}")
    
    return working_voices, non_working_voices

def adjust_audio_volume(input_path: str, output_path: str, volume: float) -> bool:
    try:
        if volume == 1.0:
            if input_path != output_path:
                shutil.copy2(input_path, output_path)
            return True
        
        if not os.path.exists(input_path):
            return False
        
        if volume > 0:
            db = 20 * math.log10(volume)
        else:
            db = -96
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-filter:a', f'volume={db}dB',
            output_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    except Exception as e:
        st.error(f"Erro ao ajustar volume: {str(e)}")
        return False

def segment_text_by_time(text: str, audio_duration: float, num_segments: int = 10) -> List[Dict]:
    words = text.split()
    total_words = len(words)
    
    if total_words == 0:
        return []
    
    segments = []
    words_per_segment = max(1, total_words // num_segments)
    
    for i in range(num_segments):
        start_idx = i * words_per_segment
        end_idx = min((i + 1) * words_per_segment, total_words)
        
        if start_idx >= total_words:
            break
        
        segment_text = ' '.join(words[start_idx:end_idx])
        time_per_segment = audio_duration / num_segments
        
        segments.append({
            'id': i + 1,
            'start_time': i * time_per_segment,
            'end_time': (i + 1) * time_per_segment,
            'duration': time_per_segment,
            'text': segment_text,
            'word_count': end_idx - start_idx
        })
    
    return segments

# ==========================
# FUNÇÕES DE IA E ANÁLISE DE VÍDEO (mantidas)
# ==========================
def analyze_text_for_themes(text: str) -> Dict:
    themes_keywords = {
        'educação': ['aprender', 'ensinar', 'escola', 'universidade', 'estudar', 'professor', 'aluno', 'curso', 'aula', 'conhecimento'],
        'tecnologia': ['computador', 'software', 'hardware', 'programação', 'aplicativo', 'internet', 'digital', 'inovação', 'startup', 'robótica'],
        'saúde': ['médico', 'hospital', 'doença', 'tratamento', 'saúde', 'exercício', 'bem-estar', 'nutrição', 'fitness', 'medicina'],
        'negócios': ['empresa', 'negócio', 'lucro', 'venda', 'mercado', 'investimento', 'empreendedor', 'gestão', 'finanças', 'estratégia'],
        'entretenimento': ['filme', 'música', 'jogo', 'diversão', 'show', 'arte', 'cinema', 'série', 'teatro', 'festival'],
        'esportes': ['futebol', 'jogar', 'competição', 'atleta', 'campeonato', 'treino', 'time', 'vitória', 'derrota', 'olímpico']
    }
    
    text_lower = text.lower()
    theme_scores = {}
    
    for theme, keywords in themes_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            theme_scores[theme] = {
                'score': score,
                'confidence': min(100, score * 10),
                'keywords_found': [k for k in keywords if k in text_lower]
            }
    
    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1]['score'], reverse=True)
    
    return {
        'primary_theme': sorted_themes[0][0] if sorted_themes else 'geral',
        'all_themes': dict(sorted_themes[:5]),
        'word_count': len(text.split()),
        'sentence_count': len(re.split(r'[.!?]+', text)),
        'reading_time_minutes': round(len(text.split()) / 150, 1)
    }

def analyze_video_content(video_path: str, transcribed_text: str) -> VideoAnalysis:
    text_analysis = analyze_text_for_themes(transcribed_text)
    
    sentences = re.split(r'[.!?]+', transcribed_text)
    key_moments = []
    
    for i, sentence in enumerate(sentences[:10]):
        if len(sentence.strip()) > 20:
            key_moments.append({
                'time': (i * 10),
                'text': sentence.strip()[:100] + "..." if len(sentence) > 100 else sentence.strip(),
                'importance': min(100, len(sentence) * 2)
            })
    
    suggestions = []
    
    if text_analysis['word_count'] < 100:
        suggestions.append("📝 **Adicione mais conteúdo:** O vídeo é muito curto. Considere expandir a explicação.")
    
    if text_analysis['sentence_count'] < 5:
        suggestions.append("🔤 **Divida o conteúdo:** Use frases mais curtas para melhor compreensão.")
    
    if text_analysis['primary_theme'] == 'educação':
        suggestions.append("🎓 **Inclua exemplos práticos:** Adicione casos reais para ilustrar o conteúdo.")
    
    if text_analysis['primary_theme'] == 'marketing':
        suggestions.append("📢 **Adicione call-to-action:** Inclua uma chamada clara para ação.")
    
    if text_analysis['primary_theme'] == 'tecnologia':
        suggestions.append("💻 **Adicione demonstrações:** Mostre o funcionamento na prática.")
    
    ai_prompts = generate_video_improvement_prompts(
        text_analysis['primary_theme'],
        transcribed_text[:500]
    )
    
    target_audience = identify_target_audience(transcribed_text)
    optimized_keywords = extract_optimized_keywords(transcribed_text)
    sentiment_scores = analyze_sentiment_enhanced(transcribed_text)
    narrative_structure = analyze_narrative_structure(transcribed_text)
    
    theme_scores = {}
    for theme in [text_analysis['primary_theme']] + list(text_analysis['all_themes'].keys())[:2]:
        theme_scores[theme] = calculate_theme_score(theme, transcribed_text)
    
    estimated_engagement = calculate_engagement_score(transcribed_text)
    
    analysis = VideoAnalysis(
        themes=[text_analysis['primary_theme']] + list(text_analysis['all_themes'].keys())[:2],
        key_moments=key_moments[:5],
        improvement_suggestions=suggestions[:5],
        ai_prompts=ai_prompts,
        transcript_summary=transcribed_text[:300] + "..." if len(transcribed_text) > 300 else transcribed_text,
        mood="informative" if text_analysis['primary_theme'] in ['educação', 'tecnologia'] else "entertaining",
        target_audience=target_audience,
        optimized_keywords=optimized_keywords,
        sentiment_scores=sentiment_scores,
        estimated_engagement=estimated_engagement,
        narrative_structure=narrative_structure,
        theme_scores=theme_scores
    )
    
    return analysis

def generate_video_improvement_prompts(theme: str, content: str) -> Dict[str, str]:
    words = content.lower().split()
    keywords = [w for w in words if len(w) > 4][:5]
    main_topic = ' '.join(keywords[:3]) if keywords else "conteúdo principal"
    
    prompt_templates = {
        'imagem': {
            'educação': f"Ilustração educativa sobre {main_topic} com cores vibrantes e elementos gráficos explicativos",
            'marketing': f"Imagem impactante para campanha sobre {main_topic} com design moderno e call-to-action visível",
            'tecnologia': f"Visual futurista sobre {main_topic} com elementos tech, linhas limpas e cores neons",
            'entretenimento': f"Cena divertida sobre {main_topic} com personagens expressivos e cores vivas",
            'default': f"Imagem sobre {main_topic} com composição equilibrada e cores harmoniosas"
        },
        'audio': {
            'educação': f"Narração clara e didática sobre {main_topic} com tom amigável e ritmo moderado",
            'marketing': f"Narração persuasiva sobre {main_topic} com tom confiante e música de fundo motivacional",
            'tecnologia': f"Narração tecnológica sobre {main_topic} com efeitos sonoros futuristas e tom profissional",
            'entretenimento': f"Narração animada sobre {main_topic} com música alegre e efeitos sonoros divertidos",
            'default': f"Narração clara sobre {main_topic} com tom adequado ao conteúdo"
        },
        'video': {
            'educação': f"Vídeo educativo sobre {main_topic} com animações explicativas, gráficos e exemplos visuais",
            'marketing': f"Vídeo promocional sobre {main_topic} com transições dinâmicas, depoimentos e call-to-action claro",
            'tecnologia': f"Vídeo tecnológico sobre {main_topic} com animações 3D, telas de código e visualizações de dados",
            'entretenimento': f"Vídeo de entretenimento sobre {main_topic} com ritmo rápido, humor e efeitos visuais",
            'default': f"Vídeo sobre {main_topic} com boa iluminação, enquadramento adequado e edição profissional"
        },
        'storyboard': {
            'educação': f"Storyboard educativo: 1. Introdução ao tema, 2. Explicação teórica, 3. Exemplo prático, 4. Resumo e conclusão",
            'marketing': f"Storyboard comercial: 1. Problema apresentado, 2. Solução oferecida, 3. Benefícios, 4. Call-to-action",
            'tecnologia': f"Storyboard tecnológico: 1. Apresentação da tecnologia, 2. Funcionamento, 3. Casos de uso, 4. Conclusão",
            'entretenimento': f"Storyboard divertido: 1. Situação cômica, 2. Desenvolvimento, 3. Clímax engraçado, 4. Resolução",
            'default': f"Storyboard: 1. Introdução, 2. Desenvolvimento, 3. Conclusão"
        }
    }
    
    selected_theme = theme if theme in ['educação', 'marketing', 'tecnologia', 'entretenimento'] else 'default'
    
    prompts = {}
    for prompt_type in ['imagem', 'audio', 'video', 'storyboard']:
        if prompt_type in prompt_templates and selected_theme in prompt_templates[prompt_type]:
            prompts[prompt_type] = prompt_templates[prompt_type][selected_theme]
        else:
            prompts[prompt_type] = prompt_templates[prompt_type]['default']
    
    return prompts

def generate_ai_prompts_for_enhancement(analysis: VideoAnalysis, enhancement_type: str) -> Dict[str, str]:
    prompts = {}
    
    if enhancement_type in ['all', 'visual']:
        prompts['visual_enhancement'] = f"""
        Melhore visualmente um vídeo sobre {analysis.themes[0]} com:
        1. Transições suaves entre cenas
        2. Gráficos explicativos para pontos-chave
        3. Legendas claras e legíveis
        4. Cores que combinem com o tema {analysis.themes[0]}
        5. Animações sutis para manter o engajamento
        """
    
    if enhancement_type in ['all', 'audio']:
        prompts['audio_enhancement'] = f"""
        Aprimore o áudio para um vídeo sobre {analysis.themes[0]}:
        1. Qualidade de voz clara e sem ruídos
        2. Música de fundo adequada ao tema
        3. Efeitos sonoros nos momentos certos
        4. Volume balanceado entre voz e música
        5. Silêncios estratégicos para ênfase
        """
    
    if enhancement_type in ['all', 'content']:
        prompts['content_enhancement'] = f"""
        Melhore o conteúdo de um vídeo sobre {analysis.themes[0]}:
        1. Estrutura clara: introdução, desenvolvimento, conclusão
        2. Exemplos práticos e relevantes
        3. Chamadas para ação quando apropriado
        4. Resumo dos pontos principais
        5. Conclusão memorável
        """
    
    return prompts

# ==========================
# FUNÇÕES PARA IA APRIMORADA (mantidas)
# ==========================
def analyze_sentiment_enhanced(text: str) -> Dict[str, float]:
    positive_words = ['excelente', 'ótimo', 'incrível', 'fantástico', 'maravilhoso', 'recomendo', 'amo', 'adoro',
                     'perfeito', 'excelência', 'surpreendente', 'notável', 'brilhante', 'espetacular']
    
    negative_words = ['ruim', 'péssimo', 'horrível', 'terrível', 'desastroso', 'evite', 'odeio', 'detesto',
                     'fracasso', 'decepcionante', 'lamentável', 'insatisfatório', 'problema', 'dificuldade']
    
    text_lower = text.lower()
    words = text_lower.split()
    
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    
    total_sentiment_words = positive_count + negative_count
    
    if total_sentiment_words > 0:
        positive_score = (positive_count / total_sentiment_words) * 100
        negative_score = (negative_count / total_sentiment_words) * 100
    else:
        positive_score = 50
        negative_score = 20
    
    neutral_score = 100 - positive_score - negative_score
    
    return {
        'positive': round(positive_score),
        'negative': round(negative_score),
        'neutral': round(max(0, neutral_score))
    }

def identify_target_audience(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    
    age_range = '25-44'
    if any(word in text_lower for word in ['adolescente', 'jovem', 'escola', 'faculdade', 'universidade']):
        age_range = '18-24'
    elif any(word in text_lower for word in ['sênior', 'idoso', 'aposentadoria', 'terceira idade']):
        age_range = '45-64'
    
    interests = []
    interest_keywords = {
        'tecnologia': ['tecnologia', 'software', 'app', 'digital', 'programação'],
        'educação': ['aprender', 'curso', 'estudo', 'conhecimento', 'educação'],
        'negócios': ['empresa', 'negócio', 'empreendedor', 'investimento', 'lucro'],
        'saúde': ['saúde', 'exercício', 'fitness', 'bem-estar', 'nutrição'],
        'entretenimento': ['filme', 'música', 'jogo', 'série', 'streaming']
    }
    
    for interest, keywords in interest_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            interests.append(interest)
    
    if not interests:
        interests = ['educação', 'tecnologia']
    
    complex_words = ['algoritmo', 'framework', 'paradigma', 'metodologia', 'estratégia', 'otimização']
    knowledge_level = 'Avançado' if any(word in text_lower for word in complex_words) else 'Iniciante/Intermediário'
    
    return {
        'age_range': age_range,
        'interests': interests[:3],
        'knowledge_level': knowledge_level,
        'estimated_size': 'Médio'
    }

def extract_optimized_keywords(text: str, max_keywords: int = 10) -> List[str]:
    text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text_clean.split()
    
    stopwords = [
        'a', 'o', 'e', 'de', 'do', 'da', 'em', 'um', 'uma', 'para', 'com', 'não', 'uma',
        'os', 'as', 'se', 'por', 'mais', 'mas', 'como', 'que', 'eu', 'ele', 'ela', 'nos',
        'vos', 'eles', 'elas', 'meu', 'minha', 'teu', 'tua', 'seu', 'sua', 'isso', 'isto',
        'aquele', 'aquela', 'está', 'estão', 'foi', 'foram', 'ser', 'era', 'eram', 'são',
        'tem', 'têm', 'ter', 'terá', 'terão', 'haver', 'houve', 'também', 'muito', 'pouco',
        'muita', 'pouca', 'muitos', 'poucos', 'algum', 'alguma', 'alguns', 'algumas',
        'todo', 'toda', 'todos', 'todas', 'qual', 'quais', 'quando', 'onde', 'quem',
        'como', 'porque', 'porquê', 'então', 'assim', 'logo', 'portanto', 'contudo',
        'todavia', 'entretanto', 'enquanto', 'após', 'antes', 'durante', 'desde', 'até'
    ]
    
    filtered_words = [w for w in words if w not in stopwords and len(w) >= 3]
    
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    keywords = [word for word, freq in sorted_words[:max_keywords]]
    
    if len(keywords) < 5:
        bigrams = []
        for i in range(len(words) - 1):
            if len(words[i]) >= 3 and len(words[i+1]) >= 3:
                bigram = f"{words[i]} {words[i+1]}"
                bigrams.append(bigram)
        
        bigram_freq = {}
        for bigram in bigrams:
            bigram_freq[bigram] = bigram_freq.get(bigram, 0) + 1
        
        sorted_bigrams = sorted(bigram_freq.items(), key=lambda x: x[1], reverse=True)
        for bigram, freq in sorted_bigrams[:3]:
            keywords.append(bigram)
    
    return keywords[:max_keywords]

def calculate_engagement_score(text: str) -> int:
    score = 50
    
    word_count = len(text.split())
    sentences = re.split(r'[.!?]+', text)
    sentence_count = len([s for s in sentences if len(s.strip()) > 3])
    
    if 200 <= word_count <= 800:
        score += 10
    elif word_count < 100:
        score -= 10
    elif word_count > 1500:
        score -= 5
    
    if sentence_count > 0:
        avg_words_per_sentence = word_count / sentence_count
        if 12 <= avg_words_per_sentence <= 20:
            score += 8
    
    question_count = text.count('?')
    if question_count >= 1:
        score += min(15, question_count * 3)
    
    exclamation_count = text.count('!')
    if 1 <= exclamation_count <= 3:
        score += 5
    
    engagement_words = ['importante', 'atenção', 'incrível', 'fantástico', 'surpreendente',
                       'você', 'seu', 'vamos', 'juntos', 'agora', 'hoje', 'descubra',
                       'aprenda', 'veja', 'experimente', 'compartilhe', 'comente']
    
    engagement_word_count = sum(1 for word in engagement_words if word in text.lower())
    score += min(12, engagement_word_count * 2)
    
    cta_keywords = ['clique', 'inscreva', 'compartilhe', 'comente', 'acesse', 'baixe']
    has_cta = any(keyword in text.lower() for keyword in cta_keywords)
    if has_cta:
        score += 8
    
    words = text.lower().split()
    unique_words = set(words)
    if len(words) > 0:
        lexical_diversity = len(unique_words) / len(words)
        if lexical_diversity > 0.4:
            score += 7
    
    has_numbers = bool(re.search(r'\d+', text))
    if has_numbers:
        score += 5
    
    story_words = ['história', 'experiência', 'caso', 'exemplo', 'aconteceu', 'momento']
    has_story_elements = any(word in text.lower() for word in story_words)
    if has_story_elements:
        score += 6
    
    return max(0, min(100, score))

def analyze_narrative_structure(text: str) -> Dict[str, Any]:
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    if not sentences:
        return {
            'structure_type': 'linear',
            'sentence_count': 0,
            'avg_sentence_length': 0,
            'has_introduction': False,
            'has_conclusion': False,
            'transitions_count': 0,
            'clarity_score': 0
        }
    
    sentence_lengths = [len(s.split()) for s in sentences]
    avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    
    has_introduction = False
    has_conclusion = False
    transitions_count = 0
    
    intro_keywords = ['primeiro', 'inicialmente', 'começo', 'introdução', 'vamos falar sobre', 'hoje vamos']
    concl_keywords = ['finalmente', 'concluindo', 'resumindo', 'em resumo', 'para finalizar', 'em conclusão']
    transition_words = ['além disso', 'por outro lado', 'entretanto', 'no entanto', 'adicionalmente', 
                       'em seguida', 'posteriormente', 'também', 'assim', 'portanto']
    
    text_lower = text.lower()
    
    for i in range(min(2, len(sentences))):
        if any(keyword in sentences[i].lower() for keyword in intro_keywords):
            has_introduction = True
            break
    
    for i in range(max(0, len(sentences)-2), len(sentences)):
        if any(keyword in sentences[i].lower() for keyword in concl_keywords):
            has_conclusion = True
            break
    
    for word in transition_words:
        if word in text_lower:
            transitions_count += text_lower.count(word)
    
    if has_introduction and has_conclusion and transitions_count >= 3:
        structure_type = 'estruturada'
    elif has_introduction or has_conclusion:
        structure_type = 'parcialmente_estruturada'
    else:
        structure_type = 'linear'
    
    clarity_score = 50
    
    if avg_sentence_length > 0:
        long_sentences = sum(1 for length in sentence_lengths if length > 25)
        if long_sentences > 0:
            clarity_score -= min(20, long_sentences * 5)
        
        short_sentences = sum(1 for length in sentence_lengths if length < 5)
        if short_sentences > 0:
            clarity_score -= min(15, short_sentences * 3)
    
    if has_introduction:
        clarity_score += 10
    if has_conclusion:
        clarity_score += 10
    if transitions_count >= 2:
        clarity_score += min(15, transitions_count * 3)
    
    clarity_score = max(0, min(100, clarity_score))
    
    return {
        'structure_type': structure_type,
        'sentence_count': len(sentences),
        'avg_sentence_length': round(avg_sentence_length, 1),
        'has_introduction': has_introduction,
        'has_conclusion': has_conclusion,
        'transitions_count': transitions_count,
        'clarity_score': clarity_score,
        'sentence_length_distribution': {
            'short': sum(1 for l in sentence_lengths if l < 10),
            'medium': sum(1 for l in sentence_lengths if 10 <= l <= 20),
            'long': sum(1 for l in sentence_lengths if l > 20)
        }
    }

def create_video_from_text(audio_path: str, output_path: str, duration: float,
                          bg_type: str = "cor sólida", bg_color: str = "#000000",
                          bg_file: str = None, resolution: str = "1280x720",
                          fps: int = 30) -> bool:
    try:
        width, height = map(int, resolution.split('x'))
        
        if bg_type == "cor sólida":
            color_hex = bg_color.lstrip('#')
            vf = f"color=c=0x{color_hex}:s={width}x{height}:d={duration},format=yuv420p"
            input_video = None
        elif bg_type == "imagem":
            if not bg_file or not os.path.exists(bg_file):
                return False
            vf = f"loop=loop=-1:size=1,format=yuv420p,scale={width}:{height}:force_original_aspect_ratio=1,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            input_video = bg_file
        else:  # vídeo
            if not bg_file or not os.path.exists(bg_file):
                return False
            vf = f"scale={width}:{height}:force_original_aspect_ratio=1,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,loop=0,setpts=N/FRAME_RATE/TB"
            input_video = bg_file
        
        cmd = ['ffmpeg']
        if input_video:
            cmd += ['-stream_loop', '-1', '-i', input_video]
        else:
            cmd += ['-f', 'lavfi', '-i', vf]
            vf = None
        
        cmd += ['-i', audio_path]
        
        filter_complex = []
        if vf:
            filter_complex = [f"[0:v]{vf}[v]"]
        else:
            filter_complex = ["[0:v]null[v]"]
        
        cmd += ['-filter_complex', ';'.join(filter_complex)]
        cmd += ['-map', '[v]', '-map', '1:a']
        cmd += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '23']
        cmd += ['-c:a', 'aac', '-b:a', '192k']
        cmd += ['-t', str(duration)]
        cmd += ['-shortest', '-y', output_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        st.error(f"Erro na criação do vídeo: {str(e)}")
        return False

def calculate_theme_score(theme: str, text: str) -> int:
    theme_keywords = {
        'educação': ['aprender', 'ensinar', 'escola', 'universidade', 'estudar', 'professor', 
                    'aluno', 'curso', 'aula', 'conhecimento', 'educação', 'estudo', 'aprendizado',
                    'didático', 'pedagógico', 'ensino', 'acadêmico'],
        'tecnologia': ['computador', 'software', 'hardware', 'programação', 'aplicativo', 
                      'internet', 'digital', 'inovação', 'startup', 'robótica', 'tecnologia',
                      'dados', 'inteligência artificial', 'IA', 'machine learning', 'código',
                      'algoritmo', 'desenvolvimento', 'sistema', 'plataforma'],
        'marketing': ['venda', 'mercado', 'consumidor', 'publicidade', 'propaganda', 'branding',
                     'segmento', 'target', 'audiência', 'conversão', 'ROI', 'lead', 'cliente',
                     'campanha', 'estratégia', 'promoção', 'oferta', 'negócio', 'lucro'],
        'entretenimento': ['filme', 'música', 'jogo', 'diversão', 'show', 'arte', 'cinema',
                          'série', 'teatro', 'festival', 'entretenimento', 'animação', 'vídeo',
                          'streaming', 'youtube', 'netflix', 'hobby', 'passatempo'],
        'saúde': ['médico', 'hospital', 'doença', 'tratamento', 'saúde', 'exercício', 
                 'bem-estar', 'nutrição', 'fitness', 'medicina', 'corpo', 'alimentação',
                 'dieta', 'exercício', 'treino', 'prevenção', 'cuidados'],
        'negócios': ['empresa', 'negócio', 'lucro', 'venda', 'mercado', 'investimento', 
                    'empreendedor', 'gestão', 'finanças', 'estratégia', 'gestão', 'liderança',
                    'equipe', 'produtividade', 'eficiência', 'resultados', 'performance']
    }
    
    text_lower = text.lower()
    keywords = theme_keywords.get(theme.lower(), [])
    
    if not keywords:
        return 0
    
    matches = 0
    total_keywords = len(keywords)
    
    for keyword in keywords:
        if keyword in text_lower:
            matches += 1
    
    if total_keywords > 0:
        base_score = (matches / total_keywords) * 100
        
        total_occurrences = sum(text_lower.count(keyword) for keyword in keywords)
        repetition_bonus = min(20, total_occurrences * 2)
        
        return min(100, int(base_score + repetition_bonus))
    
    return 0

def generate_enhanced_ai_prompts(analysis: VideoAnalysis, prompt_type: str, style: str, tone: str, 
                                platforms: List[str], complexity_level: int) -> Dict[str, Dict]:
    prompts = {}
    
    type_mapping = {
        '🎨 Imagem/Visual': 'visual',
        '🔊 Áudio/Narração': 'audio',
        '🎬 Vídeo/Edição': 'video',
        '📝 Texto/Roteiro': 'text',
        '📊 Storyboard': 'storyboard',
        '🚀 Todos Integrados': 'all'
    }
    
    prompt_type_code = type_mapping.get(prompt_type, 'all')
    
    complexity_map = {
        1: 'simples e direto',
        2: 'detalhado',
        3: 'completo com exemplos',
        4: 'avançado com técnicas específicas',
        5: 'profissional com referências de mercado'
    }
    
    complexity_desc = complexity_map.get(complexity_level, 'detalhado')
    
    main_theme = analysis.themes[0] if analysis.themes else "conteúdo principal"
    target_audience = analysis.target_audience
    mood = analysis.mood
    optimized_keywords = analysis.optimized_keywords[:3] if analysis.optimized_keywords else [main_theme]
    
    age_range = target_audience.get('age_range', 'Adultos')
    interests = target_audience.get('interests', ['tecnologia'])
    knowledge_level = target_audience.get('knowledge_level', 'Geral')
    
    if prompt_type_code in ['visual', 'all']:
        prompts['visual_prompt'] = {
            'title': '🎨 Prompt para Geração de Imagem/Visual',
            'purpose': f'Criar conteúdo visual para o tema "{main_theme}" no estilo {style}',
            'level': 'Avançado' if complexity_level >= 4 else 'Intermediário',
            'prompt': f"""Crie uma imagem/vídeo/visual sobre "{main_theme}" com as seguintes especificações:

TEMA PRINCIPAL: {main_theme.title()}
PÚBLICO-ALVO: {age_range} interessados em {', '.join(interests)}
ESTILO VISUAL: {style}
TOM EMOCIONAL: {tone}
PLATAFORMAS: {', '.join(platforms)}
NÍVEL DE DETALHE: {complexity_desc}

REQUISITOS ESPECÍFICOS:
1. Composição que prende atenção nos primeiros 3 segundos
2. Cores que refletem {tone.lower()} e {style.lower()}
3. Elementos visuais relacionados a: {', '.join(optimized_keywords)}
4. Layout otimizado para {platforms[0] if platforms else 'redes sociais'}
5. Incluir espaço para texto/legenda se necessário

ELEMENTOS A EVITAR:
- Clichés visuais do tema
- Cores muito vibrantes se tom for {tone}
- Texto muito pequeno para mobile

PALAVRAS-CHAVE PARA INSPIRAÇÃO: {' '.join(analysis.themes[:3]) if analysis.themes else main_theme} {mood} {style}""",
            'parameters': {
                'Aspect Ratio': '16:9' if 'YouTube' in platforms else '9:16' if 'TikTok' in platforms else '1:1',
                'Color Palette': f'{style} com toques de {tone}',
                'Main Focus': main_theme,
                'Secondary Elements': ', '.join(analysis.themes[1:3]) if analysis.themes and len(analysis.themes) > 1 else 'contexto relacionado'
            },
            'example': f'Para o tema "{main_theme}" no estilo {style}, crie uma imagem com fundo gradiente suave, ícones modernos representando os conceitos principais, e tipografia clara que comunique {tone.lower()}.'
        }
    
    if prompt_type_code in ['audio', 'all']:
        prompts['audio_prompt'] = {
            'title': '🔊 Prompt para Geração de Áudio/Narração',
            'purpose': f'Criar narração/áudio para conteúdo sobre "{main_theme}"',
            'level': 'Avançado' if complexity_level >= 4 else 'Intermediário',
            'prompt': f"""Crie um script de narração/áudio sobre "{main_theme}" com as seguintes especificações:

DURAÇÃO: {'3 minutos' if complexity_level >= 3 else '1 minuto'}
PÚBLICO: {age_range} - {knowledge_level}
TOM DE VOZ: {tone}
ESTILO DE NARRAÇÃO: {'Profissional e técnico' if knowledge_level == 'Avançado' else 'Amigável e explicativo'}
EMOÇÃO PRINCIPAL: {mood}
PLATAFORMAS: {', '.join(platforms)}

ESTRUTURA DO SCRIPT:
[INTRODUÇÃO - 15% do tempo]
- Gancho inicial que capture atenção
- Apresentação do tema principal
- O que o público vai aprender/ganhar

[DESENVOLVIMENTO - 70% do tempo]
- Ponto principal 1: {main_theme}
- Ponto principal 2: {analysis.themes[1] if analysis.themes and len(analysis.themes) > 1 else 'Aplicação prática'}
- Ponto principal 3: {analysis.themes[2] if analysis.themes and len(analysis.themes) > 2 else 'Benefícios'}
- Exemplos e analogias para clareza

[CONCLUSÃO - 15% do tempo]
- Resumo dos pontos principais
- Call-to-action apropriado
- Encerramento memorável

DIRETRIZES DE VOZ:
- Velocidade: {'mais lenta para explicações complexas' if complexity_level >= 4 else 'moderada para melhor compreensão'}
- Ênfase: destacar palavras-chave como {', '.join(optimized_keywords)}
- Pausas: estratégicas para absorção de informação
- Entonação: variar para manter interesse

ELEMENTOS SONOROS SUGERIDOS:
- Música de fundo: {mood} e {tone.lower()}
- Efeitos sonoros: sutis para transições
- Silêncios: estratégicos para ênfase""",
            'parameters': {
                'Tempo Total': f'{complexity_level * 1.5:.1f} minutos',
                'Velocidade de Fala': '140-160 palavras/minuto',
                'Tom Vocal': f'{tone} com {mood}',
                'Formato de Arquivo': 'MP3 192kbps estéreo'
            }
        }
    
    if prompt_type_code in ['video', 'all']:
        prompts['video_prompt'] = {
            'title': '🎬 Prompt para Edição de Vídeo',
            'purpose': f'Criar plano de edição para vídeo sobre "{main_theme}"',
            'level': 'Profissional' if complexity_level >= 4 else 'Intermediário',
            'prompt': f"""Crie um plano de edição de vídeo completo sobre "{main_theme}":

METADADOS DO VÍDEO:
- Tema Principal: {main_theme}
- Duração Alvo: {'5-7 minutos' if complexity_level >= 4 else '3-5 minutos'}
- Público-Alvo: {age_range}, {knowledge_level}
- Plataformas: {', '.join(platforms)}
- Estilo Geral: {style}
- Tom Emocional: {tone}

ESTRUTURA DETALHADA DE EDIÇÃO:

[SEÇÃO 1: ABERTURA (0:00-0:30)]
- 0:00-0:05: Hook visual impactante relacionado a {main_theme}
- 0:05-0:15: Introdução rápida com texto/animação
- 0:15-0:30: Apresentação do tema e benefícios

[SEÇÃO 2: DESENVOLVIMENTO ({'2:00-5:00' if complexity_level >= 4 else '1:00-3:00'})]
- Cena 1: Explicação do conceito principal
  • Visual: {'Gráficos animados' if style == 'Profissional' else 'Imagens ilustrativas'}
  • Áudio: Narração clara com música de fundo {mood}
  • Transição: {'Corte rápido' if 'TikTok' in platforms else 'Dissolve suave'}
  
- Cena 2: Exemplo prático/aplicação
  • Visual: Demonstração passo a passo
  • Áudio: Efeitos sonoros para ações importantes
  • Texto: Legenda de pontos-chave

- Cena 3: Dicas avançadas/benefícios
  • Visual: Lista animada com ícones
  • Áudio: Música mais energética para engajamento
  • Destaque: Box com informação importante

[SEÇÃO 3: CONCLUSÃO (últimos 30 segundos)]
- Resumo visual dos 3 principais pontos
- Call-to-action claro e visível
- Tela final com créditos e links

TÉCNICAS DE EDIÇÃO RECOMENDADAS:
1. Ritmo: {'Cortes rápidos (a cada 2-3s) para plataformas curtas' if 'TikTok' in platforms else 'Cortes moderados (a cada 5-7s)'}
2. Transições: Usar {style.lower()} apropriadas para {tone.lower()}
3. Cores: Grade de cores baseada em {mood} e {tone}
4. Tipografia: Fontes {style.lower()} para {age_range}
5. Animações: {'Sutis e profissionais' if style == 'Profissional' else 'Dinâmicas e chamativas'}

CHECKLIST DE QUALIDADE:
- [ ] Hook nos primeiros 3 segundos
- [ ] Legibilidade em dispositivos móveis
- [ ] Sincronia áudio-vídeo perfeita
- [ ] Call-to-action claro
- [ ] Otimizado para {platforms[0] if platforms else 'plataforma principal'}""",
            'parameters': {
                'Frame Rate': '30fps',
                'Resolution': '1080p' if complexity_level >= 3 else '720p',
                'Aspect Ratio': '9:16' if 'TikTok' in platforms else '16:9',
                'Color Grading': f'{style} com {tone}',
                'Audio Mix': '-6dB voz, -20dB música'
            }
        }
    
    if prompt_type_code in ['text', 'all']:
        prompts['text_prompt'] = {
            'title': '📝 Prompt para Redação/Roteiro',
            'purpose': f'Escrever conteúdo textual sobre "{main_theme}"',
            'level': 'Avançado' if complexity_level >= 4 else 'Intermediário',
            'prompt': f"""Escreva um conteúdo textual sobre "{main_theme}" com:

FORMATO: {'Artigo detalhado' if complexity_level >= 4 else 'Post de blog' if complexity_level >= 3 else 'Texto conciso'}
TÓNICA: {tone}
PÚBLICO: {age_range} com nível {knowledge_level}
OBJETIVO: {'Educar profundamente' if complexity_level >= 4 else 'Informar de forma engajadora'}
PLATAFORMAS: {', '.join(platforms)}

ESTRUTURA DETALHADA:

TÍTULO PRINCIPAL (Atraente e com palavra-chave):
- Opção 1: [Number] Formas de [Benefício] com {main_theme}
- Opção 2: O Guia Definitivo para {main_theme} em {datetime.now().year}
- Opção 3: {main_theme.title()}: Como [Resolver Problema] em [Tempo]

INTRODUÇÃO (Primeiro parágrafo - 100-150 palavras):
- Start with hook: estatística surpreendente, pergunta provocativa ou cenário comum
- Contextualize {main_theme} para o leitor
- State value proposition: o que eles vão aprender/ganhar
- Preview dos principais pontos

CORPO DO TEXTO ({'1500-2000' if complexity_level >= 4 else '800-1200'} palavras):

SEÇÃO 1: Fundamentos de {main_theme}
- Definição clara e acessível
- Por que é importante hoje
- Estatísticas relevantes (se aplicável)
- Exemplo prático do dia a dia

SEÇÃO 2: {'Implementação Prática' if complexity_level >= 3 else 'Aplicações'}
- Passo 1: [Ação específica e mensurável]
  • Como fazer
  • Ferramentas necessárias
  • Tempo estimado
- Passo 2: [Próxima ação]
  • Dicas para sucesso
  • Erros comuns a evitar
  • Exemplo de caso real

SEÇÃO 3: {'Otimizações Avançadas' if complexity_level >= 4 else 'Dicas Adicionais'}
- Técnicas para melhores resultados
- Integração com outros sistemas/conceitos
- Métricas para acompanhar sucesso

CONCLUSÃO (150-200 palavras):
- Resumo dos pontos principais
- Call-to-action específico (download, inscrição, comentário)
- Pergunta para engajar comentários
- Próximos passos sugeridos

FORMATAÇÃO E SEO:
- H1: Título principal
- H2: Cada seção principal
- H3: Subseções quando necessário
- Palavras-chave: {', '.join(analysis.optimized_keywords[:5]) if analysis.optimized_keywords else main_theme}
- Meta Description: 155 caracteres incluindo benefício principal
- URL amigável: /guia-{main_theme.lower().replace(' ', '-')}

TOM E ESTILO:
- Voz: {'Autoritativa mas acessível' if tone == 'Autoritário' else tone.lower()}
- Parágrafos: Curtos (3-4 linhas máximo)
- Listas: Usar bullet points para dicas
- Destaques: Negrito para conceitos importantes
- Transições: Frases que conectem seções""",
            'parameters': {
                'Word Count': f'{complexity_level * 500} palavras',
                'Reading Level': '8th grade' if knowledge_level == 'Iniciante' else '12th grade',
                'Keywords': ', '.join(analysis.themes[:3]),
                'CTAs': '1 por seção + final'
            }
        }
    
    if prompt_type_code in ['storyboard', 'all']:
        prompts['storyboard_prompt'] = {
            'title': '📊 Prompt para Storyboard',
            'purpose': f'Criar storyboard para vídeo sobre "{main_theme}"',
            'level': 'Profissional' if complexity_level >= 4 else 'Intermediário',
            'prompt': f"""Crie um storyboard detalhado para um vídeo sobre "{main_theme}":

INFORMAÇÕES BÁSICAS:
- Tema: {main_theme}
- Duração Total: {'5-7 minutos' if complexity_level >= 4 else '3-5 minutos'}
- Público: {age_range}, {knowledge_level}
- Estilo: {style}
- Tom: {tone}
- Plataformas: {', '.join(platforms)}

ESTRUTURA DO STORYBOARD (Cenas e Tempos):

CENA 1: ABERTURA (0:00-0:30)
- Quadro 1 (0:00-0:05): Hook visual impactante
  • Visual: {main_theme} representado de forma criativa
  • Áudio: Música de impacto ou efeito sonoro
  • Texto: Nenhum ou título muito breve
  
- Quadro 2 (0:05-0:15): Introdução
  • Visual: Apresentador/âncora ou animação introdutória
  • Áudio: Voz off explicando o que será abordado
  • Texto: "Hoje: {main_theme.title()}"
  
- Quadro 3 (0:15-0:30): Benefícios
  • Visual: 3 ícones ou elementos visuais representando benefícios
  • Áudio: Lista dos principais benefícios que o espectador terá
  • Texto: "Você vai aprender: [Benefício 1], [Benefício 2], [Benefício 3]"

CENA 2: CONCEITO PRINCIPAL ({'1:00-2:30' if complexity_level >= 4 else '0:30-1:30'})
- Quadro 4: Explicação do conceito
  • Visual: {'Gráficos animados explicando o conceito' if style == 'Profissional' else 'Imagens ilustrativas'}
  • Áudio: Narração clara e didática
  • Texto: Definição de {main_theme}
  
- Quadro 5: Exemplo prático
  • Visual: Demonstração passo a passo ou caso real
  • Áudio: Descrição do exemplo com detalhes
  • Texto: "Exemplo Prático: [Nome do exemplo]"
  
- Quadro 6: Dados/estatísticas
  • Visual: Gráficos ou números animados
  • Áudio: Citação de dados relevantes
  • Texto: Estatísticas principais

CENA 3: APLICAÇÕES ({'2:30-4:00' if complexity_level >= 4 else '1:30-2:30'})
- Quadro 7: Aplicação 1
  • Visual: Demonstração da primeira aplicação
  • Áudio: Instruções passo a passo
  • Texto: "Passo 1: [Descrição]"
  
- Quadro 8: Aplicação 2
  • Visual: Demonstração da segunda aplicação
  • Áudio: Instruções passo a passo
  • Texto: "Passo 2: [Descrição]"
  
- Quadro 9: Aplicação 3
  • Visual: Demonstração da terceira aplicação
  • Áudio: Instruções passo a passo
  • Texto: "Passo 3: [Descrição]"

CENA 4: CONCLUSÃO (últimos 30 segundos)
- Quadro 10: Resumo (X:XX-X:XX)
  • Visual: 3 pontos principais em tela
  • Áudio: Resumo conciso do conteúdo
  • Texto: "Em resumo: 1. [Ponto 1], 2. [Ponto 2], 3. [Ponto 3]"
  
- Quadro 11: Call-to-Action (X:XX-X:XX)
  • Visual: Botão ou elemento visual destacado
  • Áudio: Chamada clara para ação
  • Texto: "{'Inscreva-se agora!' if 'YouTube' in platforms else 'Siga para mais!'}"
  
- Quadro 12: Tela final (X:XX-X:XX)
  • Visual: Créditos e informações de contato
  • Áudio: Música de encerramento
  • Texto: "Obrigado por assistir! | @canal | links na descrição"

DIRETRIZES VISUAIS:
- Estilo: {style}
- Paleta de cores: Baseada em {mood} e {tone}
- Tipografia: Fontes {style.lower()} para {age_range}
- Transições: {style.lower()} apropriadas para {tone.lower()}
- Animações: {'Sutis e profissionais' if style == 'Profissional' else 'Dinâmicas e chamativas'}

FORMATO DO STORYBOARD:
Para cada quadro, especificar:
1. Número da cena/quadro
2. Tempo (início-fim)
3. Descrição visual detalhada
4. Áudio (narração/música/efeitos)
5. Texto em tela (se houver)
6. Transição para próximo quadro

EXEMPLO DE QUADRO COMPLETO:
[Cena 2, Quadro 4]
Tempo: 1:00-1:20
Visual: Animação de gráficos explicando o conceito de {main_theme}. Cores: azul e branco. Elementos se movem suavemente.
Áudio: "Agora vamos entender o conceito fundamental de {main_theme}. Basicamente, trata-se de..."
Texto: "CONCEITO: {main_theme.upper()}"
Transição: Dissolve para Quadro 5""",
            'parameters': {
                'Total de Quadros': '12-16 quadros',
                'Duração por Quadro': '15-30 segundos',
                'Formato de Saída': 'PDF ou imagem com descrições detalhadas',
                'Elementos Visuais': f'{style} com foco em {main_theme}'
            }
        }
    
    return prompts

def calculate_content_quality_score(analysis: VideoAnalysis) -> int:
    score = 50
    
    if hasattr(analysis, 'sentiment_scores'):
        positive = analysis.sentiment_scores.get('positive', 0)
        score += positive * 0.2
    
    if analysis.themes and len(analysis.themes) >= 2:
        score += 10
    
    if analysis.key_moments and len(analysis.key_moments) >= 3:
        score += 15
    
    if analysis.improvement_suggestions:
        score += min(20, len(analysis.improvement_suggestions) * 5)
    
    if hasattr(analysis, 'estimated_engagement'):
        score += analysis.estimated_engagement * 0.2
    
    return min(100, int(score))

def calculate_category_score(analysis: VideoAnalysis, category: str) -> int:
    base_scores = {
        'Conteúdo': 60,
        'Engajamento': 55,
        'Técnico': 70,
        'Narrativa': 65
    }
    
    score = base_scores.get(category, 50)
    
    if category == 'Conteúdo' and analysis.themes:
        score += min(30, len(analysis.themes) * 7)
    
    if category == 'Engajamento' and analysis.key_moments:
        avg_importance = sum(m.get('importance', 0) for m in analysis.key_moments[:3]) / 3
        score += avg_importance * 0.3
    
    if category == 'Narrativa' and hasattr(analysis, 'narrative_structure'):
        clarity = analysis.narrative_structure.get('clarity_score', 0)
        score += clarity * 0.3
    
    return min(100, int(score))

def get_priority_suggestions(analysis: VideoAnalysis) -> List[Dict[str, Any]]:
    suggestions = []
    
    if hasattr(analysis, 'transcript_summary'):
        word_count = len(analysis.transcript_summary.split())
        if word_count < 200:
            suggestions.append({
                'id': 'length',
                'title': 'Conteúdo Muito Curto',
                'description': 'Seu conteúdo poderia se beneficiar de mais profundidade e detalhes.',
                'impact': 9,
                'difficulty': 4,
                'actions': [
                    'Adicionar exemplos práticos',
                    'Incluir estatísticas relevantes',
                    'Expandir explicações técnicas',
                    'Adicionar estudos de caso'
                ],
                'ai_prompt': f'Expanda o conteúdo sobre {analysis.themes[0]} adicionando 3 exemplos práticos, 2 estatísticas relevantes e 1 estudo de caso. Mantenha o tom {analysis.mood}.'
            })
    
    if analysis.key_moments and len(analysis.key_moments) < 3:
        suggestions.append({
            'id': 'structure',
            'title': 'Estrutura Pode Melhorar',
            'description': 'A estrutura do conteúdo pode ser otimizada para melhor retenção.',
            'impact': 8,
            'difficulty': 5,
            'actions': [
                'Criar introdução mais impactante',
                'Adicionar transições entre tópicos',
                'Incluir resumos parciais',
                'Melhorar conclusão com call-to-action'
            ],
            'ai_prompt': f'Reestruture o conteúdo sobre {analysis.themes[0]} para ter: 1) Hook impactante, 2) 3 pontos principais claros, 3) Resumos parciais, 4) Conclusão forte com CTA. Tom: {analysis.mood}.'
        })
    
    if hasattr(analysis, 'estimated_engagement') and analysis.estimated_engagement < 60:
        suggestions.append({
            'id': 'engagement',
            'title': 'Aumentar Engajamento',
            'description': 'Elementos de engajamento podem melhorar a retenção do público.',
            'impact': 7,
            'difficulty': 3,
            'actions': [
                'Adicionar perguntas ao público',
                'Incluir elementos interativos',
                'Usar mais histórias e anedotas',
                'Variar ritmo e tom de voz'
            ],
            'ai_prompt': f'Reescreva partes do conteúdo sobre {analysis.themes[0]} para incluir: 1) 2 perguntas retóricas, 2) 1 história pessoal relevante, 3) Variação de ritmo, 4) Elementos surpresa. Público: {analysis.target_audience.get("age_range", "adultos")}.'
        })
    
    if hasattr(analysis, 'target_audience') and analysis.target_audience.get('knowledge_level') == 'Avançado':
        suggestions.append({
            'id': 'clarity',
            'title': 'Simplificar Conteúdo Complexo',
            'description': 'Conteúdo muito técnico pode alienar parte do público.',
            'impact': 6,
            'difficulty': 6,
            'actions': [
                'Adicionar analogias simples',
                'Criar glossário de termos',
                'Incluir exemplos do dia a dia',
                'Oferecer versão resumida'
            ],
            'ai_prompt': f'Simplifique o conteúdo técnico sobre {analysis.themes[0]} para nível {analysis.target_audience.get("knowledge_level")}. Adicione 3 analogias, 2 exemplos práticos e 1 resumo em linguagem simples.'
        })
    
    suggestions.sort(key=lambda x: x['impact'], reverse=True)
    
    return suggestions

def get_quick_improvements(analysis: VideoAnalysis) -> List[Dict[str, Any]]:
    improvements = []
    
    improvements.append({
        'id': 'thumbnail',
        'title': 'Thumbnail Atraente',
        'description': 'Criar thumbnail com texto legível e imagem impactante.',
        'time_estimate': '30 minutos',
        'impact': 'Alto',
        'tools': ['Canva', 'Photoshop', 'Thumbnail makers']
    })
    
    improvements.append({
        'id': 'hook',
        'title': 'Hook nos Primeiros 5s',
        'description': 'Reeditar início para prender atenção imediata.',
        'time_estimate': '1 hora',
        'impact': 'Muito Alto',
        'tools': ['Editor de vídeo', 'Recorte dos primeiros segundos']
    })
    
    improvements.append({
        'id': 'subtitles',
        'title': 'Legendas Sincronizadas',
        'description': 'Adicionar legendas precisas para acessibilidade.',
        'time_estimate': '2 horas',
        'impact': 'Alto',
        'tools': ['Auto-subtitle tools', 'Editor de legendas']
    })
    
    if analysis.themes and 'tecnologia' in analysis.themes:
        improvements.append({
            'id': 'graphics',
            'title': 'Gráficos Explicativos',
            'description': 'Inserir gráficos simples para explicar conceitos.',
            'time_estimate': '1.5 horas',
            'impact': 'Médio-Alto',
            'tools': ['Canva', 'PowerPoint', 'Google Slides']
        })
    
    return improvements

def generate_action_plan(analysis: VideoAnalysis, focus_areas: List[str]) -> Dict[str, Dict]:
    action_plan = {}
    
    if 'Engajamento Inicial' in focus_areas:
        action_plan['Engajamento Inicial'] = {
            'objective': 'Aumentar retenção nos primeiros 30 segundos',
            'tasks': [
                {'task': 'Analisar dados de retenção atuais', 'time_estimate': '30 min', 'completed': False},
                {'task': 'Redesenhar hook visual/verbal', 'time_estimate': '1 hora', 'completed': False},
                {'task': 'Testar 3 versões diferentes', 'time_estimate': '2 horas', 'completed': False},
                {'task': 'Implementar melhor versão', 'time_estimate': '1 hora', 'completed': False}
            ],
            'total_time': '4.5 horas',
            'success_metrics': 'Retenção +15% nos primeiros 30s'
        }
    
    if 'Retenção de Audiência' in focus_areas:
        action_plan['Retenção de Audiência'] = {
            'objective': 'Manter audiência engajada durante todo o vídeo',
            'tasks': [
                {'task': 'Identificar pontos de queda de audiência', 'time_estimate': '45 min', 'completed': False},
                {'task': 'Inserir elementos surpresa nos pontos críticos', 'time_estimate': '1.5 horas', 'completed': False},
                {'task': 'Variar ritmo e formato a cada 60-90s', 'time_estimate': '2 horas', 'completed': False},
                {'task': 'Adicionar perguntas interativas', 'time_estimate': '1 hora', 'completed': False}
            ],
            'total_time': '5.25 horas',
            'success_metrics': 'Retenção média +20%'
        }
    
    if 'Qualidade Visual' in focus_areas:
        action_plan['Qualidade Visual'] = {
            'objective': 'Melhorar aparência e profissionalismo visual',
            'tasks': [
                {'task': 'Ajustar color grading para consistência', 'time_estimate': '1.5 horas', 'completed': False},
                {'task': 'Padronizar fontes e tamanhos de texto', 'time_estimate': '1 hora', 'completed': False},
                {'task': 'Adicionar transições suaves entre cenas', 'time_estimate': '1.5 horas', 'completed': False},
                {'task': 'Otimizar para diferentes tamanhos de tela', 'time_estimate': '1 hora', 'completed': False}
            ],
            'total_time': '5 horas',
            'success_metrics': 'Feedback visual positivo +30%'
        }
    
    return action_plan

# ==========================
# NOVAS FUNÇÕES PARA A ESTRUTURA NARRATIVA
# ==========================
def generate_act_prompts(act: NarrativeAct, analysis: Optional[VideoAnalysis] = None) -> Dict[str, str]:
    """Gera prompts para um ato baseado em seu tom, estilo e conteúdo"""
    if not act.text_content:
        return {}
    
    # Se não houver análise, cria uma análise simples do texto do ato
    if analysis is None:
        text_analysis = analyze_text_for_themes(act.text_content)
        # Cria uma análise mínima
        analysis = VideoAnalysis(
            themes=[text_analysis['primary_theme']],
            key_moments=[],
            improvement_suggestions=[],
            ai_prompts={},
            transcript_summary=act.text_content[:200],
            mood=act.emotional_tone,
            target_audience={'age_range': '25-44', 'interests': [text_analysis['primary_theme']], 'knowledge_level': 'Intermediário'},
            optimized_keywords=extract_optimized_keywords(act.text_content, 5),
            sentiment_scores=analyze_sentiment_enhanced(act.text_content),
            estimated_engagement=50,
            narrative_structure={},
            theme_scores={}
        )
    
    # Gera prompts avançados usando a função existente, mas ajustando para o ato
    # Usamos um prompt_type 'all' para gerar todos os tipos
    platforms = ['YouTube']  # Poderíamos permitir customização
    complexity = 3  # Nível médio
    
    prompts = generate_enhanced_ai_prompts(
        analysis=analysis,
        prompt_type='🚀 Todos Integrados',
        style=act.visual_style,
        tone=act.emotional_tone,
        platforms=platforms,
        complexity_level=complexity
    )
    
    # Adiciona também prompts específicos para o tom do ato
    # Podemos enriquecer com informações do ato
    for key in prompts:
        if 'prompt' in prompts[key]:
            prompts[key]['prompt'] = f"[ATO {act.number}: {act.title}]\n" + prompts[key]['prompt']
    
    return prompts

def render_narrative_tab():
    """Aba para configuração da estrutura narrativa"""
    st.markdown("### 🎭 Estrutura Narrativa")
    
    # Seleção de template
    template_options = list(NARRATIVE_TEMPLATES.keys())
    if not template_options:
        st.warning("Nenhum template disponível.")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_template = st.selectbox(
            "Escolha um template narrativo",
            template_options,
            format_func=lambda x: NARRATIVE_TEMPLATES[x].name,
            key="narrative_template_select"
        )
    
    with col2:
        if st.button("📋 Carregar Template", type="primary", use_container_width=True):
            template = NARRATIVE_TEMPLATES[selected_template]
            st.session_state.narrative_template = template
            st.success(f"Template '{template.name}' carregado!")
            st.rerun()
    
    if st.session_state.narrative_template is None:
        st.info("Selecione um template e clique em 'Carregar Template' para começar.")
        return
    
    template = st.session_state.narrative_template
    
    # Exibe descrição
    st.info(template.description)
    
    # Opção de personalizar durações
    st.markdown("#### ⏱️ Ajuste de Duração (opcional)")
    total_minutes = st.number_input(
        "Duração total desejada (minutos)",
        min_value=1, max_value=60,
        value=int(sum(act.target_duration for act in template.acts) / 60),
        key="narrative_total_duration"
    )
    total_seconds = total_minutes * 60
    
    # Distribuição automática proporcional
    if st.button("🔄 Distribuir automaticamente", use_container_width=True):
        total_weight = sum(act.target_duration for act in template.acts)
        if total_weight > 0:
            for act in template.acts:
                act.target_duration = (act.target_duration / total_weight) * total_seconds
        st.success("Durações recalculadas proporcionalmente!")
    
    st.markdown("#### 📝 Conteúdo dos Atos")
    
    # Para cada ato, permite edição e geração de prompts
    for i, act in enumerate(template.acts):
        with st.expander(f"Ato {act.number}: {act.title}", expanded=i==0):
            col1, col2 = st.columns(2)
            with col1:
                act.emotional_tone = st.selectbox(
                    f"Tom emocional",
                    ["misterioso", "energético", "reflexivo", "íntimo", "informativo", "convincente"],
                    index=["misterioso", "energético", "reflexivo", "íntimo", "informativo", "convincente"].index(act.emotional_tone) if act.emotional_tone in ["misterioso","energético","reflexivo","íntimo","informativo","convincente"] else 0,
                    key=f"narrative_tone_{i}"
                )
                act.visual_style = st.selectbox(
                    f"Estilo visual",
                    ["dark", "vibrante", "suave", "clean", "dinâmico", "neutro"],
                    key=f"narrative_style_{i}"
                )
            with col2:
                act.target_duration = st.number_input(
                    f"Duração (segundos)",
                    min_value=10, max_value=600,
                    value=int(act.target_duration),
                    key=f"narrative_dur_{i}"
                )
            
            # Campo de texto para o roteiro do ato
            act.text_content = st.text_area(
                f"Roteiro do Ato {act.number}",
                value=act.text_content,
                height=150,
                key=f"narrative_text_{i}",
                placeholder="Digite ou cole o texto deste ato..."
            )
            
            # Botão para gerar prompts com IA baseado no texto e nas configurações
            if act.text_content and st.button(f"✨ Gerar Prompts para Ato {act.number}", key=f"narrative_gen_prompt_{i}"):
                with st.spinner("Gerando prompts..."):
                    # Usa a análise existente se disponível, ou cria uma análise simples
                    if st.session_state.video_analysis:
                        analysis = st.session_state.video_analysis
                    else:
                        # Cria uma análise básica a partir do texto do ato
                        text_analysis = analyze_text_for_themes(act.text_content)
                        analysis = VideoAnalysis(
                            themes=[text_analysis['primary_theme']],
                            key_moments=[],
                            improvement_suggestions=[],
                            ai_prompts={},
                            transcript_summary=act.text_content[:200],
                            mood=act.emotional_tone,
                            target_audience={'age_range': '25-44', 'interests': [text_analysis['primary_theme']], 'knowledge_level': 'Intermediário'},
                            optimized_keywords=extract_optimized_keywords(act.text_content, 5),
                            sentiment_scores=analyze_sentiment_enhanced(act.text_content),
                            estimated_engagement=50,
                            narrative_structure={},
                            theme_scores={}
                        )
                    
                    prompts = generate_enhanced_ai_prompts(
                        analysis=analysis,
                        prompt_type='🚀 Todos Integrados',
                        style=act.visual_style,
                        tone=act.emotional_tone,
                        platforms=['YouTube'],
                        complexity_level=3
                    )
                    act.prompts = prompts
                    st.success("Prompts gerados!")
            
            # Exibe prompts se existirem
            if act.prompts:
                st.markdown("**📋 Prompts gerados:**")
                for p_name, p_data in act.prompts.items():
                    with st.expander(f"{p_data['title']}", expanded=False):
                        st.code(p_data['prompt'], language='text')
    
    # Botão para salvar a estrutura no estado da sessão
    if st.button("💾 Salvar Estrutura Narrativa", type="primary", use_container_width=True):
        st.session_state.narrative_template = template
        st.success("Estrutura salva! Vá para a aba de IA para gerar os prompts completos ou para a aba de exportação para renderizar o vídeo por atos.")

# ==========================
# FUNÇÕES DE INTERFACE (modificadas)
# ==========================
def render_text_tab():
    st.markdown("### 📝 Transcrição e Texto")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.session_state.transcribed_text:
            st.markdown("#### 📋 Texto Transcrito")
            
            edited_text = st.text_area(
                "Texto transcrito (editável)",
                value=st.session_state.transcribed_text,
                height=400,
                key="transcription_editor"
            )
            
            if edited_text != st.session_state.transcribed_text:
                st.session_state.transcribed_text = edited_text
                if st.button("💾 Salvar Alterações", use_container_width=True):
                    st.success("Texto salvo!")
            
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                word_count = len(st.session_state.transcribed_text.split())
                st.metric("📝 Palavras", word_count)
            with col_stats2:
                char_count = len(st.session_state.transcribed_text)
                st.metric("🔤 Caracteres", char_count)
            with col_stats3:
                reading_time = round(word_count / 150, 1)
                st.metric("⏱️ Tempo de Leitura", f"{reading_time} min")
            
            if st.session_state.text_segments:
                st.markdown("#### 🎯 Segmentos do Texto")
                for segment in st.session_state.text_segments:
                    with st.expander(f"Segmento {segment['id']}: {segment['start_time']:.1f}s - {segment['end_time']:.1f}s", expanded=False):
                        st.write(segment['text'])
                        st.caption(f"Palavras: {segment['word_count']} | Duração: {segment['duration']:.1f}s")
            
        else:
            st.info("""
            **Para obter transcrição:**
            
            1. **Faça upload de um áudio** ou vídeo na barra lateral
            2. **Clique em 'Transcrever Áudio'** na aba Upload
            3. **Aguarde o processamento** pela IA
            
            **Funcionalidades disponíveis:**
            • 📝 Edição do texto transcrito
            • 🎯 Divisão automática em segmentos
            • 📊 Estatísticas do conteúdo
            • 💾 Exportação do texto
            """)
    
    with col2:
        st.markdown("#### 🔧 Ferramentas de Texto")
        
        if st.session_state.transcribed_text and st.button("🎯 Analisar Temas", use_container_width=True):
            with st.spinner("Analisando temas..."):
                analysis = analyze_text_for_themes(st.session_state.transcribed_text)
                
                st.markdown("**📊 Temas Identificados:**")
                for theme, data in list(analysis['all_themes'].items())[:3]:
                    st.markdown(f"• **{theme.title()}** ({data['confidence']}%)")
                
                if analysis['primary_theme']:
                    st.success(f"Tema principal: **{analysis['primary_theme'].title()}**")
        
        if st.session_state.transcribed_text and st.button("📄 Gerar Resumo", use_container_width=True):
            with st.spinner("Gerando resumo..."):
                text = st.session_state.transcribed_text
                sentences = re.split(r'[.!?]+', text)
                
                summary = ' '.join(sentences[:3])
                st.markdown("**📄 Resumo:**")
                st.info(summary)
        
        if st.session_state.transcribed_text and st.button("🔪 Dividir em Partes", use_container_width=True):
            if st.session_state.audio_info and 'duration' in st.session_state.audio_info:
                segments = segment_text_by_time(
                    st.session_state.transcribed_text,
                    st.session_state.audio_info['duration'],
                    num_segments=8
                )
                st.session_state.text_segments = segments
                st.success(f"Texto dividido em {len(segments)} segmentos!")
            else:
                st.warning("Informações de áudio não disponíveis para divisão por tempo")
        
        if st.session_state.transcribed_text:
            st.markdown("---")
            st.markdown("**💾 Exportar:**")
            
            text_bytes = st.session_state.transcribed_text.encode('utf-8')
            st.download_button(
                label="📥 Baixar TXT",
                data=text_bytes,
                file_name=f"transcricao_{st.session_state.project_name}.txt",
                mime="text/plain",
                use_container_width=True
            )

def render_edit_tab():
    st.markdown("### ✂️ Edição de Vídeo")
    
    if not st.session_state.video_parts and st.session_state.video_path:
        if st.button("🔪 Dividir Vídeo em Partes", type="primary", use_container_width=True):
            with st.spinner("Dividindo vídeo em partes..."):
                parts = split_video_into_parts(st.session_state.video_path)
                if parts:
                    st.session_state.video_parts = parts
                    st.session_state.is_partitioned = True
                    st.success(f"Vídeo dividido em {len(parts)} partes!")
                    st.rerun()
                else:
                    st.error("Falha ao dividir o vídeo")
    
    if st.session_state.video_parts:
        total_duration = sum(p.duration for p in st.session_state.video_parts if hasattr(p, 'duration'))
        
        st.markdown('<div class="timeline-container">', unsafe_allow_html=True)
        
        for part in st.session_state.video_parts:
            if part.duration > 0 and total_duration > 0:
                width_percent = (part.duration / total_duration) * 100
                left_percent = (part.start_time / total_duration) * 100
                
                status_color = "#4cc9f0" if part.status != "error" else "#ff375f"
                
                st.markdown(f"""
                <div class="timeline-segment" style="left: {left_percent}%; width: {width_percent}%; background: linear-gradient(90deg, {status_color}, {status_color}cc);"
                     title="Parte {part.part_id}: {part.start_time:.1f}s - {part.end_time:.1f}s">
                    <div style="font-size: 0.7rem;">{part.part_id}</div>
                    <div style="font-size: 0.6rem;">{part.duration:.0f}s</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("#### 📋 Partes do Vídeo")
        
        for i, part in enumerate(st.session_state.video_parts):
            with st.expander(f"Parte {part.part_id}: {part.start_time:.1f}s - {part.end_time:.1f}s ({part.duration:.1f}s)", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if os.path.exists(part.output_path):
                        try:
                            with open(part.output_path, 'rb') as f:
                                video_bytes = f.read()
                            st.video(video_bytes, format='video/mp4')
                        except Exception as e:
                            st.warning(f"Não foi possível carregar esta parte: {str(e)}")
                    else:
                        st.warning("Arquivo da parte não encontrado")
                    
                    st.markdown("##### 🎨 Efeitos Visuais")
                    selected_effects = st.multiselect(
                        f"Selecione efeitos - Parte {part.part_id}",
                        list(VIDEO_EFFECTS.keys()),
                        format_func=lambda x: VIDEO_EFFECTS[x]['name'],
                        key=f"effects_{i}"
                    )
                    
                    if selected_effects and st.button(f"Aplicar Efeitos - Parte {part.part_id}", key=f"apply_{i}"):
                        with st.spinner(f"Aplicando efeitos na parte {part.part_id}..."):
                            for effect in selected_effects:
                                new_path = apply_video_effect(part.output_path, effect)
                                if new_path != part.output_path:
                                    part.output_path = new_path
                                    part.effects.append(effect)
                            st.success("Efeitos aplicados!")
                
                with col2:
                    st.markdown("##### ⚡ Ações Rápidas")
                    
                    if st.button(f"👁️ Visualizar", key=f"view_{i}", use_container_width=True):
                        st.session_state.selected_part_index = i
                    
                    if st.button(f"🔊 Extrair Áudio", key=f"extract_{i}", use_container_width=True):
                        with st.spinner("Extraindo áudio..."):
                            audio_path = extract_audio_from_video(part.output_path)
                            if audio_path:
                                part.audio_path = audio_path
                                st.success("Áudio extraído!")
                    
                    if st.button(f"🎨 Pré-visualizar", key=f"preview_{i}", use_container_width=True):
                        if os.path.exists(part.output_path):
                            with open(part.output_path, 'rb') as f:
                                st.video(f.read())
                    
                    st.markdown("##### 📊 Informações")
                    st.markdown(f"**Status:** {part.status}")
                    st.markdown(f"**Tamanho:** {part.size_mb:.1f} MB")
                    if part.effects:
                        st.markdown(f"**Efeitos:** {', '.join(part.effects)}")
    
    elif st.session_state.video_path:
        st.info("Clique em 'Dividir Vídeo em Partes' para começar a edição")
    else:
        st.info("Faça upload de um vídeo na barra lateral para começar a edição")

def render_audio_tab():
    st.markdown("### 🔊 Edição de Áudio")
    
    with st.expander("🔧 Testar Todas as Vozes", expanded=False):
        if st.button("🎙️ Testar Todas as Vozes", use_container_width=True):
            working, non_working = test_all_voices()
            st.success(f"✅ Vozes funcionando: {', '.join(working)}")
            if non_working:
                st.warning(f"❌ Vozes não funcionando: {', '.join(non_working)}")
    
    if st.session_state.audio_path:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            try:
                with open(st.session_state.audio_path, 'rb') as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format='audio/mp3')
            except:
                st.warning("Não foi possível carregar o áudio")
            
            if st.session_state.audio_info:
                info = st.session_state.audio_info
                col_info1, col_info2, col_info3 = st.columns(3)
                with col_info1:
                    st.metric("⏱️ Duração", f"{info.get('duration', 0):.1f}s")
                with col_info2:
                    st.metric("📦 Tamanho", f"{info.get('size_mb', 0):.1f} MB")
                with col_info3:
                    st.metric("🎵 Formato", info.get('format', 'Desconhecido'))
            
            st.markdown("#### 🎚️ Efeitos de Áudio")
            
            selected_audio_effects = st.multiselect(
                "Selecione efeitos para aplicar",
                list(AUDIO_EFFECTS.keys()),
                format_func=lambda x: AUDIO_EFFECTS[x]['name'],
                key="audio_effects_select"
            )
            
            if selected_audio_effects:
                st.markdown("##### ⚙️ Configurações dos Efeitos")
                
                effect_params = {}
                for effect in selected_audio_effects:
                    with st.expander(f"⚙️ {AUDIO_EFFECTS[effect]['name']}", expanded=True):
                        st.write(AUDIO_EFFECTS[effect]['description'])
                        
                        params_container = st.container()
                        with params_container:
                            for param, value in AUDIO_EFFECTS[effect]['params'].items():
                                if isinstance(value, (int, float)):
                                    if isinstance(value, int):
                                        min_val = -100 if param == 'threshold' else 0
                                        max_val = 100 if param == 'threshold' else 10
                                        step = 1
                                    else:
                                        min_val = 0.0
                                        max_val = 2.0
                                        step = 0.1
                                    
                                    effect_params[f"{effect}_{param}"] = st.slider(
                                        param.replace('_', ' ').title(),
                                        min_val, max_val, float(value), step,
                                        key=f"audio_effect_{effect}_{param}"
                                    )
                
                if st.button("🎵 Aplicar Efeitos de Áudio", type="primary", use_container_width=True):
                    st.info("Funcionalidade de efeitos de áudio será implementada na próxima versão")
                    st.success("Configurações de efeitos salvas!")
        
        with col2:
            st.markdown("#### 🗣️ Texto para Áudio")
            
            voice_options = list(DEFAULT_VOICE_PROFILES.keys())
            selected_voice = st.selectbox(
                "Voz",
                voice_options,
                format_func=lambda x: DEFAULT_VOICE_PROFILES[x].name,
                index=voice_options.index(st.session_state.selected_voice)
            )
            
            tts_text = st.text_area(
                "Texto para converter em áudio",
                value=st.session_state.tts_text,
                height=150,
                placeholder="Digite o texto que deseja converter em áudio...",
                key="tts_text_input"
            )
            
            if tts_text:
                st.session_state.tts_text = tts_text
                
                col_speed, col_pitch, col_volume = st.columns(3)
                with col_speed:
                    speed = st.slider("Velocidade", 0.5, 2.0, 1.0, 0.1, key="tts_speed")
                with col_pitch:
                    pitch = st.slider("Tom", 0.5, 2.0, 1.0, 0.1, key="tts_pitch")
                with col_volume:
                    volume = st.slider("Volume", 0.0, 2.0, 1.0, 0.1, key="tts_volume")
                
                if st.button("🔊 Converter Texto em Áudio", type="primary", use_container_width=True):
                    with st.spinner("Convertendo texto em áudio..."):
                        voice_profile = DEFAULT_VOICE_PROFILES[selected_voice]
                        voice_profile.speed = speed
                        voice_profile.pitch = pitch
                        voice_profile.volume = volume
                        
                        success, result = text_to_speech_edge(tts_text, voice_profile)
                        
                        if success:
                            try:
                                with open(result, 'rb') as f:
                                    audio_data = f.read()
                                st.audio(audio_data, format='audio/mp3')
                                st.success("Áudio gerado com sucesso!")
                                
                                st.download_button(
                                    label="💾 Baixar Áudio Gerado",
                                    data=audio_data,
                                    file_name=f"tts_{st.session_state.project_name}.mp3",
                                    mime="audio/mp3",
                                    use_container_width=True
                                )
                            except:
                                st.error("Erro ao carregar áudio gerado")
                        else:
                            st.error(f"Falha na conversão: {result}")
            
            st.markdown("#### 🔊 Ajuste de Volume")
            volume_slider = st.slider("Nível de Volume", 0.0, 2.0, 1.0, 0.1, key="volume_slider")
            
            if volume_slider != 1.0 and st.button("🔊 Ajustar Volume do Áudio", use_container_width=True):
                with st.spinner("Ajustando volume..."):
                    output_path = os.path.join(
                        st.session_state.working_dir, 
                        f"volume_adjusted_{os.path.basename(st.session_state.audio_path)}"
                    )
                    if adjust_audio_volume(st.session_state.audio_path, output_path, volume_slider):
                        st.session_state.audio_path = output_path
                        st.session_state.audio_info = get_media_info(output_path, 'audio')
                        st.success("Volume ajustado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Falha ao ajustar volume")
            
            st.markdown("---")
            if os.path.exists(st.session_state.audio_path):
                with open(st.session_state.audio_path, 'rb') as f:
                    audio_data = f.read()
                
                st.download_button(
                    label="💾 Baixar Áudio",
                    data=audio_data,
                    file_name=f"audio_{st.session_state.project_name}.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )
    
    else:
        st.info("""
        **Para editar áudio:**
        
        1. **Faça upload de um áudio** na barra lateral
        2. **Ou extraia áudio de um vídeo** na aba Upload
        3. **Use as ferramentas** de edição disponíveis
        
        **Funcionalidades disponíveis:**
        • 🔊 Ajuste de volume
        • 🎚️ Efeitos de áudio
        • 🗣️ Conversor texto-áudio
        • 💾 Exportação do áudio editado
        """)

def render_ai_tab():
    """Aba de IA e prompts - VERSÃO MODIFICADA para incluir narrativa"""
    
    if st.session_state.get("processing_ai", False):
        st.info("🔄 Processando IA... Por favor, aguarde.")
        st.stop()
    
    st.markdown("### 🤖 Inteligência Artificial Avançada")
    
    # Se houver um template narrativo ativo, mostrar uma mensagem
    if st.session_state.narrative_template:
        st.success(f"🎭 Template narrativo ativo: **{st.session_state.narrative_template.name}**. Os prompts podem ser gerados por ato na aba 'Estrutura Narrativa'.")
    
    tab1, tab2, tab3 = st.tabs(["🎯 Análise de Conteúdo", "🧠 Gerador de Prompts", "⚡ Sugestões de Aprimoramento"])
    
    with tab1:
        st.markdown("#### 🎯 Análise Inteligente de Conteúdo")
        
        if st.session_state.video_path and st.session_state.transcribed_text:
            if not st.session_state.video_analysis_complete:
                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button("🔍 Analisar Conteúdo com IA Avançada", type="primary", use_container_width=True):
                        st.session_state.analyzing_content = True
                        with st.spinner("🤖 Analisando profundamente o conteúdo..."):
                            analysis = analyze_video_content(
                                st.session_state.video_path,
                                st.session_state.transcribed_text
                            )
                            st.session_state.video_analysis = analysis
                            st.session_state.video_analysis_complete = True
                            st.session_state.analyzing_content = False
                            st.success("✅ Análise avançada concluída!")
                with col2:
                    st.info("**Análise Avançada** inclui:\n• Sentimento do conteúdo\n• Público-alvo\n• Estrutura narrativa\n• Palavras-chave otimizadas")
            
            if st.session_state.video_analysis:
                if st.session_state.get("analyzing_content", False):
                    st.info("🔄 Concluindo análise...")
                else:
                    analysis = st.session_state.video_analysis
                    
                    st.markdown("##### 🎨 Temas e Categorias Identificadas")
                    theme_cols = st.columns(min(4, len(analysis.themes)))
                    for idx, theme in enumerate(analysis.themes[:4]):
                        with theme_cols[idx]:
                            theme_score = analysis.theme_scores.get(theme, 0)
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, rgba(76,201,240,0.15), rgba(67,97,238,0.15)); 
                                    padding: 1rem; border-radius: 10px; border-left: 4px solid #4cc9f0;">
                                <h4 style="margin: 0; color: white;">{theme.title()}</h4>
                                <small>Relevância: {theme_score}%</small>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("##### ⭐ Momentos de Destaque")
                    for moment in analysis.key_moments[:5]:
                        with st.expander(f"🎬 Momento {moment.get('time', 0):.0f}s", expanded=False):
                            col_m1, col_m2 = st.columns([3, 1])
                            with col_m1:
                                st.write(f"**Conteúdo:** {moment.get('text', '')}")
                                if moment.get('importance', 0) > 70:
                                    st.info("💡 **Momento de alto impacto**")
                            with col_m2:
                                st.metric("Impacto", f"{moment.get('importance', 0)}%")
                    
                    if analysis.target_audience:
                        st.markdown("##### 👥 Perfil do Público-alvo")
                        st.write(f"**Idade:** {analysis.target_audience.get('age_range', '18-45')}")
                        st.write(f"**Interesses:** {', '.join(analysis.target_audience.get('interests', []))}")
                        st.write(f"**Nível de Conhecimento:** {analysis.target_audience.get('knowledge_level', 'Iniciante/Intermediário')}")
                    
                    st.markdown("##### 😊 Análise de Sentimento")
                    sentiment_cols = st.columns(3)
                    with sentiment_cols[0]:
                        st.metric("Positividade", f"{analysis.sentiment_scores.get('positive', 0)}%")
                    with sentiment_cols[1]:
                        st.metric("Neutralidade", f"{analysis.sentiment_scores.get('neutral', 0)}%")
                    with sentiment_cols[2]:
                        st.metric("Negatividade", f"{analysis.sentiment_scores.get('negative', 0)}%")
        
        else:
            st.info("""
            ### 🎬 Para uma análise completa:
            
            1. **Faça upload de um vídeo** na barra lateral
            2. **Transcreva o áudio** automaticamente
            3. **Clique em "Analisar Conteúdo"** para obter:
               - 🎯 **Temas principais** identificados
               - ⭐ **Momentos-chave** destacados
               - 👥 **Público-alvo** sugerido
               - 😊 **Análise de sentimento**
               - 📊 **Métricas de engajamento**
            
            **Benefícios:**
            • Entenda melhor seu conteúdo
            • Identifique oportunidades de melhoria
            • Otimize para seu público-alvo
            • Crie conteúdo mais engajante
            """)
    
    with tab2:
        st.markdown("#### 🧠 Gerador de Prompts Avançados")
        
        if st.session_state.video_analysis:
            analysis = st.session_state.video_analysis
            
            if analysis.themes:
                st.markdown("##### 🎭 Contexto Baseado na Análise")
                st.success(f"**Tema Principal:** {analysis.themes[0].title()} | **Público:** {analysis.target_audience.get('age_range', 'Adultos')} | **Tom:** {analysis.mood.title()}")
                
                prompt_type = st.selectbox(
                    "🎯 Tipo de Conteúdo para Gerar",
                    ['🎨 Imagem/Visual', '🔊 Áudio/Narração', '🎬 Vídeo/Edição', '📝 Texto/Roteiro', '📊 Storyboard', '🚀 Todos Integrados'],
                    help="Selecione o tipo de conteúdo que deseja criar com IA",
                    key="prompt_type_select_enhanced"
                )
                
                with st.expander("⚙️ Configurações Avançadas do Prompt", expanded=True):
                    col_style, col_tone = st.columns(2)
                    with col_style:
                        style = st.selectbox(
                            "Estilo Visual/Narrativo",
                            ['Realista', 'Cinematográfico', 'Animado', 'Minimalista', 'Futurista', 'Vintage', 'Profissional', 'Casual'],
                            index=1
                        )
                    with col_tone:
                        tone = st.selectbox(
                            "Tom da Comunicação",
                            ['Inspirador', 'Informativo', 'Persuasivo', 'Divertido', 'Emocional', 'Autoritário', 'Amigável', 'Urgente'],
                            index=0
                        )
                    
                    platform = st.multiselect(
                        "📱 Plataformas de Destino",
                        ['YouTube', 'TikTok/Reels', 'Instagram', 'LinkedIn', 'Twitter', 'Site/Blog', 'Apresentação', 'Curso Online'],
                        default=['YouTube', 'TikTok/Reels']
                    )
                    
                    complexity = st.slider(
                        "📈 Nível de Detalhe/Complexidade",
                        1, 5, 3,
                        help="1 = Básico/Simples, 5 = Avançado/Detalhado"
                    )
                
                if st.button("✨ Gerar Prompts Personalizados", type="primary", use_container_width=True, key="generate_enhanced_prompts"):
                    st.session_state.processing_ai = True
                    
                    with st.spinner("🧠 Criando prompts otimizados..."):
                        prompts = generate_enhanced_ai_prompts(
                            analysis=analysis,
                            prompt_type=prompt_type,
                            style=style,
                            tone=tone,
                            platforms=platform,
                            complexity_level=complexity
                        )
                        
                        st.session_state.enhanced_prompts = prompts
                        st.session_state.processing_ai = False
                        
                        st.success(f"✅ {len(prompts)} prompts gerados com sucesso!")
                
                if hasattr(st.session_state, 'enhanced_prompts') and st.session_state.enhanced_prompts:
                    prompts = st.session_state.enhanced_prompts
                    
                    st.markdown("##### ✨ Prompts Gerados (Otimizados)")
                    
                    max_open_expanders = 3
                    prompts_list = list(prompts.items())
                    
                    for idx, (prompt_name, prompt_data) in enumerate(prompts_list):
                        initially_expanded = idx < max_open_expanders
                        
                        with st.expander(f"📋 {prompt_data.get('title', prompt_name.title())}", expanded=initially_expanded):
                            st.markdown(f"**🎯 Objetivo:** {prompt_data.get('purpose', '')}")
                            st.markdown(f"**📊 Nível:** {prompt_data.get('level', 'Intermediário')}")
                            
                            st.markdown("**💡 PROMPT PRINCIPAL:**")
                            st.code(prompt_data['prompt'], language='text')
                            
                            if prompt_data.get('parameters'):
                                st.markdown("**⚙️ Parâmetros Sugeridos:**")
                                params = prompt_data['parameters']
                                for param, value in params.items():
                                    st.write(f"- **{param}:** {value}")
                            
                            if prompt_data.get('example'):
                                with st.expander("📖 Exemplo de Uso", expanded=False):
                                    st.write(prompt_data['example'])
                            
                            col_copy, col_save, col_test = st.columns(3)
                            with col_copy:
                                copy_key = f"copy_{prompt_name}_{st.session_state.get('copy_counter', 0)}"
                                if st.button(f"📋 Copiar", key=copy_key):
                                    st.success("Prompt copiado para área de transferência!")
                            with col_save:
                                save_key = f"save_{prompt_name}_{st.session_state.get('save_counter', 0)}"
                                if st.button(f"💾 Salvar", key=save_key):
                                    prompt_path = os.path.join(
                                        st.session_state.working_dir,
                                        f"prompt_avancado_{prompt_name}_{datetime.now().strftime('%H%M%S')}.txt"
                                    )
                                    with open(prompt_path, 'w', encoding='utf-8') as f:
                                        f.write(json.dumps(prompt_data, ensure_ascii=False, indent=2))
                                    st.success(f"Prompt salvo em: {prompt_path}")
                            with col_test:
                                test_key = f"test_{prompt_name}_{st.session_state.get('test_counter', 0)}"
                                if st.button(f"🚀 Testar", key=test_key):
                                    st.info("Funcionalidade de teste será implementada na próxima versão")
            else:
                st.warning("Não há temas identificados na análise. Faça uma análise completa primeiro.")
    
    with tab3:
        if st.session_state.get("generating_suggestions", False):
            st.info("🔄 Gerando sugestões...")
        else:
            st.markdown("#### ⚡ Sugestões Inteligentes de Aprimoramento")
            
            if st.session_state.video_analysis:
                analysis = st.session_state.video_analysis
                
                st.markdown("##### 📊 Score de Qualidade do Conteúdo")
                quality_score = calculate_content_quality_score(analysis)
                
                col_score, col_gauge = st.columns([2, 1])
                with col_score:
                    st.metric("Pontuação Geral", f"{quality_score}/100")
                    st.progress(quality_score/100)
                
                with col_gauge:
                    if quality_score >= 80:
                        st.success("🎉 Excelente!")
                    elif quality_score >= 60:
                        st.info("👍 Bom")
                    else:
                        st.warning("💡 Pode melhorar")
                
                st.markdown("##### 📈 Análise por Categoria")
                
                categories = ['Conteúdo', 'Engajamento', 'Técnico', 'Narrativa']
                cat_cols = st.columns(len(categories))
                
                for idx, category in enumerate(categories):
                    with cat_cols[idx]:
                        score = calculate_category_score(analysis, category)
                        st.markdown(f"""
                        <div style="text-align: center; padding: 1rem; background: rgba(255,255,255,0.05); border-radius: 10px;">
                            <h4 style="margin: 0;">{category}</h4>
                            <h2 style="margin: 0; color: #4cc9f0;">{score}%</h2>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("##### 🚀 Sugestões Prioritárias de Melhoria")
                
                priority_suggestions = get_priority_suggestions(analysis)
                
                for i, suggestion in enumerate(priority_suggestions[:3]):
                    initially_expanded = i < 2
                    
                    with st.expander(f"🔴 PRIORIDADE {i+1}: {suggestion['title']}", expanded=initially_expanded):
                        st.markdown(f"**📝 Descrição:** {suggestion['description']}")
                        
                        col_imp, col_dif = st.columns(2)
                        with col_imp:
                            st.metric("Impacto", f"{suggestion['impact']}/10")
                        with col_dif:
                            st.metric("Dificuldade", f"{suggestion['difficulty']}/10")
                        
                        st.markdown("**🎯 Ações Recomendadas:**")
                        for action in suggestion['actions']:
                            st.write(f"• {action}")
                        
                        if suggestion.get('ai_prompt'):
                            with st.expander("🤖 Prompt de IA para esta melhoria", expanded=False):
                                st.code(suggestion['ai_prompt'], language='text')
                
                st.markdown("##### ⚡ Melhorias Rápidas (1-2 horas)")
                
                quick_improvements = get_quick_improvements(analysis)
                
                for improvement in quick_improvements[:3]:
                    col_q1, col_q2 = st.columns([3, 1])
                    with col_q1:
                        st.markdown(f"**✅ {improvement['title']}**")
                        st.caption(improvement['description'])
                    with col_q2:
                        apply_key = f"apply_{improvement['id']}_{st.session_state.get('improvement_counter', 0)}"
                        if st.button(f"Aplicar", key=apply_key, use_container_width=True):
                            st.success(f"Melhoria '{improvement['title']}' aplicada!")
                
                st.markdown("##### 📋 Plano de Ação Personalizado")
                
                selected_areas = st.multiselect(
                    "🎯 Áreas para focar",
                    ['Engajamento Inicial', 'Retenção de Audiência', 'Qualidade Visual', 'Áudio Profissional', 
                     'Chamadas para Ação', 'Storytelling', 'Otimização SEO', 'Acessibilidade'],
                    default=['Engajamento Inicial', 'Retenção de Audiência']
                )
                
                if selected_areas and st.button("🎯 Gerar Plano de Ação Detalhado", type="primary", use_container_width=True):
                    st.session_state.generating_suggestions = True
                    with st.spinner("Gerando plano de ação..."):
                        action_plan = generate_action_plan(analysis, selected_areas)
                        st.session_state.generated_action_plan = action_plan
                        st.session_state.generating_suggestions = False
                        st.success("Plano de ação gerado!")
                
                if hasattr(st.session_state, 'generated_action_plan') and st.session_state.generated_action_plan:
                    action_plan = st.session_state.generated_action_plan
                    
                    st.markdown("##### 📅 Plano de Implementação")
                    
                    for area, plan in action_plan.items():
                        with st.expander(f"📌 {area}", expanded=True):
                            st.markdown(f"**🎯 Objetivo:** {plan['objective']}")
                            
                            st.markdown("**📝 Tarefas:**")
                            for task in plan['tasks']:
                                status = "✅" if task.get('completed', False) else "⏳"
                                st.write(f"{status} **{task['task']}** (Tempo: {task['time_estimate']})")
                            
                            st.markdown(f"**⏱️ Tempo Total Estimado:** {plan['total_time']}")
                            
                            checklist_key = f"checklist_{area}_{st.session_state.get('checklist_counter', 0)}"
                            if st.button(f"📥 Baixar Checklist - {area}", key=checklist_key):
                                st.success(f"Checklist para {area} pronto para download!")
            
            else:
                st.info("""
                ### ⚡ Para Sugestões Personalizadas:
                
                1. **Analise seu conteúdo** na primeira aba
                2. **Receba avaliações** em tempo real
                3. **Obtenha recomendações** específicas
                
                **O que você vai receber:**
                
                🚀 **Sugestões Prioritárias**
                • Baseadas em análise de IA
                • Ordenadas por impacto
                • Com ações concretas
                
                ⚡ **Melhorias Rápidas**
                • Implementação em 1-2 horas
                • Alto impacto visual/auditivo
                • Fáceis de aplicar
                
                📋 **Planos de Ação**
                • Personalizados para seu conteúdo
                • Com prazos realistas
                • Checklists práticos
                
                🎯 **Pontuação de Qualidade**
                • Avaliação objetiva
                • Comparativos por categoria
                • Metas de melhoria
                """)

def render_export_tab():
    """Aba de exportação - MODIFICADA para incluir renderização por atos"""
    st.markdown("### 💾 Exportação e Finalização")
    
    if st.session_state.video_parts or st.session_state.audio_path or st.session_state.narrative_template:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎥 Configurações de Vídeo")
            
            format_options = ['MP4', 'MOV', 'AVI', 'WMV', 'MKV']
            export_format = st.selectbox("Formato", format_options, key="export_format")
            
            resolution_options = ['640x360', '854x480', '1280x720', '1920x1080', '3840x2160']
            resolution = st.selectbox("Resolução", resolution_options, index=3, key="export_resolution")
            
            fps_options = [24, 25, 30, 50, 60]
            fps = st.selectbox("FPS", fps_options, index=2, key="export_fps")
            
            quality = st.select_slider(
                "Qualidade",
                options=['Baixa', 'Média', 'Alta', 'Máxima'],
                value='Alta',
                key="export_quality"
            )
        
        with col2:
            st.markdown("#### 🔊 Configurações de Áudio")
            
            audio_bitrate = st.selectbox(
                "Bitrate de Áudio",
                ['64k', '128k', '192k', '256k', '320k'],
                index=2,
                key="audio_bitrate"
            )
            
            audio_channels = st.radio("Canais", ['Mono', 'Estéreo'], index=1, key="audio_channels")
            
            st.markdown("#### 📦 O que exportar?")
            
            export_options = []
            if st.session_state.video_parts:
                export_options.append("Vídeo editado (partes)")
            if st.session_state.audio_path:
                export_options.append("Áudio editado")
            if st.session_state.transcribed_text:
                export_options.append("Texto transcrito")
            if st.session_state.video_analysis:
                export_options.append("Análise IA")
            
            # Opção narrativa
            if st.session_state.narrative_template:
                export_options.append("Vídeo narrativo (atos concatenados)")
            
            selected_exports = st.multiselect(
                "Selecione os itens para exportar",
                export_options,
                default=export_options[:1] if export_options else [],
                key="export_selections"
            )
        
        st.markdown("#### 👁️ Pré-visualização")
        
        if "Vídeo editado (partes)" in selected_exports and st.session_state.video_parts:
            first_part = st.session_state.video_parts[0]
            if os.path.exists(first_part.output_path):
                try:
                    with open(first_part.output_path, 'rb') as f:
                        video_bytes = f.read()
                    st.video(video_bytes, format='video/mp4')
                    st.caption(f"Pré-visualização: Parte 1 de {len(st.session_state.video_parts)}")
                except:
                    st.warning("Não foi possível carregar pré-visualização")
        
        st.markdown("---")
        
        export_button = st.button("🚀 EXPORTAR TUDO", type="primary", use_container_width=True, key="export_all_button")
        
        if export_button:
            with st.spinner("Preparando exportação..."):
                export_dir = os.path.join(st.session_state.working_dir, "export")
                os.makedirs(export_dir, exist_ok=True)
                
                exported_files = []
                
                # Exporta vídeo por partes
                if "Vídeo editado (partes)" in selected_exports and st.session_state.video_parts:
                    try:
                        list_file = os.path.join(export_dir, "concat_list.txt")
                        
                        valid_parts = [p for p in st.session_state.video_parts if os.path.exists(p.output_path)]
                        
                        if valid_parts:
                            with open(list_file, 'w', encoding='utf-8') as f:
                                for part in valid_parts:
                                    f.write(f"file '{os.path.abspath(part.output_path)}'\n")
                            
                            output_video = os.path.join(export_dir, f"{st.session_state.project_name}.{export_format.lower()}")
                            
                            bitrate_map = {
                                'Baixa': '1000k',
                                'Média': '2500k',
                                'Alta': '5000k',
                                'Máxima': '8000k'
                            }
                            video_bitrate = bitrate_map.get(quality, '5000k')
                            
                            cmd = [
                                'ffmpeg', '-f', 'concat', '-safe', '0',
                                '-i', list_file,
                                '-c:v', 'libx264',
                                '-s', resolution,
                                '-r', str(fps),
                                '-b:v', video_bitrate,
                                '-c:a', 'aac',
                                '-b:a', audio_bitrate,
                                '-ar', '44100',
                                '-ac', '2' if audio_channels == 'Estéreo' else '1',
                                '-preset', 'medium',
                                output_video, '-y'
                            ]
                            
                            progress_text = st.empty()
                            progress_bar = st.progress(0)
                            progress_text.text("Exportando vídeo...")
                            
                            try:
                                process = subprocess.run(cmd, capture_output=True, text=True)
                                if process.returncode == 0:
                                    exported_files.append(output_video)
                                    progress_bar.progress(1.0)
                                    progress_text.text("Vídeo exportado com sucesso!")
                                else:
                                    st.error(f"Erro ao exportar vídeo: {process.stderr[:200]}")
                            except Exception as e:
                                st.error(f"Erro: {str(e)}")
                        else:
                            st.warning("Nenhuma parte válida para exportar")
                    except Exception as e:
                        st.error(f"Erro ao processar vídeo: {str(e)}")
                
                # Exporta vídeo narrativo (atos concatenados)
                if "Vídeo narrativo (atos concatenados)" in selected_exports and st.session_state.narrative_template:
                    template = st.session_state.narrative_template
                    videos_to_concat = []
                    
                    # Verifica se cada ato tem um vídeo associado
                    for act in template.acts:
                        if hasattr(act, 'video_path') and act.video_path and os.path.exists(act.video_path):
                            videos_to_concat.append(act.video_path)
                        else:
                            st.warning(f"Ato {act.number} não possui vídeo gerado. Ignorando.")
                    
                    if videos_to_concat:
                        list_file = os.path.join(export_dir, "concat_narrative.txt")
                        with open(list_file, 'w', encoding='utf-8') as f:
                            for v in videos_to_concat:
                                f.write(f"file '{os.path.abspath(v)}'\n")
                        
                        output_narrative = os.path.join(export_dir, f"{st.session_state.project_name}_narrative.mp4")
                        cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output_narrative, '-y']
                        try:
                            subprocess.run(cmd, capture_output=True, check=True)
                            exported_files.append(output_narrative)
                            st.success("Vídeo narrativo gerado!")
                        except Exception as e:
                            st.error(f"Erro ao concatenar atos: {str(e)}")
                    else:
                        st.warning("Nenhum vídeo de ato encontrado para exportar o vídeo narrativo.")
                
                # Exporta áudio
                if "Áudio editado" in selected_exports and st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
                    try:
                        output_audio = os.path.join(export_dir, f"{st.session_state.project_name}_audio.mp3")
                        shutil.copy2(st.session_state.audio_path, output_audio)
                        exported_files.append(output_audio)
                        st.success("Áudio exportado!")
                    except Exception as e:
                        st.error(f"Erro ao exportar áudio: {str(e)}")
                
                # Exporta texto
                if "Texto transcrito" in selected_exports and st.session_state.transcribed_text:
                    try:
                        output_text = os.path.join(export_dir, f"{st.session_state.project_name}_transcricao.txt")
                        with open(output_text, 'w', encoding='utf-8') as f:
                            f.write(st.session_state.transcribed_text)
                        exported_files.append(output_text)
                        st.success("Texto exportado!")
                    except Exception as e:
                        st.error(f"Erro ao exportar texto: {str(e)}")
                
                # Exporta análise IA
                if "Análise IA" in selected_exports and st.session_state.video_analysis:
                    try:
                        output_analysis = os.path.join(export_dir, f"{st.session_state.project_name}_analise_ia.json")
                        with open(output_analysis, 'w', encoding='utf-8') as f:
                            json.dump(asdict(st.session_state.video_analysis), f, ensure_ascii=False, indent=2)
                        exported_files.append(output_analysis)
                        st.success("Análise IA exportada!")
                    except Exception as e:
                        st.error(f"Erro ao exportar análise: {str(e)}")
                
                if exported_files:
                    st.success(f"✅ Exportação concluída! {len(exported_files)} arquivos exportados.")
                    
                    for file in exported_files:
                        if os.path.exists(file):
                            file_name = os.path.basename(file)
                            file_size = os.path.getsize(file) / (1024 * 1024)
                            
                            with open(file, 'rb') as f:
                                file_data = f.read()
                            
                            if file.endswith('.mp4') or file.endswith('.avi') or file.endswith('.mov'):
                                mime_type = "video/mp4"
                            elif file.endswith('.mp3'):
                                mime_type = "audio/mp3"
                            elif file.endswith('.txt'):
                                mime_type = "text/plain"
                            elif file.endswith('.json'):
                                mime_type = "application/json"
                            else:
                                mime_type = "application/octet-stream"
                            
                            st.download_button(
                                label=f"⬇️ Baixar {file_name} ({file_size:.1f} MB)",
                                data=file_data,
                                file_name=file_name,
                                mime=mime_type,
                                key=f"download_{file_name}_{uuid.uuid4().hex[:8]}"
                            )
                else:
                    st.error("Nenhum arquivo foi exportado.")
    
    else:
        st.info("""
        **Para exportar seu trabalho:**
        
        1. **Edite um vídeo ou áudio** nas abas anteriores
        2. **Configure as opções** de exportação acima
        3. **Selecione** o que deseja exportar
        4. **Clique em EXPORTAR TUDO**
        
        **Formatos suportados:**
        • 🎥 Vídeo: MP4, MOV, AVI, WMV, MKV
        • 🔊 Áudio: MP3
        • 📝 Texto: TXT
        • 🧠 Análise: JSON
        """)

def render_text_to_video_tab():
    st.markdown("### 📝 Criar Vídeo a partir de Texto")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### ✍️ Escreva o texto do vídeo")
        text_input = st.text_area(
            "Texto para narração",
            value=st.session_state.get('tts_text', ''),
            height=200,
            placeholder="Digite aqui o texto que será transformado em áudio e vídeo...",
            key="text_to_video_input"
        )
        
        if text_input:
            st.session_state.tts_text = text_input
            
            st.markdown("#### 🎤 Configurações de Voz")
            voice_options = list(DEFAULT_VOICE_PROFILES.keys())
            selected_voice = st.selectbox(
                "Voz",
                voice_options,
                format_func=lambda x: DEFAULT_VOICE_PROFILES[x].name,
                key="ttv_voice"
            )
            
            col_speed, col_pitch, col_vol = st.columns(3)
            with col_speed:
                speed = st.slider("Velocidade", 0.5, 2.0, 1.0, 0.1, key="ttv_speed")
            with col_pitch:
                pitch = st.slider("Tom", 0.5, 2.0, 1.0, 0.1, key="ttv_pitch")
            with col_vol:
                volume = st.slider("Volume", 0.0, 2.0, 1.0, 0.1, key="ttv_volume")
            
            st.markdown("#### 🖼️ Background do Vídeo")
            bg_option = st.radio(
                "Tipo de fundo",
                ["Cor sólida", "Imagem", "Vídeo"],
                horizontal=True,
                key="bg_type"
            )
            
            bg_color = "#000000"
            bg_file = None
            if bg_option == "Cor sólida":
                bg_color = st.color_picker("Cor de fundo", "#000000", key="bg_color")
            else:
                uploaded_bg = st.file_uploader(
                    f"Selecione um arquivo de {bg_option.lower()}",
                    type=['jpg', 'jpeg', 'png', 'mp4'] if bg_option == "Imagem" else ['mp4', 'mov', 'avi'],
                    key=f"bg_upload_{bg_option}"
                )
                if uploaded_bg:
                    bg_ext = "jpg" if bg_option == "Imagem" else "mp4"
                    bg_path = os.path.join(st.session_state.working_dir, f"bg_{uuid.uuid4().hex[:8]}.{bg_ext}")
                    with open(bg_path, 'wb') as f:
                        f.write(uploaded_bg.getvalue())
                    bg_file = bg_path
            
            st.markdown("#### ⚙️ Configurações de Vídeo")
            col_res, col_fps = st.columns(2)
            with col_res:
                resolution = st.selectbox(
                    "Resolução",
                    ['640x360', '854x480', '1280x720', '1920x1080'],
                    index=2,
                    key="ttv_res"
                )
            with col_fps:
                fps = st.selectbox("FPS", [24, 25, 30], index=1, key="ttv_fps")
            
            if st.button("🎬 GERAR VÍDEO", type="primary", use_container_width=True):
                if not text_input.strip():
                    st.warning("Digite algum texto.")
                else:
                    with st.spinner("Gerando áudio e vídeo..."):
                        voice_profile = DEFAULT_VOICE_PROFILES[selected_voice]
                        voice_profile.speed = speed
                        voice_profile.pitch = pitch
                        voice_profile.volume = volume
                        
                        success, audio_result = text_to_speech_edge(text_input, voice_profile)
                        if not success:
                            st.error(f"Falha na geração de áudio: {audio_result}")
                            st.stop()
                        
                        audio_path = audio_result
                        
                        audio_info = get_media_info(audio_path, 'audio')
                        audio_duration = audio_info.get('duration', 5)
                        
                        output_video = os.path.join(
                            st.session_state.working_dir,
                            f"text_to_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                        )
                        
                        if create_video_from_text(
                            audio_path=audio_path,
                            output_path=output_video,
                            duration=audio_duration,
                            bg_type=bg_option.lower(),
                            bg_color=bg_color,
                            bg_file=bg_file,
                            resolution=resolution,
                            fps=fps
                        ):
                            st.session_state.generated_video = output_video
                            st.success("✅ Vídeo gerado com sucesso!")
                        else:
                            st.error("Erro ao criar o vídeo.")
    
    with col2:
        st.markdown("#### 🎬 Pré‑visualização")
        if 'generated_video' in st.session_state and os.path.exists(st.session_state.generated_video):
            try:
                with open(st.session_state.generated_video, 'rb') as f:
                    video_data = f.read()
                st.video(video_data)
                
                st.download_button(
                    label="💾 Baixar Vídeo",
                    data=video_data,
                    file_name=f"texto_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
            except Exception as e:
                st.warning(f"Erro ao carregar vídeo: {e}")
        else:
            st.info("Após gerar, o vídeo aparecerá aqui.")

def render_upload_tab():
    st.markdown("### 📤 Upload e Visualização")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎥 Visualizador de Vídeo")
        
        if st.session_state.video_path and os.path.exists(st.session_state.video_path):
            info = st.session_state.video_info
            if info:
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.metric("Duração", f"{info.get('duration', 0):.1f}s")
                    st.metric("Resolução", info.get('resolution', 'Desconhecida'))
                with col_info2:
                    st.metric("Tamanho", f"{info.get('size_mb', 0):.1f} MB")
                    st.metric("Formato", info.get('format', 'Desconhecido'))
            
            try:
                with open(st.session_state.video_path, 'rb') as f:
                    video_bytes = f.read()
                st.video(video_bytes, format='video/mp4')
            except Exception as e:
                st.warning(f"Não foi possível carregar o vídeo: {str(e)}")
            
            col_actions1, col_actions2 = st.columns(2)
            with col_actions1:
                if st.button("🎵 Extrair Áudio do Vídeo", use_container_width=True, key="extract_audio_button"):
                    with st.spinner("Extraindo áudio..."):
                        audio_path = extract_audio_from_video(st.session_state.video_path)
                        if audio_path:
                            st.session_state.audio_path = audio_path
                            st.session_state.audio_info = get_media_info(audio_path, 'audio')
                            st.success("Áudio extraído com sucesso!")
                            st.rerun()
                        else:
                            st.error("Falha ao extrair áudio")
            with col_actions2:
                if st.button("🔪 Dividir em Partes", use_container_width=True, key="split_button_upload"):
                    with st.spinner("Dividindo vídeo..."):
                        parts = split_video_into_parts(st.session_state.video_path, 60)
                        if parts:
                            st.session_state.video_parts = parts
                            st.session_state.is_partitioned = True
                            st.success(f"Vídeo dividido em {len(parts)} partes!")
                            st.rerun()
        
        else:
            st.info("Faça upload de um vídeo na barra lateral")
    
    with col2:
        st.markdown("#### 🔊 Visualizador de Áudio")
        
        if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
            info = st.session_state.audio_info
            if info:
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.metric("Duração", f"{info.get('duration', 0):.1f}s")
                    st.metric("Taxa de Bits", f"{info.get('bitrate', '0')[:4]} kbps")
                with col_info2:
                    st.metric("Tamanho", f"{info.get('size_mb', 0):.1f} MB")
                    st.metric("Taxa de Amostragem", f"{info.get('sample_rate', '0')[:4]} Hz")
            
            try:
                with open(st.session_state.audio_path, 'rb') as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format='audio/mp3')
            except:
                st.warning("Não foi possível carregar o áudio")
            
            if st.button("📝 Transcrever Áudio com IA", type="primary", use_container_width=True, key="transcribe_button"):
                with st.spinner("Transcrevendo com Whisper..."):
                    text = transcribe_audio_with_whisper(st.session_state.audio_path)
                    st.session_state.transcribed_text = text
                    
                    if info and 'duration' in info:
                        segments = segment_text_by_time(text, info['duration'])
                        st.session_state.text_segments = segments
                    
                    st.success("Transcrição concluída!")
                    st.rerun()
        
        else:
            st.info("Faça upload de um áudio ou extraia do vídeo")

# ==========================
# FUNÇÃO DE SEGMENTAÇÃO ROBUSTA
# ==========================
def extract_segments_from_conversation(text: str) -> List[Dict]:
    """
    Extrai segmentos de um texto de conversa/roteiro.
    Agrupa por parágrafos (linhas em branco) e reconhece títulos.
    Retorna lista de dicionários com 'title', 'text', 'scene_desc', 'time_start', 'time_end'.
    """
    lines = text.split('\n')
    segments = []
    current_title = ""
    current_text = []
    current_scene = ""
    time_pattern = re.compile(r'\((\d+):(\d+)\s*[–\-]\s*(\d+):(\d+)\)')

    title_patterns = [
        r'^##\s*(.+)',           # Título markdown nível 2
        r'^###\s*(.+)',          # Título markdown nível 3
        r'^PARTE\s*(\d+)',       # "PARTE 1"
        r'^Cena\s*(\d+)',        # "Cena 1"
        r'^\[(.*?)\]',           # [Título entre colchetes]
        r'^\*\*(.+?)\*\*',       # **Título em negrito**
        r'^📍?\s*(.+)',           # Título com emoji de localização
    ]

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        line_stripped = line.strip()

        # Linha em branco indica fim de parágrafo – fecha segmento atual
        if not line_stripped and current_text:
            segments.append({
                'title': current_title,
                'text': '\n'.join(current_text).strip(),
                'scene_desc': current_scene,
                'time_start': None,
                'time_end': None
            })
            current_title = ""
            current_text = []
            current_scene = ""
            i += 1
            continue

        if line_stripped:
            # Verifica se é título
            title_match = None
            for pat in title_patterns:
                m = re.match(pat, line_stripped)
                if m:
                    title_match = m.group(1).strip()
                    break
            if title_match:
                # Salva segmento anterior
                if current_title or current_text:
                    segments.append({
                        'title': current_title,
                        'text': '\n'.join(current_text).strip(),
                        'scene_desc': current_scene,
                        'time_start': None,
                        'time_end': None
                    })
                current_title = title_match
                current_text = []
                current_scene = ""
                i += 1
                continue

            # Verifica se é descrição de cena (ex: "Cena: ...")
            if line_stripped.lower().startswith('cena:') or line_stripped.lower().startswith('**cena:**'):
                current_scene = line_stripped.split(':', 1)[-1].strip()
            else:
                # Adiciona linha ao texto atual
                current_text.append(line)
        i += 1

    # Último segmento
    if current_title or current_text:
        segments.append({
            'title': current_title,
            'text': '\n'.join(current_text).strip(),
            'scene_desc': current_scene,
            'time_start': None,
            'time_end': None
        })

    # Extrai tempos se houver no texto
    for seg in segments:
        combined = seg['title'] + " " + seg['text']
        match = time_pattern.search(combined)
        if match:
            h1, m1, h2, m2 = map(int, match.groups())
            seg['time_start'] = h1 * 60 + m1
            seg['time_end'] = h2 * 60 + m2

    return segments

# ==========================
# FUNÇÕES PARA GERAÇÃO DE VÍDEO POR SEGMENTO
# ==========================
def generate_segment_video(segment_text: str, analysis: Dict, output_path: str, 
                           voice_profiles: Dict, music_library: Dict) -> bool:
    """
    Gera um vídeo para um segmento de texto.
    - analysis: dicionário com 'tone', 'style', 'keywords', etc.
    - voice_profiles: dicionário mapeando tom para VoiceProfile
    - music_library: dicionário mapeando tom para caminho de arquivo de música
    Retorna True se sucesso.
    """
    try:
        # 1. Seleciona perfil de voz baseado no tom
        tone = analysis.get('tone', 'Informativo')
        voice_key = TONE_TO_VOICE.get(tone, 'masculina_padrao')
        voice_profile = voice_profiles[voice_key]

        # 2. Gera áudio TTS
        audio_path = output_path.replace('.mp4', '_audio.mp3')
        success, audio_result = text_to_speech_edge(segment_text, voice_profile, audio_path)
        if not success:
            st.error(f"Falha no TTS: {audio_result}")
            return False

        # 3. Obtém duração do áudio
        audio_info = get_media_info(audio_path, 'audio')
        audio_duration = audio_info.get('duration', 5)

        # 4. Seleciona música de fundo (se disponível)
        music_path = music_library.get(tone, music_library.get('default', None))
        final_audio = audio_path
        mixed_audio_path = None
        if music_path and os.path.exists(music_path):
            # Mixa música com áudio (volume reduzido)
            mixed_audio_path = output_path.replace('.mp4', '_mixed.mp3')
            mix_audio_with_music(audio_path, music_path, mixed_audio_path, music_volume=0.3)
            final_audio = mixed_audio_path

        # 5. Cria vídeo com fundo escuro e texto animado
        video_path = output_path
        create_text_video(
            text=segment_text,
            audio_path=final_audio,
            output_path=video_path,
            duration=audio_duration,
            bg_color="#000000",
            text_color="#FFFFFF",
            font_size=48,
            resolution="1920x1080",
            fps=30
        )

        # 6. Limpeza (remove arquivos temporários)
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if mixed_audio_path and os.path.exists(mixed_audio_path):
            os.remove(mixed_audio_path)

        return True

    except Exception as e:
        st.error(f"Erro ao gerar vídeo do segmento: {str(e)}")
        traceback.print_exc()
        return False

def create_text_video(text: str, audio_path: str, output_path: str, duration: float,
                      bg_color="#000000", text_color="#FFFFFF", font_size=48,
                      resolution="1920x1080", fps=30):
    """
    Cria um vídeo com fundo colorido e texto centralizado.
    O texto é dividido em linhas para caber na tela.
    """
    width, height = map(int, resolution.split('x'))
    
    # Prepara o texto: quebra em linhas de no máximo 60 caracteres
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= 60:
            current_line += " " + word if current_line else word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    
    # Converte para string com quebras de linha
    multiline_text = "\\n".join(lines)  # para usar no drawtext
    
    # Escapa caracteres especiais para ffmpeg
    multiline_text = multiline_text.replace("'", r"\'").replace(":", r"\:")
    
    # Comando ffmpeg: fundo colorido com texto centralizado
    cmd = [
        'ffmpeg',
        '-f', 'lavfi', '-i', f"color=c={bg_color}:s={resolution}:d={duration}:r={fps}",
        '-i', audio_path,
        '-vf', f"drawtext=text='{multiline_text}':fontcolor={text_color}:fontsize={font_size}:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=10",
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest', '-y', output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Erro ffmpeg: {e.stderr.decode()}")
        return False

def mix_audio_with_music(voice_audio: str, music_audio: str, output_path: str, music_volume=0.3):
    """
    Mixa voz e música, reduzindo o volume da música.
    """
    cmd = [
        'ffmpeg',
        '-i', voice_audio,
        '-i', music_audio,
        '-filter_complex', f'[1:a]volume={music_volume}[music]; [0:a][music]amix=inputs=2:duration=longest',
        '-c:a', 'libmp3lame', '-q:a', '2',
        output_path, '-y'
    ]
    subprocess.run(cmd, capture_output=True, check=True)

def concatenate_videos(video_paths: List[str], output_path: str) -> bool:
    """Concatena vários vídeos usando ffmpeg."""
    list_file = os.path.join(os.path.dirname(output_path), "concat_list.txt")
    with open(list_file, 'w') as f:
        for v in video_paths:
            f.write(f"file '{os.path.abspath(v)}'\n")
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', list_file,
        '-c', 'copy',
        output_path, '-y'
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Erro na concatenação: {e.stderr.decode()}")
        return False
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)

def analyze_segment_enhanced(segment_text: str, scene_desc: str = "") -> Dict:
    """
    Analisa um segmento individual para determinar:
        - tema principal
        - palavras-chave
        - sentimento (positivo, negativo, neutro)
        - tom sugerido (inspirador, informativo, etc.)
        - estilo visual sugerido
        - palavras que indicam necessidade de efeitos sonoros
    """
    theme_analysis = analyze_text_for_themes(segment_text)
    primary_theme = theme_analysis.get('primary_theme', 'geral')
    keywords = extract_optimized_keywords(segment_text, max_keywords=5)

    sentiment = analyze_sentiment_enhanced(segment_text)

    tone = "Informativo"
    if sentiment['positive'] > 60:
        tone = "Inspirador"
    elif sentiment['negative'] > 40:
        tone = "Urgente"
    emotional_words = ['incrível', 'fantástico', 'surpreendente', 'revolucionário', 'poderoso']
    if any(w in segment_text.lower() for w in emotional_words):
        tone = "Empolgante"

    style_map = {
        'educação': 'Profissional e didático',
        'tecnologia': 'Futurista e minimalista',
        'marketing': 'Persuasivo e vibrante',
        'entretenimento': 'Animado e colorido',
        'saúde': 'Calmo e clean',
        'negócios': 'Sóbrio e profissional'
    }
    style = style_map.get(primary_theme, 'Cinematográfico')

    sound_effects_keywords = ['explosão', 'batida', 'alarme', 'passos', 'porta', 'chuva', 'trovão', 'aplausos', 'risos']
    effects_needed = [word for word in sound_effects_keywords if word in segment_text.lower()]

    return {
        'primary_theme': primary_theme,
        'keywords': keywords,
        'sentiment': sentiment,
        'tone': tone,
        'style': style,
        'effects_needed': effects_needed,
        'scene_desc': scene_desc
    }

def generate_multimedia_prompts(segment_analysis: Dict, user_style: str = None, user_tone: str = None, original_text: str = "") -> Dict:
    """
    Gera prompts para diferentes mídias com base na análise, preferências do usuário e o texto original do segmento.
    Retorna dicionário com prompts para imagem, música, efeitos sonoros e narração.
    """
    theme = segment_analysis['primary_theme']
    keywords = segment_analysis['keywords']
    tone = user_tone or segment_analysis['tone']
    style = user_style or segment_analysis['style']
    scene_desc = segment_analysis.get('scene_desc', '')
    effects = segment_analysis.get('effects_needed', [])
    
    context = original_text[:300] + "..." if len(original_text) > 300 else original_text

    if scene_desc:
        image_prompt = f"Crie uma imagem baseada na descrição: {scene_desc}. Contexto adicional do roteiro: {context}. Estilo visual: {style}. Tom emocional: {tone}."
    else:
        image_prompt = f"Crie uma imagem representando o tema '{theme}', com foco em {', '.join(keywords)}. Baseie-se no seguinte trecho do roteiro: {context}. Estilo visual: {style}. Tom emocional: {tone}."

    music_prompt = f"Composição musical de fundo para um vídeo sobre {theme}. O trecho correspondente do roteiro diz: {context}. Estilo musical: {style}, tom {tone.lower()}. Instrumentos sugeridos: {'sintetizadores' if theme=='tecnologia' else 'orquestral' if theme in ['cinema', 'épico'] else 'piano e cordas'}. Duração aproximada: 30-60 segundos, com variação de intensidade conforme a emoção do texto."

    if effects:
        sfx_prompt = f"Incluir efeitos sonoros nos momentos apropriados, baseado no seguinte trecho: {context}. Efeitos sugeridos: {', '.join(effects)}. Os efeitos devem ser sutis e bem integrados à cena, reforçando as ações ou emoções descritas."
    else:
        sfx_prompt = f"Sem necessidade de efeitos sonoros específicos para este segmento; manter apenas a música de fundo. O trecho é: {context}."

    narration_prompt = f"Tom de narração: {tone}. Velocidade: moderada, com pausas para ênfase. Destaque as palavras-chave: {', '.join(keywords)}. O texto a ser narrado é:\n\n{original_text}"

    return {
        'image': image_prompt,
        'music': music_prompt,
        'sound_effects': sfx_prompt,
        'narration': narration_prompt
    }

def render_conversation_to_video_tab():
    st.markdown("### 🎬 Criar Vídeo a partir de Conversa com IA")
    st.markdown("""
    Cole abaixo uma conversa ou roteiro (como o exemplo do AlmaFluxo).  
    A plataforma irá analisar automaticamente, dividir em partes e gerar sugestões de prompts para cada segmento. Copie e cole o segmento junto o prompt desejado.
    """)

    conversation_text = st.text_area(
        "📋 Cole o texto da conversa aqui",
        height=300,
        key="conversation_input"
    )

    if st.button("🔍 Analisar Conversa", type="primary", use_container_width=True):
        if not conversation_text.strip():
            st.warning("Cole um texto primeiro.")
        else:
            with st.spinner("Analisando e dividindo em segmentos..."):
                segments = extract_segments_from_conversation(conversation_text)
                if not segments:
                    st.warning("Não foi possível identificar segmentos. O texto pode não ter uma estrutura clara.")
                else:
                    st.session_state.conversation_segments = []
                    for seg in segments:
                        analysis = analyze_segment_enhanced(seg['text'], seg.get('scene_desc', ''))
                        prompts = generate_multimedia_prompts(
                            segment_analysis=analysis,
                            original_text=seg['text']
                        )
                        seg['analysis'] = analysis
                        seg['prompts'] = prompts
                        st.session_state.conversation_segments.append(seg)

                    st.success(f"Conversa dividida em {len(segments)} segmentos!")

    if 'conversation_segments' in st.session_state and st.session_state.conversation_segments:
        st.markdown("#### 📌 Segmentos Identificados")

        # Se houver um template narrativo ativo, oferecer associação
        if st.session_state.narrative_template:
            st.markdown("#### 🔗 Associar Segmentos aos Atos Narrativos")
            act_options = [f"Ato {a.number}: {a.title}" for a in st.session_state.narrative_template.acts]
            
            for idx, seg in enumerate(st.session_state.conversation_segments):
                assigned_act = st.selectbox(
                    f"Segmento {idx+1} ({seg['title']}) pertence a:",
                    act_options,
                    key=f"assign_{idx}"
                )
                seg['assigned_act'] = assigned_act

        with st.expander("🎨 Configurações Globais (opcional)", expanded=False):
            global_style = st.selectbox(
                "Estilo Visual Padrão",
                ['Realista', 'Cinematográfico', 'Animado', 'Minimalista', 'Futurista', 'Vintage', 'Profissional', 'Casual'],
                index=1
            )
            global_tone = st.selectbox(
                "Tom Padrão",
                ['Inspirador', 'Informativo', 'Persuasivo', 'Divertido', 'Emocional', 'Autoritário', 'Amigável', 'Urgente', 'Empolgante'],
                index=0
            )

        for idx, seg in enumerate(st.session_state.conversation_segments):
            time_str = f"{seg.get('time_start', '?')}s - {seg.get('time_end', '?')}s"
            with st.expander(f"**{seg['title']}** (tempo: {time_str})", expanded=idx==0):
                col1, col2 = st.columns([2, 2])

                with col1:
                    st.markdown(f"**Texto:**\n{seg['text'][:300]}..." if len(seg['text'])>300 else seg['text'])
                    st.markdown(f"**Tema:** {seg['analysis']['primary_theme']} | **Tom:** {seg['analysis']['tone']} | **Estilo sugerido:** {seg['analysis']['style']}")
                    if seg['analysis']['effects_needed']:
                        st.markdown(f"**Efeitos sugeridos:** {', '.join(seg['analysis']['effects_needed'])}")

                with col2:
                    st.markdown("**Personalizar:**")
                    seg_style = st.selectbox(
                        "Estilo",
                        ['Realista', 'Cinematográfico', 'Animado', 'Minimalista', 'Futurista', 'Vintage', 'Profissional', 'Casual'],
                        index=['Realista', 'Cinematográfico', 'Animado', 'Minimalista', 'Futurista', 'Vintage', 'Profissional', 'Casual'].index(seg['analysis']['style']) if seg['analysis']['style'] in ['Realista', 'Cinematográfico', 'Animado', 'Minimalista', 'Futurista', 'Vintage', 'Profissional', 'Casual'] else 1,
                        key=f"style_{idx}"
                    )
                    seg_tone = st.selectbox(
                        "Tom",
                        ['Inspirador', 'Informativo', 'Persuasivo', 'Divertido', 'Emocional', 'Autoritário', 'Amigável', 'Urgente', 'Empolgante'],
                        index=['Inspirador', 'Informativo', 'Persuasivo', 'Divertido', 'Emocional', 'Autoritário', 'Amigável', 'Urgente', 'Empolgante'].index(seg['analysis']['tone']) if seg['analysis']['tone'] in ['Inspirador', 'Informativo', 'Persuasivo', 'Divertido', 'Emocional', 'Autoritário', 'Amigável', 'Urgente', 'Empolgante'] else 0,
                        key=f"tone_{idx}"
                    )

                if st.button(f"🔄 Regenerar Prompts", key=f"regenerate_{idx}"):
                    seg['analysis']['style'] = seg_style
                    seg['analysis']['tone'] = seg_tone
                    new_prompts = generate_multimedia_prompts(
                        segment_analysis=seg['analysis'],
                        user_style=seg_style,
                        user_tone=seg_tone,
                        original_text=seg['text']
                    )
                    seg['prompts'] = new_prompts
                    st.rerun()

                st.markdown("**📋 Prompts gerados:**")
                prompt_tabs = st.tabs(["🖼️ Imagem", "🎵 Música", "🔊 Efeitos", "🎤 Narração"])
                with prompt_tabs[0]:
                    st.code(seg['prompts']['image'], language='text')
                with prompt_tabs[1]:
                    st.code(seg['prompts']['music'], language='text')
                with prompt_tabs[2]:
                    st.code(seg['prompts']['sound_effects'], language='text')
                with prompt_tabs[3]:
                    st.code(seg['prompts']['narration'], language='text')

        if st.button("🎬 GERAR VÍDEO COMPLETO", type="primary", use_container_width=True):
            if not st.session_state.conversation_segments:
                st.warning("Nenhum segmento para gerar vídeo.")
            else:
                with st.spinner("Gerando vídeos dos segmentos..."):
                    segment_videos = []
                    progress_bar = st.progress(0)
                    for idx, seg in enumerate(st.session_state.conversation_segments):
                        # Caminho para o vídeo deste segmento
                        seg_video_path = os.path.join(
                            st.session_state.working_dir,
                            f"segment_{idx:03d}.mp4"
                        )
                        
                        # Usa a análise armazenada no segmento
                        analysis = seg['analysis']
                        
                        # Gera vídeo
                        success = generate_segment_video(
                            segment_text=seg['text'],
                            analysis=analysis,
                            output_path=seg_video_path,
                            voice_profiles=DEFAULT_VOICE_PROFILES,
                            music_library=MUSIC_LIBRARY
                        )
                        if success:
                            segment_videos.append(seg_video_path)
                        else:
                            st.error(f"Falha no segmento {idx+1}")
                            break
                        
                        progress_bar.progress((idx+1)/len(st.session_state.conversation_segments))
                    
                    if len(segment_videos) == len(st.session_state.conversation_segments):
                        # Concatena todos os vídeos
                        final_video = os.path.join(
                            st.session_state.working_dir,
                            f"conversa_completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                        )
                        if concatenate_videos(segment_videos, final_video):
                            st.session_state.generated_video = final_video
                            st.success("✅ Vídeo completo gerado!")
                            # Limpa vídeos temporários
                            for v in segment_videos:
                                try: os.remove(v)
                                except: pass
                        else:
                            st.error("Falha ao concatenar vídeos.")
                    else:
                        st.error("Nem todos os segmentos foram gerados com sucesso.")

def render_sidebar():
    with st.sidebar:
        st.markdown("### 🎛️ Controle Principal")
        
        with st.expander("📤 Upload de Arquivos", expanded=True):
            uploaded_video = st.file_uploader(
                "🎥 Vídeo",
                type=['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv'],
                help="Faça upload do vídeo para edição",
                key="video_uploader"
            )
            
            uploaded_audio = st.file_uploader(
                "🔊 Áudio",
                type=['mp3', 'wav', 'ogg', 'm4a', 'flac'],
                help="Faça upload de áudio para transcrição",
                key="audio_uploader"
            )
            
            if uploaded_video is not None and uploaded_video != st.session_state.uploaded_video:
                video_path = os.path.join(st.session_state.working_dir, f"video_{uuid.uuid4().hex[:8]}.mp4")
                with open(video_path, 'wb') as f:
                    f.write(uploaded_video.getvalue())
                
                st.session_state.video_path = video_path
                st.session_state.video_info = get_media_info(video_path, 'video')
                st.session_state.uploaded_video = uploaded_video
                
                with st.spinner("Extraindo áudio do vídeo..."):
                    audio_path = extract_audio_from_video(video_path)
                    if audio_path:
                        st.session_state.audio_path = audio_path
                        st.session_state.audio_info = get_media_info(audio_path, 'audio')
                
                st.success("✅ Vídeo carregado com sucesso!")
                st.rerun()
            
            if uploaded_audio is not None and uploaded_audio != st.session_state.uploaded_audio:
                audio_path = os.path.join(st.session_state.working_dir, f"audio_{uuid.uuid4().hex[:8]}.mp3")
                with open(audio_path, 'wb') as f:
                    f.write(uploaded_audio.getvalue())
                
                st.session_state.audio_path = audio_path
                st.session_state.audio_info = get_media_info(audio_path, 'audio')
                st.session_state.uploaded_audio = uploaded_audio
                st.success("✅ Áudio carregado com sucesso!")
                st.rerun()
        
        with st.expander("⚙️ Configurações", expanded=True):
            st.session_state.project_name = st.text_input(
                "Nome do Projeto",
                value=st.session_state.project_name,
                key="project_name_input"
            )
            
            st.session_state.auto_mode = st.checkbox(
                "Modo Automático",
                value=True,
                help="Executa operações automaticamente quando possível",
                key="auto_mode_checkbox"
            )
            
            part_duration = st.select_slider(
                "Duração das Partes",
                options=[15, 30, 60, 120, 180, 300],
                value=60,
                format_func=lambda x: f"{x}s",
                key="part_duration_slider"
            )
            
            if st.button("🔪 Dividir Vídeo", use_container_width=True, key="split_video_button"):
                if st.session_state.video_path:
                    with st.spinner("Dividindo vídeo em partes..."):
                        parts = split_video_into_parts(st.session_state.video_path, part_duration)
                        if parts:
                            st.session_state.video_parts = parts
                            st.session_state.is_partitioned = True
                            st.success(f"Vídeo dividido em {len(parts)} partes!")
                            st.rerun()
                        else:
                            st.error("Falha ao dividir o vídeo")
                else:
                    st.warning("Nenhum vídeo carregado")
        
        st.markdown("### 🔧 Status")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.video_path:
                st.markdown('<div class="status-indicator status-ready">✅ Vídeo</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-indicator status-missing">❌ Vídeo</div>', unsafe_allow_html=True)
        
        with col2:
            if st.session_state.audio_path:
                st.markdown('<div class="status-indicator status-ready">✅ Áudio</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-indicator status-missing">❌ Áudio</div>', unsafe_allow_html=True)
        
        with col3:
            if st.session_state.transcribed_text:
                st.markdown('<div class="status-indicator status-ready">✅ Texto</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-indicator status-missing">❌ Texto</div>', unsafe_allow_html=True)
        
        if st.session_state.video_analysis_complete:
            st.markdown("### 🧠 Análise")
            st.markdown('<div class="status-indicator status-ready">✅ Análise Completa</div>', unsafe_allow_html=True)
        
        st.markdown("### ⚡ Ações Rápidas")
        
        col_actions1, col_actions2 = st.columns(2)
        
        with col_actions1:
            if st.button("🔄 Analisar", use_container_width=True, 
                        disabled=not st.session_state.video_path or not st.session_state.transcribed_text,
                        key="analyze_button"):
                if st.session_state.video_path and st.session_state.transcribed_text:
                    with st.spinner("Analisando conteúdo do vídeo..."):
                        analysis = analyze_video_content(
                            st.session_state.video_path,
                            st.session_state.transcribed_text
                        )
                        st.session_state.video_analysis = analysis
                        st.session_state.video_analysis_complete = True
                        st.success("Análise concluída!")
                        st.rerun()
        
        with col_actions2:
            if st.button("🧹 Limpar", use_container_width=True, key="clear_button"):
                for key in list(st.session_state.keys()):
                    if key not in ['initialized', 'dependencies']:
                        del st.session_state[key]
                initialize_state()
                st.success("Sistema limpo e reiniciado!")
                st.rerun()
        
        st.markdown("---")
        st.markdown("### ℹ️ Informações")
        st.caption(f"**ID do Projeto:** {st.session_state.project_id}")
        st.caption(f"**Diretório:** {st.session_state.working_dir}")
        st.caption("**Versão:** 10.0 • Edição Completa")

def render_header():
    """Renderiza cabeçalho da aplicação"""
    st.markdown(f"""
    <div class="main-header">
        <h1>🎬 STUDIO PRO EDITOR AI</h1>
        <p>Edição Completa de Vídeo e Áudio • IA Integrada • Fácil e Poderoso</p>
        <div style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.8;">
            <span class="status-indicator status-ready">✅ Online</span> • 
            <span class="status-indicator status-ready">⚡ Pronto</span> • 
            Projeto: {st.session_state.project_name}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================
# APLICAÇÃO PRINCIPAL
# ==========================
def main():
    """Função principal da aplicação"""
    initialize_state()
    
    render_header()
    
    render_sidebar()
    
    # Sistema de abas principal - AGORA COM A ABA "ESTRUTURA NARRATIVA"
    tabs = st.tabs([
        "📤 Upload", 
        "✂️ Editar Vídeo", 
        "🔊 Editar Áudio", 
        "📝 Transcrição", 
        "🤖 IA", 
        "🎭 Estrutura Narrativa",  # NOVA ABA
        "📝 Texto para Vídeo",
        "🎬 Conversa para Vídeo",
        "💾 Exportar"
    ])
    
    with tabs[0]:
        render_upload_tab()
    
    with tabs[1]:
        render_edit_tab()
    
    with tabs[2]:
        render_audio_tab()
    
    with tabs[3]:
        render_text_tab()
    
    with tabs[4]:
        render_ai_tab()
    
    with tabs[5]:
        render_narrative_tab()
    
    with tabs[6]:
        render_text_to_video_tab()
    
    with tabs[7]:
        render_conversation_to_video_tab()
    
    with tabs[8]:
        render_export_tab()
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.caption(f"**🎬 Studio Pro Editor AI**")
        st.caption("v10.0 • Edição Completa")
    
    with col2:
        if st.session_state.video_info:
            dur = st.session_state.video_info.get('duration', 0)
            st.caption(f"**⏱️ Duração:** {dur:.1f}s")
        else:
            st.caption("**⏱️ Duração:** --")
    
    with col3:
        if st.session_state.video_parts:
            st.caption(f"**🔪 Partes:** {len(st.session_state.video_parts)}")
        else:
            st.caption("**🔪 Partes:** --")
    
    with col4:
        if st.session_state.transcribed_text:
            words = len(st.session_state.transcribed_text.split())
            st.caption(f"**📝 Palavras:** {words}")
        else:
            st.caption("**📝 Palavras:** --")

# ==========================
# EXECUÇÃO
# ==========================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Ocorreu um erro crítico: {str(e)}")
        st.info("Recarregue a página ou limpe o cache do navegador.")
        
        if st.button("🔄 Reiniciar Aplicação", type="primary"):
            for key in list(st.session_state.keys()):
                if key != 'initialized':
                    del st.session_state[key]
            st.rerun()