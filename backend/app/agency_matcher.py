#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import re
import json
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz, process
import logging

logger = logging.getLogger(__name__)

class AdvancedAgencyMatcher:
    """
    Sistema avanzado de matching de agencias con múltiples técnicas de precisión:
    1. Matching exacto por código
    2. Fuzzy matching por nombre
    3. Extracción de patrones de códigos
    4. Normalización de texto
    5. Filtrado de grupos SURIEL
    """
    
    def __init__(self, excel_path: str = "DataAgencias.xlsx"):
        self.excel_path = excel_path
        self.agencies_data = {}
        self.code_patterns = {}
        self.suriel_groups = set()
        self.load_agencies_data()
    
    def load_agencies_data(self):
        """Cargar y procesar datos del Excel con optimizaciones"""
        try:
            logger.info(f"Cargando datos de agencias desde {self.excel_path}")
            
            # Leer Excel
            df = pd.read_excel(self.excel_path)
            
            # Identificar grupos SURIEL
            suriel_mask = df['Grupo'].str.contains('SURIEL', case=False, na=False)
            self.suriel_groups = set(df[suriel_mask]['Grupo'].unique())
            
            logger.info(f"Grupos SURIEL identificados: {len(self.suriel_groups)}")
            for grupo in sorted(self.suriel_groups):
                logger.info(f"  - {grupo}")
            
            # Filtrar terminales NO-SURIEL
            df_filtered = df[~suriel_mask].copy()
            
            logger.info(f"Terminales cargadas: {len(df)} total, {len(df_filtered)} NO-SURIEL")
            
            # Crear múltiples índices para matching
            self._create_matching_indices(df_filtered)
            
            # Guardar como JSON para backup
            self._save_to_json(df_filtered)
            
        except Exception as e:
            logger.error(f"Error cargando datos de agencias: {e}")
            raise
    
    def _create_matching_indices(self, df: pd.DataFrame):
        """Crear múltiples índices para diferentes técnicas de matching"""
        
        for _, row in df.iterrows():
            codigo = str(row['Codigo']).strip()
            terminal = str(row['Terminal']).strip()
            grupo = str(row['Grupo']).strip()
            
            # 1. Índice por código exacto
            self.agencies_data[codigo] = {
                'codigo': codigo,
                'terminal': terminal,
                'grupo': grupo,
                'normalized_terminal': self._normalize_text(terminal)
            }
            
            # 2. Extraer códigos adicionales del terminal
            extracted_codes = self._extract_codes_from_terminal(terminal)
            for extracted_code in extracted_codes:
                if extracted_code not in self.agencies_data:
                    self.agencies_data[extracted_code] = {
                        'codigo': codigo,
                        'terminal': terminal,
                        'grupo': grupo,
                        'normalized_terminal': self._normalize_text(terminal),
                        'extracted_from': terminal
                    }
            
            # 3. Crear patrones de códigos
            self._create_code_patterns(codigo, terminal, grupo)
    
    def _extract_codes_from_terminal(self, terminal: str) -> List[str]:
        """Extraer todos los códigos posibles del nombre del terminal"""
        codes = []
        
        # Patrones de códigos comunes
        patterns = [
            r'\b(\d{6,7})\b',  # Códigos de 6-7 dígitos
            r'\b(\d{4,5})\b',  # Códigos de 4-5 dígitos
            r'(\d{3,4})\s*\|',  # Códigos antes de |
            r'\|\s*(\d{3,7})',  # Códigos después de |
            r'^(\d{3,7})',     # Códigos al inicio
            r'(\d{3,7})\s*-',  # Códigos antes de -
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, terminal)
            codes.extend(matches)
        
        # Limpiar y filtrar códigos
        cleaned_codes = []
        for code in codes:
            code = code.strip()
            if len(code) >= 3 and code.isdigit():
                cleaned_codes.append(code)
                # También agregar versiones con ceros a la izquierda
                if len(code) < 6:
                    cleaned_codes.append(code.zfill(6))
                if len(code) < 7:
                    cleaned_codes.append(code.zfill(7))
        
        return list(set(cleaned_codes))
    
    def _create_code_patterns(self, codigo: str, terminal: str, grupo: str):
        """Crear patrones de códigos para matching flexible"""
        # Patrones basados en longitud
        code_len = len(codigo)
        if code_len not in self.code_patterns:
            self.code_patterns[code_len] = {}
        
        self.code_patterns[code_len][codigo] = {
            'terminal': terminal,
            'grupo': grupo
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalizar texto para comparación"""
        if pd.isna(text):
            return ""
        
        # Convertir a minúsculas y remover caracteres especiales
        normalized = re.sub(r'[^\w\s]', ' ', str(text).lower())
        # Remover espacios múltiples
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _save_to_json(self, df: pd.DataFrame):
        """Guardar datos como JSON para backup y debugging"""
        try:
            json_data = {
                'agencies': df.to_dict('records'),
                'suriel_groups': list(self.suriel_groups),
                'total_agencies': len(df),
                'total_groups': df['Grupo'].nunique()
            }
            
            with open('backend/data/agencies_data.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
                
            logger.info("Datos guardados en agencies_data.json")
        except Exception as e:
            logger.warning(f"No se pudo guardar JSON: {e}")
    
    def find_agency_group(self, agency_code: str, agency_name: str) -> Optional[Dict]:
        """
        Encontrar el grupo de una agencia usando múltiples técnicas avanzadas
        """
        
        # Técnica 1: Matching exacto por código
        result = self._exact_code_match(agency_code)
        if result:
            logger.debug(f"Matching exacto encontrado para {agency_code}")
            return result
        
        # Técnica 2: Matching por códigos extraídos
        result = self._extracted_code_match(agency_code, agency_name)
        if result:
            logger.debug(f"Matching por extracción encontrado para {agency_code}")
            return result
        
        # Técnica 3: Fuzzy matching por nombre
        result = self._fuzzy_name_match(agency_name)
        if result:
            logger.debug(f"Fuzzy matching encontrado para {agency_name}")
            return result
        
        # Técnica 4: Matching por patrones de longitud
        result = self._pattern_length_match(agency_code)
        if result:
            logger.debug(f"Pattern matching encontrado para {agency_code}")
            return result
        
        logger.warning(f"No se encontró match para {agency_code} - {agency_name}")
        return None
    
    def _exact_code_match(self, agency_code: str) -> Optional[Dict]:
        """Matching exacto por código"""
        clean_code = str(agency_code).strip()
        
        if clean_code in self.agencies_data:
            return self.agencies_data[clean_code]
        
        return None
    
    def _extracted_code_match(self, agency_code: str, agency_name: str) -> Optional[Dict]:
        """Matching usando códigos extraídos del nombre de la agencia"""
        
        # Extraer códigos del nombre de la agencia del scraping
        extracted_codes = self._extract_codes_from_terminal(agency_name)
        extracted_codes.append(agency_code.strip())
        
        for code in extracted_codes:
            if code in self.agencies_data:
                return self.agencies_data[code]
        
        return None
    
    def _fuzzy_name_match(self, agency_name: str, threshold: int = 85) -> Optional[Dict]:
        """Fuzzy matching por nombre de terminal"""
        
        normalized_input = self._normalize_text(agency_name)
        
        best_match = None
        best_score = 0
        
        for data in self.agencies_data.values():
            if 'normalized_terminal' in data:
                score = fuzz.partial_ratio(normalized_input, data['normalized_terminal'])
                
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = data
        
        if best_match:
            logger.debug(f"Fuzzy match score: {best_score}")
            return best_match
        
        return None
    
    def _pattern_length_match(self, agency_code: str) -> Optional[Dict]:
        """Matching por patrones de longitud de código"""
        
        code_len = len(str(agency_code).strip())
        
        if code_len in self.code_patterns:
            # Buscar códigos similares de la misma longitud
            for code, data in self.code_patterns[code_len].items():
                if self._codes_similar(agency_code, code):
                    return {
                        'codigo': code,
                        'terminal': data['terminal'],
                        'grupo': data['grupo'],
                        'pattern_match': True
                    }
        
        return None
    
    def _codes_similar(self, code1: str, code2: str, threshold: float = 0.8) -> bool:
        """Verificar si dos códigos son similares"""
        return SequenceMatcher(None, str(code1), str(code2)).ratio() >= threshold
    
    def is_suriel_group(self, group_name: str) -> bool:
        """Verificar si un grupo es SURIEL"""
        if not group_name:
            return False
        
        return 'suriel' in group_name.lower()
    
    def get_statistics(self) -> Dict:
        """Obtener estadísticas del sistema de matching"""
        return {
            'total_agencies': len(self.agencies_data),
            'suriel_groups': len(self.suriel_groups),
            'code_patterns': sum(len(patterns) for patterns in self.code_patterns.values()),
            'suriel_groups_list': list(self.suriel_groups)
        }

# Instancia global del matcher
agency_matcher = None

def get_agency_matcher() -> AdvancedAgencyMatcher:
    """Obtener instancia global del matcher"""
    global agency_matcher
    if agency_matcher is None:
        agency_matcher = AdvancedAgencyMatcher()
    return agency_matcher 