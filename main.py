#!/usr/bin/env python3
"""
Bible Verse Notifier - Aplicación para notificaciones periódicas de versículos bíblicos
Autor: Asistente AI
Licencia: GPL v3
Versión: PySide6
"""

import os
import sys
import json
import time
import random
import threading
from datetime import datetime
from pathlib import Path
import requests
from typing import List, Dict, Optional, Tuple

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

API_BASE_URL = "https://bible-api.deno.dev"

# Versiones disponibles según la API
AVAILABLE_VERSIONS = [
    {"name": "Reina Valera 1960", "code": "rv1960"},
    {"name": "Reina Valera 1995", "code": "rv1995"},
    {"name": "Nueva Versión Internacional", "code": "nvi"},
    {"name": "Dios habla hoy", "code": "dhh"},
    {"name": "Palabra de Dios para todos", "code": "pdt"}
]

# Categorías de versículos (para búsquedas temáticas) con íconos
VERSE_CATEGORIES = {
    "fe": {"name": "Fe", "keywords": ["fe", "confiar", "creer", "confianza"], "icon": "🌟"},
    "amor": {"name": "Amor", "keywords": ["amor", "amar", "caridad", "bondad"], "icon": "❤️"},
    "esperanza": {"name": "Esperanza", "keywords": ["esperanza", "esperar", "confianza"], "icon": "🌈"},
    "paz": {"name": "Paz", "keywords": ["paz", "tranquilidad", "quietud"], "icon": "🕊️"},
    "alegria": {"name": "Alegría", "keywords": ["alegría", "gozo", "regocijo", "felicidad"], "icon": "😊"},
    "fuerza": {"name": "Fuerza", "keywords": ["fuerza", "fortaleza", "poder", "vigor"], "icon": "💪"},
    "sabiduria": {"name": "Sabiduría", "keywords": ["sabiduría", "entendimiento", "conocimiento"], "icon": "📚"},
    "consuelo": {"name": "Consuelo", "keywords": ["consuelo", "consolar", "aliento", "ánimo"], "icon": "🤗"},
    "perdon": {"name": "Perdón", "keywords": ["perdón", "perdonar", "misericordia"], "icon": "🙏"},
    "gratitud": {"name": "Gratitud", "keywords": ["gratitud", "agradecer", "gracias", "acción de gracias"], "icon": "🙌"}
}

# Configuración por defecto
DEFAULT_CONFIG = {
    "enabled": True,
    "notification_interval": 30,  # minutos entre notificaciones
    "notification_duration": 10,  # segundos de duración de notificación
    "version": "rv1960",
    "categories": ["fe", "amor", "esperanza"],
    "testament": "both",
    "show_book_info": True,
    "play_sound": False,
    "sound_type": "default",
    "start_minimized": True,
    "theme": "auto",
    "last_verse": None,
    "last_notification": None,
    "verse_history": []  # Historial de versículos mostrados
}

CONFIG_DIR = Path.home() / ".config" / "bible-notifier"
CONFIG_FILE = CONFIG_DIR / "config.json"

def get_resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    full_path = os.path.join(base_path, relative_path)
    
    if not os.path.exists(full_path):
        for i in range(5):
            parent_path = os.path.join(base_path, "../" * i, relative_path)
            parent_path = os.path.abspath(parent_path)
            if os.path.exists(parent_path):
                return parent_path
    
    return full_path

def ensure_config_dir():
    """Asegura que el directorio de configuración exista"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_config():
    """Carga la configuración desde el archivo"""
    ensure_config_dir()
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            full_config = DEFAULT_CONFIG.copy()
            full_config.update(config)
            return full_config
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Guarda la configuración en el archivo"""
    try:
        ensure_config_dir()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando configuración: {e}")
        return False

