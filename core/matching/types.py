from dataclasses import dataclass, field
from datetime import datetime

# =============================================================================
# CONSTANTES DO ALGORITMO
# =============================================================================

# Versão do algoritmo - incrementar a cada mudança significativa
VERSAO_ALGORITMO = "2.0.0"

# Pesos das camadas (devem somar 1.0)
PESO_CAMADA_1 = 0.60  # Match direto de skills
PESO_CAMADA_2 = 0.25  # Match por similaridade
PESO_CAMADA_3 = 0.15  # Compatibilidade de perfil

# Peso das subcategorias da Camada 3
PESO_AREA = 0.50      # 50% da Camada 3 = 7.5% do total
PESO_SENIORIDADE = 0.50  # 50% da Camada 3 = 7.5% do total

# Decaimento temporal: nivel * (FATOR_DECAIMENTO ^ anos_inativo)
FATOR_DECAIMENTO = 0.85  # 15% de perda por ano

# Score mínimo para aparecer nos resultados
SCORE_MINIMO = 40.0

# Ano atual para cálculo de defasagem
ANO_ATUAL = datetime.now().year

# Mapa de senioridade para valor numérico (para cálculo de gap)
SENIORIDADE_VALOR = {
    'junior': 1,
    'pleno': 2,
    'senior': 3,
}

# =============================================================================
# DATACLASSES PARA TIPAGEM FORTE
# =============================================================================

@dataclass
class SkillMatch:
    """Representa o match de uma skill específica."""
    nome: str
    nivel_candidato: int
    nivel_minimo: int
    nivel_efetivo: float  # Após decaimento
    anos_inativo: int
    match_direto: bool
    skill_similar: str | None = None  # Se match por similaridade
    peso_similaridade: float = 1.0
    score_contribuicao: float = 0.0


@dataclass
class GapAnalysis:
    """Análise de gaps do candidato em relação à vaga."""
    skills_ausentes: list[str] = field(default_factory=list)
    skills_abaixo_nivel: list[dict] = field(default_factory=list)
    skills_desejaveis_ausentes: list[str] = field(default_factory=list)
    texto_explicativo: str = ""


@dataclass
class ResultadoMatch:
    """Resultado do matching para um candidato."""
    candidato_id: str
    candidato_nome: str
    candidato_email: str
    candidato_senioridade: str
    candidato_disponivel: bool
    score_final: float
    score_camada_1: float
    score_camada_2: float
    score_camada_3: float
    skills_matched: list[SkillMatch] = field(default_factory=list)
    gap_analysis: GapAnalysis = field(default_factory=GapAnalysis)
    snapshot_skills: dict = field(default_factory=dict)