class ThemeManager:
    """Manejador de temas claro/oscuro estilo Deepin"""
    
    @staticmethod
    def get_light_theme():
        """Tema claro estilo Deepin"""
        return {
            "primary": "#2CA7F8",  # Azul Deepin
            "primary_dark": "#1E8FD5",
            "primary_light": "#4AB8FF",
            "secondary": "#6C6C6C",
            "background": "#FFFFFF",
            "background_light": "#F5F5F5",
            "background_dark": "#E6E6E6",
            "text": "#303030",
            "text_light": "#606060",
            "border": "#D8D8D8",
            "success": "#35C335",
            "warning": "#FF9500",
            "danger": "#FF4A4A",
            "card_bg": "#FFFFFF",
            "card_shadow": "rgba(0, 0, 0, 0.05)",
            "hover": "#F0F7FF"
        }
    
    @staticmethod
    def get_dark_theme():
        """Tema oscuro estilo Deepin"""
        return {
            "primary": "#2CA7F8",
            "primary_dark": "#1E8FD5",
            "primary_light": "#4AB8FF",
            "secondary": "#A0A0A0",
            "background": "#242424",
            "background_light": "#2D2D2D",
            "background_dark": "#1A1A1A",
            "text": "#E0E0E0",
            "text_light": "#A0A0A0",
            "border": "#404040",
            "success": "#35C335",
            "warning": "#FF9500",
            "danger": "#FF4A4A",
            "card_bg": "#2D2D2D",
            "card_shadow": "rgba(0, 0, 0, 0.2)",
            "hover": "#2A3A4A"
        }
    
    @staticmethod
    @staticmethod
    def get_theme_stylesheet(theme_type="light"):
        """Genera hoja de estilos basada en el tema"""
        if theme_type == "dark":
            theme = ThemeManager.get_dark_theme()
        else:
            theme = ThemeManager.get_light_theme()
        
        return f"""
        /* Estilos generales */
        QMainWindow, QDialog, QWidget {{
            background-color: {theme['background']};
            color: {theme['text']};
            font-family: "Noto Sans", "Microsoft YaHei", sans-serif;
            font-size: 13px;
        }}
        
        /* Títulos y textos */
        QLabel {{
            color: {theme['text']};
            padding: 2px;
        }}
        
        QLabel#title {{
            font-size: 16px;
            font-weight: bold;
            color: {theme['primary']};
            padding: 8px 0;
        }}
        
        QLabel#subtitle {{
            font-size: 13px;
            color: {theme['text_light']};
            padding: 2px 0;
        }}
        
        /* Botones - MÁS DELGADOS */
        QPushButton {{
            background-color: {theme['background_light']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
            padding: 6px 12px;
            color: {theme['text']};
            font-weight: 500;
            min-height: 28px;
            margin: 1px;
        }}
        
        QPushButton:hover {{
            background-color: {theme['hover']};
            border-color: {theme['primary_light']};
        }}
        
        QPushButton:pressed {{
            background-color: {theme['primary_dark']};
            color: white;
        }}
        
        QPushButton:disabled {{
            background-color: {theme['background_dark']};
            color: {theme['text_light']};
        }}
        
        QPushButton#primary {{
            background-color: {theme['primary']};
            color: white;
            border: none;
            font-weight: 600;
            padding: 7px 16px;
        }}
        
        QPushButton#primary:hover {{
            background-color: {theme['primary_light']};
        }}
        
        QPushButton#primary:pressed {{
            background-color: {theme['primary_dark']};
        }}
        
        /* Checkboxes - MÁS COMPACTOS */
        QCheckBox {{
            spacing: 6px;
            color: {theme['text']};
            padding: 3px 0;
            margin: 1px;
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {theme['border']};
            border-radius: 3px;
            background-color: {theme['background_light']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {theme['primary']};
            border-color: {theme['primary']};
            image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 12 12"><path fill="white" d="M10.28 2.28L4 8.56 1.72 6.28a1 1 0 00-1.41 1.41l3 3a1 1 0 001.41 0l7-7a1 1 0 00-1.41-1.41z"/></svg>');
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {theme['primary_light']};
        }}
        
        /* Combobox - MÁS ELEGANTE */
        QComboBox {{
            background-color: {theme['background_light']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
            padding: 5px 10px;
            color: {theme['text']};
            min-height: 28px;
            margin: 1px;
        }}
        
        QComboBox:hover {{
            border-color: {theme['primary_light']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 12 12"><path fill="{theme['text_light'].replace('#', '%23')}" d="M6 8.5L1.5 4 2.5 3 6 6.5 9.5 3l1 1z"/></svg>');
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {theme['background_light']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
            selection-background-color: {theme['primary']};
            selection-color: white;
            padding: 4px;
        }}
        
        /* Spinbox - MÁS DELGADO */
        QSpinBox {{
            background-color: {theme['background_light']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
            padding: 4px 8px;
            color: {theme['text']};
            min-height: 28px;
            margin: 1px;
        }}
        
        QSpinBox:hover {{
            border-color: {theme['primary_light']};
        }}
        
        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: {theme['background_dark']};
            border: none;
            width: 18px;
            border-radius: 2px;
            margin: 1px;
        }}
        
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: {theme['hover']};
        }}
        
        QSpinBox::up-arrow, QSpinBox::down-arrow {{
            width: 7px;
            height: 7px;
        }}
        
        /* GroupBox - MÁS REFINADO */
        QGroupBox {{
            border: 1px solid {theme['border']};
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 8px;
            background-color: {theme['card_bg']};
            font-weight: 600;
            color: {theme['text']};
            font-size: 13px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
            color: {theme['primary']};
        }}
        
        /* ScrollArea */
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        
        QScrollBar:vertical {{
            background-color: {theme['background_dark']};
            width: 6px;
            border-radius: 3px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {theme['border']};
            border-radius: 3px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {theme['primary_light']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        /* ListWidget - MÁS COMPACTO */
        QListWidget {{
            background-color: {theme['background_light']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
            color: {theme['text']};
        }}
        
        QListWidget::item {{
            padding: 6px 10px;
            border-bottom: 1px solid {theme['border']};
            min-height: 24px;
        }}
        
        QListWidget::item:selected {{
            background-color: {theme['primary']};
            color: white;
        }}
        
        QListWidget::item:hover {{
            background-color: {theme['hover']};
        }}
        
        /* Separadores */
        QFrame#separator {{
            background-color: {theme['border']};
            max-height: 1px;
            min-height: 1px;
            margin: 8px 0;
        }}
        
        /* Cards para categorías - MÁS DELGADAS */
        QFrame#category_card {{
            background-color: {theme['card_bg']};
            border: 1px solid {theme['border']};
            border-radius: 6px;
            padding: 10px;
            margin: 2px;
        }}
        
        QFrame#category_card:hover {{
            border-color: {theme['primary_light']};
            background-color: {theme['hover']};
        }}
        
        /* Status indicators */
        QFrame#status_active {{
            background-color: {theme['success']};
            border-radius: 3px;
            min-width: 8px;
            max-width: 8px;
            min-height: 8px;
            max-height: 8px;
            margin: 0 5px;
        }}
        
        QFrame#status_inactive {{
            background-color: {theme['danger']};
            border-radius: 3px;
            min-width: 8px;
            max-width: 8px;
            min-height: 8px;
            max-height: 8px;
            margin: 0 5px;
        }}
        
        /* Form layouts - Mejor espaciado */
        QFormLayout {{
            spacing: 6px;
            margin: 0;
        }}
        
        QFormLayout QLabel {{
            padding-right: 8px;
        }}
        
        /* Input fields - Más consistentes */
        QLineEdit {{
            background-color: {theme['background_light']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
            padding: 5px 8px;
            min-height: 28px;
            margin: 1px;
        }}
        
        QLineEdit:hover {{
            border-color: {theme['primary_light']};
        }}
        
        QLineEdit:focus {{
            border-color: {theme['primary']};
            background-color: {theme['background']};
        }}
        
        /* Radio buttons */
        QRadioButton {{
            spacing: 6px;
            color: {theme['text']};
            padding: 3px 0;
            margin: 1px;
        }}
        
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 1px solid {theme['border']};
            background-color: {theme['background_light']};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {theme['primary']};
            border-color: {theme['primary']};
        }}
        
        /* Tooltips */
        QToolTip {{
            background-color: {theme['background_dark']};
            color: {theme['text']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        
        /* TabWidget */
        QTabWidget::pane {{
            border: 1px solid {theme['border']};
            border-radius: 4px;
            background-color: {theme['background']};
        }}
        
        QTabBar::tab {{
            background-color: {theme['background_light']};
            border: 1px solid {theme['border']};
            border-bottom: none;
            padding: 6px 12px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {theme['primary']};
            color: white;
            border-color: {theme['primary']};
        }}
        
        QTabBar::tab:hover {{
            background-color: {theme['hover']};
        }}
        """

class BibleAPI:
    """Clase para interactuar con la API de la Biblia"""
    
    @staticmethod
    def search_verse(query: str, version: str = "rv1960", testament: str = "both", 
                    take: int = 5, page: int = 1) -> List[Dict]:
        try:
            url = f"{API_BASE_URL}/api/read/{version}/search"
            params = {
                "q": query,
                "testament": testament,
                "take": take,
                "page": page
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return data.get("data", [])
        except Exception as e:
            print(f"Error buscando versículos: {e}")
            return []
    
    @staticmethod
    def get_random_verse(version: str = "rv1960") -> Optional[Dict]:
        try:
            # Primero, obtener todos los libros disponibles
            books_url = f"{API_BASE_URL}/api/books"
            response = requests.get(books_url, timeout=10)
            response.raise_for_status()
            books = response.json()
            
            if not books:
                return None
            
            # Seleccionar un libro aleatorio
            book = random.choice(books)
            
            # Obtener un capítulo aleatorio del libro
            chapters = book.get("chapters", 1)
            if chapters < 1:
                chapters = 1
            chapter = random.randint(1, chapters)
            
            # Obtener el capítulo completo
            book_abbrev = book.get('abrev', '')
            if not book_abbrev:
                # Intentar obtener abreviatura del nombre
                book_name = book.get('name', '').lower()
                # Mapeo simple de nombres a abreviaturas
                abbrev_map = {
                    'génesis': 'gen', 'éxodo': 'exo', 'levítico': 'lev',
                    'números': 'num', 'deuteronomio': 'deu', 'josué': 'jos',
                    'jueces': 'jue', 'rut': 'rut', '1 samuel': '1sa',
                    '2 samuel': '2sa', '1 reyes': '1re', '2 reyes': '2re',
                    '1 crónicas': '1cr', '2 crónicas': '2cr', 'esdras': 'esd',
                    'nehemías': 'neh', 'ester': 'est', 'job': 'job',
                    'salmos': 'sal', 'proverbios': 'pro', 'eclesiastés': 'ecl',
                    'cantares': 'can', 'isaías': 'isa', 'jeremías': 'jer',
                    'lamentaciones': 'lam', 'ezequiel': 'eze', 'daniel': 'dan',
                    'oseas': 'ose', 'joel': 'joe', 'amos': 'amo',
                    'abdías': 'abd', 'jonás': 'jon', 'miqueas': 'mic',
                    'nahúm': 'nah', 'habacuc': 'hab', 'sofonías': 'sof',
                    'hageo': 'hag', 'zacarías': 'zac', 'malaquías': 'mal',
                    'mateo': 'mat', 'marcos': 'mar', 'lucas': 'luc',
                    'juan': 'jua', 'hechos': 'hec', 'romanos': 'rom',
                    '1 corintios': '1co', '2 corintios': '2co', 'gálatas': 'gal',
                    'efesios': 'efe', 'filipenses': 'fil', 'colosenses': 'col',
                    '1 tesalonicenses': '1te', '2 tesalonicenses': '2te',
                    '1 timoteo': '1ti', '2 timoteo': '2ti', 'tito': 'tit',
                    'filemón': 'fil', 'hebreos': 'heb', 'santiago': 'sant',
                    '1 pedro': '1pe', '2 pedro': '2pe', '1 juan': '1jn',
                    '2 juan': '2jn', '3 juan': '3jn', 'judas': 'jud',
                    'apocalipsis': 'apo'
                }
                book_abbrev = abbrev_map.get(book_name, book_name[:3])
            
            verse_url = f"{API_BASE_URL}/api/read/{version}/{book_abbrev}/{chapter}"
            response = requests.get(verse_url, timeout=10)
            response.raise_for_status()
            chapter_data = response.json()
            
            # Seleccionar un versículo aleatorio del capítulo
            vers = chapter_data.get("vers", [])
            if not vers:
                return None
            
            verse_data = random.choice(vers)
            
            return {
                "verse": verse_data.get("verse", ""),
                "book": book.get("name", ""),
                "chapter": chapter,
                "number": verse_data.get("number", 0),
                "version": version,
                "study": verse_data.get("study", "")
            }
        except Exception as e:
            print(f"Error obteniendo versículo aleatorio: {e}")
            return None

class CategoriesWindow(QDialog):
    """Ventana para seleccionar categorías de versículos"""
    
    categories_changed = Signal(list)
    
    def __init__(self, selected_categories, parent=None):
        super().__init__(parent)
        self.selected_categories = selected_categories.copy()
        self.current_theme = "light"  # Valor por defecto
        self.setWindowTitle("Seleccionar Categorías")
        self.setMinimumSize(500, 400)
        
        # Establecer como diálogo modal
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        self.setStyleSheet(ThemeManager.get_theme_stylesheet(self.current_theme))
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title_label = QLabel("Selecciona las categorías de versículos")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel("Las notificaciones mostrarán versículos de las categorías seleccionadas")
        desc_label.setObjectName("subtitle")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Separador
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        
        # Scroll area para las categorías
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Widget contenedor de categorías
        categories_widget = QWidget()
        categories_layout = QVBoxLayout(categories_widget)
        categories_layout.setSpacing(10)
        categories_layout.setContentsMargins(5, 5, 5, 5)
        
        self.category_cards = {}
        for category_id, category_info in VERSE_CATEGORIES.items():
            card = self.create_category_card(category_id, category_info)
            categories_layout.addWidget(card)
            self.category_cards[category_id] = card
        
        # Espaciador
        categories_layout.addStretch()
        
        scroll_area.setWidget(categories_widget)
        layout.addWidget(scroll_area)
        
        # Separador
        separator2 = QFrame()
        separator2.setObjectName("separator")
        separator2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator2)
        
        # Contador de categorías seleccionadas
        self.counter_label = QLabel(f"Categorías seleccionadas: {len(self.selected_categories)}")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.counter_label)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Seleccionar todas")
        self.select_all_btn.clicked.connect(self.select_all_categories)
        button_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("Deseleccionar todas")
        self.deselect_all_btn.clicked.connect(self.deselect_all_categories)
        button_layout.addWidget(self.deselect_all_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Guardar")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.save_categories)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def create_category_card(self, category_id, category_info):
        card = QFrame()
        card.setObjectName("category_card")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        
        card_layout = QHBoxLayout(card)
        card_layout.setSpacing(15)
        card_layout.setContentsMargins(15, 15, 15, 15)
        
        # Ícono
        icon_label = QLabel(category_info["icon"])
        icon_label.setFont(QFont("Arial", 20))
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_label)
        
        # Información de la categoría
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(5)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Nombre
        name_label = QLabel(category_info["name"])
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(name_label)
        
        # Palabras clave
        keywords = ", ".join(category_info["keywords"])
        keywords_label = QLabel(f"Palabras clave: {keywords}")
        keywords_label.setStyleSheet("font-size: 12px; color: #666;")
        keywords_label.setWordWrap(True)
        info_layout.addWidget(keywords_label)
        
        card_layout.addWidget(info_widget, 1)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(category_id in self.selected_categories)
        checkbox.toggled.connect(lambda checked, cat=category_id: self.toggle_category(cat, checked))
        checkbox.setFixedSize(24, 24)
        card_layout.addWidget(checkbox)
        
        # Guardar referencia al checkbox
        card.checkbox = checkbox
        
        # Conectar clic en la card al checkbox
        card.mousePressEvent = lambda event: self.card_clicked(category_id, card)
        
        return card
    
    def card_clicked(self, category_id, card):
        card.checkbox.toggle()
    
    def toggle_category(self, category_id, checked):
        if checked and category_id not in self.selected_categories:
            self.selected_categories.append(category_id)
        elif not checked and category_id in self.selected_categories:
            self.selected_categories.remove(category_id)
        
        # Actualizar contador
        self.counter_label.setText(f"Categorías seleccionadas: {len(self.selected_categories)}")
    
    def select_all_categories(self):
        self.selected_categories = list(VERSE_CATEGORIES.keys())
        for category_id, card in self.category_cards.items():
            card.checkbox.setChecked(True)
        self.counter_label.setText(f"Categorías seleccionadas: {len(self.selected_categories)}")
    
    def deselect_all_categories(self):
        self.selected_categories = []
        for category_id, card in self.category_cards.items():
            card.checkbox.setChecked(False)
        self.counter_label.setText(f"Categorías seleccionadas: {len(self.selected_categories)}")
    
    def save_categories(self):
        self.categories_changed.emit(self.selected_categories)
        self.accept()
    
    def apply_theme(self):
        parent = self.parent()
        theme_type = "light"  # Valor por defecto
        
        # Intentar obtener el tema de varias maneras
        if parent:
            if hasattr(parent, 'current_theme'):
                theme_type = parent.current_theme
            elif hasattr(parent, 'config'):
                theme_type = parent.config.get("theme", "auto")
            elif isinstance(parent, MainWindow):
                theme_type = parent.config.get("theme", "auto")
        
        if theme_type == "auto":
            import subprocess
            try:
                result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], 
                                    capture_output=True, text=True)
                if 'dark' in result.stdout.lower():
                    theme_type = "dark"
                else:
                    theme_type = "light"
            except:
                theme_type = "light"
        
        self.setStyleSheet(ThemeManager.get_theme_stylesheet(theme_type))

class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bible Verse Notifier")
        self.setMinimumSize(200, 100)
        
        # Cargar configuración
        self.config = load_config()
        self.current_theme = self.config.get("theme", "auto")
        self.apply_theme()
        
        # Variables para mantener referencia a los diálogos
        self.config_dialog = None
        self.history_dialog = None
        self.categories_dialog = None
        
        # Inicializar componentes
        self.init_tray()
        self.init_notification_timer()
        
        # Ocultar la ventana principal (solo se ejecuta en segundo plano)
        if self.config.get("start_minimized", True):
            self.hide()
        
        # Mostrar primera notificación si está habilitado
        if self.config["enabled"]:
            QTimer.singleShot(5000, self.show_notification)  # Esperar 5 segundos al inicio
    
    def apply_theme(self):
        theme_type = self.current_theme
        if theme_type == "auto":
            # Detectar tema del sistema (simple)
            import subprocess
            try:
                result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], 
                                      capture_output=True, text=True)
                if 'dark' in result.stdout.lower():
                    theme_type = "dark"
                else:
                    theme_type = "light"
            except:
                theme_type = "light"
        
        self.setStyleSheet(ThemeManager.get_theme_stylesheet(theme_type))
    
    def init_tray(self):
        # Crear ícono
        self.tray_icon = QSystemTrayIcon(self)
        
        # Intentar cargar ícono personalizado
        icon_paths = [
            get_resource_path("resources/bible-icon.png"),
            get_resource_path("bible-icon.png"),
            os.path.join(os.path.dirname(__file__), "bible-icon.png"),
            "/usr/share/icons/hicolor/48x48/apps/bible-notifier.png",
        ]
        
        icon_loaded = False
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
                icon_loaded = True
                print(f"Icono cargado desde: {icon_path}")
                break
        
        if not icon_loaded:
            # Crear un ícono simple programáticamente
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Dibujar un círculo azul
            painter.setBrush(QColor(44, 167, 248))  # Azul Deepin
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 2, 60, 60)
            
            # Dibujar una "B" blanca
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 32, QFont.Weight.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "B")
            
            painter.end()
            
            self.tray_icon.setIcon(QIcon(pixmap))
            print("Icono creado programáticamente")
        
        # Crear menú contextual
        self.tray_menu = QMenu()
        
        self.show_now_action = QAction("📖 Mostrar versículo ahora", self)
        self.show_now_action.triggered.connect(self.show_notification)
        self.tray_menu.addAction(self.show_now_action)
        
        self.tray_menu.addSeparator()
        
        # Estado (habilitado/deshabilitado)
        status_icon = "✅" if self.config["enabled"] else "❌"
        self.enable_action = QAction(f"{status_icon} Notificaciones", self)
        self.enable_action.setCheckable(True)
        self.enable_action.setChecked(self.config["enabled"])
        self.enable_action.triggered.connect(self.toggle_notifications)
        self.tray_menu.addAction(self.enable_action)
        
        self.tray_menu.addSeparator()
        
        self.config_action = QAction("⚙️ Configuración", self)
        self.config_action.triggered.connect(self.show_config_dialog)
        self.tray_menu.addAction(self.config_action)
        
        # Ver historial
        self.history_action = QAction("📜 Ver historial", self)
        self.history_action.triggered.connect(self.show_history)
        self.tray_menu.addAction(self.history_action)
        
        self.tray_menu.addSeparator()
        
        self.quit_action = QAction("🚪 Salir", self)
        self.quit_action.triggered.connect(self.quit_app)
        self.tray_menu.addAction(self.quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        self.tray_icon.showMessage(
            "Bible Verse Notifier",
            "La aplicación se está ejecutando en la bandeja del sistema.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
    
    def init_notification_timer(self):
        """Inicializar el temporizador para notificaciones periódicas"""
        self.notification_timer = QTimer()
        self.notification_timer.timeout.connect(self.show_notification)
        
        if self.config["enabled"]:
            self.start_notification_timer()
    
    def start_notification_timer(self):
        interval = self.config["notification_interval"] * 60 * 1000  # Convertir a milisegundos
        self.notification_timer.start(interval)
        print(f"Temporizador iniciado: {interval} ms ({self.config['notification_interval']} minutos)")
    
    def stop_notification_timer(self):
        self.notification_timer.stop()
        print("Temporizador detenido")
    
    def toggle_notifications(self, checked):
        self.config["enabled"] = checked
        status_icon = "✅" if checked else "❌"
        self.enable_action.setText(f"{status_icon} Notificaciones")
        self.enable_action.setChecked(checked)
        
        if checked:
            self.start_notification_timer()
            self.show_notification()
        else:
            self.stop_notification_timer()
        
        save_config(self.config)
        print(f"Notificaciones {'habilitadas' if checked else 'deshabilitadas'}")
    
    def show_notification(self):
        if not self.config["enabled"]:
            return
        
        print("Mostrando notificación...")
        
        # Obtener un versículo
        verse = self.get_random_verse()
        
        if not verse:
            print("No se pudo obtener un versículo")
            return
        
        # Guardar en historial
        verse_record = {
            "verse": verse["verse"],
            "reference": f"{verse['book']} {verse['chapter']}:{verse['number']}",
            "version": verse["version"],
            "timestamp": datetime.now().isoformat(),
            "study": verse.get("study", "")
        }
        
        self.config["verse_history"].append(verse_record)
        
        # Mantener solo los últimos 50 registros
        if len(self.config["verse_history"]) > 50:
            self.config["verse_history"] = self.config["verse_history"][-50:]
        
        # Actualizar último versículo
        self.config["last_verse"] = verse_record
        self.config["last_notification"] = datetime.now().isoformat()
        
        # Guardar configuración
        save_config(self.config)
        
        # Preparar texto de la notificación
        title = "📖 Palabra de Dios"
        message = verse["verse"]
        
        if self.config["show_book_info"]:
            message = f"{verse['book']} {verse['chapter']}:{verse['number']}\n\n{message}"
        
        # Calcular duración en milisegundos
        duration = self.config.get("notification_duration", 10) * 1000
        
        # Mostrar notificación
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, duration)
        
        # Reproducir sonido si está habilitado
        if self.config.get("play_sound", False) and self.config.get("sound_type", "default") != "none":
            self.play_notification_sound()
        
        print(f"Notificación mostrada ({duration/1000}s): {verse['book']} {verse['chapter']}:{verse['number']}")
    
    def get_random_verse(self) -> Optional[Dict]:
        # Seleccionar una categoría aleatoria de las activas
        active_categories = self.config.get("categories", ["fe", "amor", "esperanza"])
        
        if not active_categories:
            # Si no hay categorías activas, usar versículo completamente aleatorio
            return BibleAPI.get_random_verse(self.config["version"])
        
        category = random.choice(active_categories)
        
        # Obtener palabras clave para esta categoría
        keywords = VERSE_CATEGORIES[category]["keywords"]
        keyword = random.choice(keywords)
        
        print(f"Buscando versículos con palabra clave: '{keyword}'")
        
        # Buscar versículos con esta palabra clave
        verses = BibleAPI.search_verse(
            query=keyword,
            version=self.config["version"],
            testament=self.config["testament"],
            take=10,
            page=1
        )
        
        if verses:
            # Seleccionar un versículo aleatorio de los resultados
            verse_data = random.choice(verses)
            
            return {
                "verse": verse_data.get("verse", ""),
                "book": verse_data.get("book", ""),
                "chapter": verse_data.get("chapter", 0),
                "number": verse_data.get("number", 0),
                "version": self.config["version"],
                "study": verse_data.get("study", "")
            }
        else:
            # Fallback a versículo aleatorio
            print(f"No se encontraron versículos para '{keyword}', usando aleatorio...")
            return BibleAPI.get_random_verse(self.config["version"])
    
    def play_notification_sound(self):
        sound_type = self.config.get("sound_type", "default")
        
        try:
            if sound_type == "bell":
                command = ["paplay", "--volume", "65536", "/usr/share/sounds/freedesktop/stereo/bell.oga"]
            elif sound_type == "chime":
                command = ["paplay", "--volume", "65536", "/usr/share/sounds/freedesktop/stereo/message.oga"]
            else:  # default
                command = ["canberra-gtk-play", "-i", "message"]
            
            import subprocess
            subprocess.run(command, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL,
                         timeout=2)
            print(f"Sonido de notificación reproducido: {sound_type}")
        except FileNotFoundError:
            print(f"Programa de sonido no encontrado. Intenta instalar: sudo apt install libcanberra-gtk-module")
        except Exception as e:
            print(f"No se pudo reproducir sonido: {e}")
    
    def show_config_dialog(self):
        print("Mostrando diálogo de configuración...")
        
        # Si ya hay un diálogo abierto, traerlo al frente
        if self.config_dialog is not None:
            print("Diálogo ya abierto, trayendo al frente...")
            self.config_dialog.raise_()
            self.config_dialog.activateWindow()
            return
        
        # Crear el diálogo de configuración
        self.config_dialog = ConfigWindow(self.config, self)
        self.config_dialog.config_changed.connect(self.handle_config_change)
        
        # Conectar la señal de cerrado para limpiar la referencia
        self.config_dialog.finished.connect(self.on_config_closed)
        
        # Mostrar el diálogo
        self.config_dialog.show()
        print("Diálogo de configuración mostrado")
    
    def on_config_closed(self, result):
        print(f"Diálogo de configuración cerrado, resultado: {result}")
        self.config_dialog = None
    
    def show_history(self):
        print("Mostrando historial...")
        
        # Si ya hay un diálogo abierto, traerlo al frente
        if self.history_dialog is not None:
            print("Diálogo de historial ya abierto, trayendo al frente...")
            self.history_dialog.raise_()
            self.history_dialog.activateWindow()
            return
        
        # Crear el diálogo de historial
        self.history_dialog = HistoryWindow(self.config.get("verse_history", []), self)
        
        # Conectar la señal de cerrado para limpiar la referencia
        self.history_dialog.finished.connect(self.on_history_closed)
        
        # Mostrar el diálogo
        self.history_dialog.show()
        print("Diálogo de historial mostrado")
    
    def on_history_closed(self, result):
        print(f"Diálogo de historial cerrado, resultado: {result}")
        self.history_dialog = None
    
    def handle_config_change(self, new_config):
        # Verificar si el tema cambió
        old_theme = self.config.get("theme", "auto")
        new_theme = new_config.get("theme", "auto")
        
        # Actualizar configuración
        self.config.update(new_config)
        save_config(self.config)
        
        # Actualizar tema si cambió
        if old_theme != new_theme:
            self.current_theme = new_theme
            self.apply_theme()
        
        # Actualizar estado del menú
        status_icon = "✅" if self.config["enabled"] else "❌"
        self.enable_action.setText(f"{status_icon} Notificaciones")
        self.enable_action.setChecked(self.config["enabled"])
        
        # Reiniciar temporizador si es necesario
        if self.config["enabled"]:
            self.stop_notification_timer()
            self.start_notification_timer()
        else:
            self.stop_notification_timer()
        
        print("Configuración actualizada")
    
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_notification()
            print("Doble clic: mostrando notificación")
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.toggle_notifications(not self.config["enabled"])
            print("Clic medio: alternando notificaciones")
    
    def quit_app(self):
        print("Saliendo de la aplicación...")
        
        # Cerrar ventanas si están abiertas
        if self.config_dialog:
            self.config_dialog.close()
        if self.history_dialog:
            self.history_dialog.close()
        if self.categories_dialog:
            self.categories_dialog.close()
        
        # Guardar configuración
        save_config(self.config)
        
        # Ocultar ícono
        self.tray_icon.hide()
        
        # Salir de la aplicación
        QApplication.quit()
    
    def closeEvent(self, event):
        # Si el usuario cierra la ventana principal, solo ocultarla
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()


class ConfigWindow(QDialog):
    
    config_changed = Signal(dict)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle("Configuración - Bible Notifier")
        self.setMinimumWidth(550)
        self.setMinimumHeight(650)
        
        # Establecer como diálogo modal de ventana
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        self.init_ui()
        self.load_config()
        self.apply_theme()
    
    def apply_theme(self):
        parent = self.parent()
        if parent and hasattr(parent, 'current_theme'):
            theme_type = parent.current_theme
        else:
            theme_type = "light"
        
        self.setStyleSheet(ThemeManager.get_theme_stylesheet(theme_type))
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title_label = QLabel("Configuración de Bible Notifier")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Scroll area para el contenido
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Widget contenedor
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        # ========== NOTIFICACIONES ==========
        notifications_group = QGroupBox("🔔 Notificaciones")
        notifications_layout = QVBoxLayout()
        
        # Estado de notificaciones
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Estado:"))
        
        self.status_indicator = QFrame()
        self.status_indicator.setObjectName("status_active" if self.config.get("enabled", True) else "status_inactive")
        status_layout.addWidget(self.status_indicator)
        
        status_text = QLabel("Activas" if self.config.get("enabled", True) else "Inactivas")
        status_layout.addWidget(status_text)
        
        status_layout.addStretch()
        notifications_layout.addLayout(status_layout)
        
        # Habilitar notificaciones
        self.enable_cb = QCheckBox("Habilitar notificaciones automáticas")
        self.enable_cb.toggled.connect(self.update_status_indicator)
        notifications_layout.addWidget(self.enable_cb)
        
        # Intervalo de notificaciones
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Mostrar cada:"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(5, 1440)  # De 5 minutos a 24 horas
        self.interval_spin.setSuffix(" minutos")
        self.interval_spin.setValue(30)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        notifications_layout.addLayout(interval_layout)
        
        # Duración de notificaciones
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duración de notificación:"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(3, 60)  # De 3 a 60 segundos
        self.duration_spin.setSuffix(" segundos")
        self.duration_spin.setValue(10)
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()
        notifications_layout.addLayout(duration_layout)
        
        notifications_group.setLayout(notifications_layout)
        content_layout.addWidget(notifications_group)
        
        # ========== BIBLIA ==========
        bible_group = QGroupBox("📖 Biblia")
        bible_layout = QVBoxLayout()
        
        # Versión de la Biblia
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("Versión:"))
        self.version_combo = QComboBox()
        for version in AVAILABLE_VERSIONS:
            self.version_combo.addItem(version["name"], version["code"])
        version_layout.addWidget(self.version_combo)
        version_layout.addStretch()
        bible_layout.addLayout(version_layout)
        
        # Testamento
        testament_layout = QHBoxLayout()
        testament_layout.addWidget(QLabel("Testamento:"))
        self.testament_combo = QComboBox()
        self.testament_combo.addItem("Ambos testamentos", "both")
        self.testament_combo.addItem("Antiguo Testamento", "old")
        self.testament_combo.addItem("Nuevo Testamento", "new")
        testament_layout.addWidget(self.testament_combo)
        testament_layout.addStretch()
        bible_layout.addLayout(testament_layout)
        
        # Mostrar información del libro
        self.show_book_cb = QCheckBox("Mostrar libro y capítulo en notificaciones")
        bible_layout.addWidget(self.show_book_cb)
        
        bible_group.setLayout(bible_layout)
        content_layout.addWidget(bible_group)
        
        # ========== CATEGORÍAS ==========
        categories_group = QGroupBox("🏷️ Categorías")
        categories_layout = QVBoxLayout()
        
        # Contador de categorías seleccionadas
        self.categories_count_label = QLabel("Categorías seleccionadas: 0")
        categories_layout.addWidget(self.categories_count_label)
        
        # Botón para seleccionar categorías
        self.categories_btn = QPushButton("Seleccionar categorías...")
        self.categories_btn.clicked.connect(self.show_categories_dialog)
        categories_layout.addWidget(self.categories_btn)
        
        categories_group.setLayout(categories_layout)
        content_layout.addWidget(categories_group)
        
        # ========== SONIDO ==========
        sound_group = QGroupBox("🔊 Sonido")
        sound_layout = QVBoxLayout()
        
        self.play_sound_cb = QCheckBox("Reproducir sonido con notificaciones")
        sound_layout.addWidget(self.play_sound_cb)
        
        sound_type_layout = QHBoxLayout()
        sound_type_layout.addWidget(QLabel("Tipo de sonido:"))
        self.sound_combo = QComboBox()
        self.sound_combo.addItem("Predeterminado", "default")
        self.sound_combo.addItem("Campana", "bell")
        self.sound_combo.addItem("Timbre", "chime")
        self.sound_combo.addItem("Ninguno", "none")
        sound_type_layout.addWidget(self.sound_combo)
        sound_type_layout.addStretch()
        sound_layout.addLayout(sound_type_layout)
        
        sound_group.setLayout(sound_layout)
        content_layout.addWidget(sound_group)
        
        # ========== INTERFAZ ==========
        interface_group = QGroupBox("🎨 Interfaz")
        interface_layout = QVBoxLayout()
        
        # Tema
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Tema:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Automático", "auto")
        self.theme_combo.addItem("Claro", "light")
        self.theme_combo.addItem("Oscuro", "dark")
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        interface_layout.addLayout(theme_layout)
        
        self.start_minimized_cb = QCheckBox("Iniciar minimizado a la bandeja")
        interface_layout.addWidget(self.start_minimized_cb)
        
        interface_group.setLayout(interface_layout)
        content_layout.addWidget(interface_group)
        
        # Espaciador
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # ========== BOTONES ==========
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Probar notificación")
        self.test_button.clicked.connect(self.test_notification)
        button_layout.addWidget(self.test_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("Guardar")
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(self.save_config)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
    
    def update_status_indicator(self, checked):
        self.status_indicator.setObjectName("status_active" if checked else "status_inactive")
        self.status_indicator.style().polish(self.status_indicator)
    
    def show_categories_dialog(self):
        print("Mostrando diálogo de categorías...")
        
        parent = self.parent()
        if parent and hasattr(parent, 'categories_dialog') and parent.categories_dialog is not None:
            parent.categories_dialog.raise_()
            parent.categories_dialog.activateWindow()
            return
        
        parent.categories_dialog = CategoriesWindow(self.config.get("categories", []), self)
        parent.categories_dialog.categories_changed.connect(self.update_categories)
        
        if parent and hasattr(parent, 'current_theme'):
            parent.categories_dialog.current_theme = parent.current_theme
        else:
            theme_type = self.config.get("theme", "auto")
            if theme_type == "auto":
                # Detectar tema del sistema
                import subprocess
                try:
                    result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], 
                                        capture_output=True, text=True)
                    if 'dark' in result.stdout.lower():
                        theme_type = "dark"
                    else:
                        theme_type = "light"
                except:
                    theme_type = "light"
            parent.categories_dialog.current_theme = theme_type
        
        # Aplicar el tema inmediatamente
        parent.categories_dialog.setStyleSheet(
            ThemeManager.get_theme_stylesheet(parent.categories_dialog.current_theme)
        )
        
        parent.categories_dialog.finished.connect(lambda result: setattr(parent, 'categories_dialog', None))
        
        parent.categories_dialog.show()
        print("Diálogo de categorías mostrado")
    
    def update_categories(self, categories):
        self.config["categories"] = categories
        count = len(categories)
        self.categories_count_label.setText(f"Categorías seleccionadas: {count}")
        
        # Mostrar nombres de categorías si hay pocas
        if count <= 3:
            category_names = []
            for cat_id in categories:
                if cat_id in VERSE_CATEGORIES:
                    category_names.append(VERSE_CATEGORIES[cat_id]["name"])
            if category_names:
                self.categories_count_label.setText(f"Categorías: {', '.join(category_names)}")
    
    def load_config(self):
        print("Cargando configuración en los controles...")
        
        self.enable_cb.setChecked(self.config.get("enabled", True))
        self.interval_spin.setValue(self.config.get("notification_interval", 30))
        self.duration_spin.setValue(self.config.get("notification_duration", 10))
        
        # Versión
        version = self.config.get("version", "rv1960")
        index = self.version_combo.findData(version)
        if index >= 0:
            self.version_combo.setCurrentIndex(index)
        
        # Testamento
        testament = self.config.get("testament", "both")
        index = self.testament_combo.findData(testament)
        if index >= 0:
            self.testament_combo.setCurrentIndex(index)
        
        # Categorías
        categories = self.config.get("categories", ["fe", "amor", "esperanza"])
        self.update_categories(categories)
        
        # Sonido
        self.play_sound_cb.setChecked(self.config.get("play_sound", False))
        sound_type = self.config.get("sound_type", "default")
        index = self.sound_combo.findData(sound_type)
        if index >= 0:
            self.sound_combo.setCurrentIndex(index)
        
        # Interfaz
        self.show_book_cb.setChecked(self.config.get("show_book_info", True))
        self.start_minimized_cb.setChecked(self.config.get("start_minimized", True))
        
        # Tema
        theme = self.config.get("theme", "auto")
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        # Actualizar indicador de estado
        self.update_status_indicator(self.config.get("enabled", True))
    
    def get_config(self):
        config = {}
        
        config["enabled"] = self.enable_cb.isChecked()
        config["notification_interval"] = self.interval_spin.value()
        config["notification_duration"] = self.duration_spin.value()
        config["version"] = self.version_combo.currentData()
        config["testament"] = self.testament_combo.currentData()
        config["categories"] = self.config.get("categories", ["fe", "amor", "esperanza"])
        config["play_sound"] = self.play_sound_cb.isChecked()
        config["sound_type"] = self.sound_combo.currentData()
        config["show_book_info"] = self.show_book_cb.isChecked()
        config["start_minimized"] = self.start_minimized_cb.isChecked()
        config["theme"] = self.theme_combo.currentData()
        
        return config
    
    def save_config(self):
        new_config = self.get_config()
        self.config_changed.emit(new_config)
        self.accept()
    
    def test_notification(self):
        # Obtener configuración temporal
        temp_config = self.get_config()
        
        # Buscar un versículo de prueba
        active_categories = temp_config.get("categories", ["fe", "amor", "esperanza"])
        if not active_categories:
            active_categories = ["amor"]
        
        category = random.choice(active_categories)
        keywords = VERSE_CATEGORIES[category]["keywords"]
        keyword = random.choice(keywords)
        
        # Buscar versículos
        verses = BibleAPI.search_verse(
            query=keyword,
            version=temp_config["version"],
            testament=temp_config["testament"],
            take=5,
            page=1
        )
        
        if verses:
            verse_data = random.choice(verses)
            
            # Preparar mensaje
            title = "📖 Prueba de notificación"
            message = verse_data.get("verse", "")
            
            if temp_config["show_book_info"]:
                message = f"{verse_data.get('book', '')} {verse_data.get('chapter', 0)}:{verse_data.get('number', 0)}\n\n{message}"
            
            # Calcular duración
            duration = temp_config.get("notification_duration", 10) * 1000
            
            # Mostrar notificación usando el ícono de bandeja de la aplicación principal
            parent = self.parent()
            if parent and hasattr(parent, 'tray_icon'):
                parent.tray_icon.showMessage(
                    title, message, 
                    QSystemTrayIcon.MessageIcon.Information, 
                    duration
                )
            
            # Reproducir sonido si está habilitado
            if temp_config.get("play_sound", False) and temp_config.get("sound_type", "default") != "none":
                try:
                    if temp_config["sound_type"] == "bell":
                        command = ["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"]
                    elif temp_config["sound_type"] == "chime":
                        command = ["paplay", "/usr/share/sounds/freedesktop/stereo/message.oga"]
                    else:
                        command = ["canberra-gtk-play", "-i", "message"]
                    
                    import subprocess
                    subprocess.run(command, 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL,
                                 timeout=2)
                except:
                    pass
    
    def closeEvent(self, event):
        print("ConfigWindow cerrada por closeEvent")
        self.reject()

class HistoryWindow(QDialog):
    
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.history = history
        self.setWindowTitle("Historial de versículos")
        self.setMinimumSize(700, 500)
        
        # Establecer como diálogo modal de ventana
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        self.init_ui()
        self.apply_theme()
    
    def apply_theme(self):
        parent = self.parent()
        if parent and hasattr(parent, 'current_theme'):
            theme_type = parent.current_theme
        else:
            theme_type = "light"
        
        self.setStyleSheet(ThemeManager.get_theme_stylesheet(theme_type))
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title_label = QLabel("📜 Historial de Versículos")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        count_label = QLabel(f"Total de versículos: {len(self.history)}")
        count_label.setObjectName("subtitle")
        count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(count_label)
        
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        
        # Lista de versículos
        self.history_list = QListWidget()
        self.history_list.setAlternatingRowColors(True)
        self.history_list.itemDoubleClicked.connect(self.show_verse_details)
        
        # Cargar historial
        self.load_history()
        
        layout.addWidget(self.history_list)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.details_button = QPushButton("Ver detalles")
        self.details_button.clicked.connect(self.show_selected_details)
        button_layout.addWidget(self.details_button)
        
        self.clear_button = QPushButton("Limpiar historial")
        self.clear_button.clicked.connect(self.clear_history)
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("Cerrar")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def load_history(self):
        self.history_list.clear()
        
        if not self.history:
            item = QListWidgetItem("No hay versículos en el historial")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor(128, 128, 128))
            self.history_list.addItem(item)
            return
        
        # Ordenar por fecha (más recientes primero)
        sorted_history = sorted(
            self.history, 
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )
        
        for verse in sorted_history:
            # Formatear fecha
            timestamp = verse.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    date_str = dt.strftime("%d/%m/%Y %H:%M")
                except:
                    date_str = timestamp
            else:
                date_str = "Fecha desconocida"
            
            # Crear texto del item
            reference = verse.get("reference", "Referencia desconocida")
            verse_text = verse.get("verse", "")
            if len(verse_text) > 50:
                verse_text = verse_text[:50] + "..."
            
            text = f"{date_str} - {reference}\n{verse_text}"
            
            # Añadir item
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, verse)
            self.history_list.addItem(item)
    
    def show_verse_details(self, item):
        verse = item.data(Qt.ItemDataRole.UserRole)
        if verse:
            self.show_verse_dialog(verse)
    
    def show_selected_details(self):
        """Mostrar detalles del versículo seleccionado"""
        item = self.history_list.currentItem()
        if item:
            verse = item.data(Qt.ItemDataRole.UserRole)
            if verse:
                self.show_verse_dialog(verse)
    
    def show_verse_dialog(self, verse):
        dialog = QDialog(self)
        dialog.setWindowTitle("Detalles del versículo")
        dialog.setMinimumWidth(500)
        dialog.setModal(True)
        
        # Aplicar tema
        parent = self.parent()
        if parent and hasattr(parent, 'current_theme'):
            theme_type = parent.current_theme
            dialog.setStyleSheet(ThemeManager.get_theme_stylesheet(theme_type))
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Referencia
        reference = verse.get("reference", "Referencia desconocida")
        reference_label = QLabel(f"<h3 style='color: #2CA7F8;'>{reference}</h3>")
        reference_label.setTextFormat(Qt.TextFormat.RichText)
        reference_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(reference_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #D8D8D8;")
        layout.addWidget(separator)
        
        # Versículo
        verse_text = verse.get("verse", "")
        verse_label = QLabel(f"<p style='font-size: 14pt; line-height: 1.5;'>{verse_text}</p>")
        verse_label.setWordWrap(True)
        verse_label.setTextFormat(Qt.TextFormat.RichText)
        verse_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(verse_label)
        
        # Información adicional
        info_group = QGroupBox("📋 Información")
        info_layout = QFormLayout()
        info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Versión
        version = verse.get("version", "Desconocida")
        version_name = next((v["name"] for v in AVAILABLE_VERSIONS if v["code"] == version), version)
        info_layout.addRow("Versión:", QLabel(version_name))
        
        # Fecha
        timestamp = verse.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                date_str = dt.strftime("%d/%m/%Y %H:%M:%S")
                info_layout.addRow("Fecha:", QLabel(date_str))
            except:
                pass
        
        # Estudio (si está disponible)
        study = verse.get("study", "")
        if study:
            study_label = QLabel(study)
            study_label.setWordWrap(True)
            info_layout.addRow("Estudio:", study_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Botón para cerrar
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()
    
    def clear_history(self):
        """Limpiar el historial"""
        reply = QMessageBox.question(
            self, "Limpiar historial",
            "¿Está seguro de que desea eliminar todo el historial de versículos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Limpiar historial en la configuración principal
            parent = self.parent()
            if parent and hasattr(parent, 'config'):
                parent.config["verse_history"] = []
                save_config(parent.config)
            
            # Actualizar lista
            self.history = []
            self.load_history()
    
    def closeEvent(self, event):
        """Manejar el cierre de la ventana"""
        print("HistoryWindow cerrada por closeEvent")
        self.reject()

def main():
    """Función principal de la aplicación"""
    print("=== Bible Verse Notifier ===")
    print(f"Configuración: {CONFIG_FILE}")
    
    # Solucionar problema de entorno Qt
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    
    # Crear aplicación Qt estándar
    app = QApplication(sys.argv)
    app.setApplicationName("Bible Verse Notifier")
    app.setOrganizationName("BibleNotifier")
    
    # Crear ventana principal
    window = MainWindow()
    
    # Mostrar u ocultar según configuración
    config = load_config()
    if not config.get("start_minimized", True):
        window.show()
    else:
        window.hide()
    
    # Ejecutar aplicación
    print("✅ Aplicación iniciada correctamente")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
