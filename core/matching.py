"""
HRTech - Matching Engine (Fase 2)
=================================

Motor de recomendação de candidatos usando grafo Neo4j.

Arquitetura:
    PostgreSQL: dados transacionais (Vaga, Candidato, AuditoriaMatch)
    Neo4j: grafo de habilidades e relações de similaridade

Algoritmo de 3 Camadas:
    Camada 1 (60%): Match direto de habilidades obrigatórias
        - Decaimento temporal de 15%/ano para skills defasadas
        - Penalização para skills ausentes ou abaixo do nível mínimo

    Camada 2 (25%): Match por similaridade
        - Usa relação SIMILAR_A do grafo
        - Score parcial proporcional ao peso da similaridade
        - Ex: Tableau similar a Power BI com peso 0.8

    Camada 3 (15%): Compatibilidade de perfil
        - Área de atuação (7.5%)
        - Senioridade (7.5%) - penaliza gaps nos dois sentidos

Score final: 0-100 (candidatos < 40 são filtrados)

Critérios de desempate:
    1. Disponibilidade imediata
    2. Menor gap de senioridade
    3. Data de cadastro mais recente

Decisões Arquiteturais:
-----------------------------------------------------------------------------
1. Query Cypher única vs múltiplas queries
   DECISÃO: Query única com OPTIONAL MATCH
   RAZÃO: Reduz roundtrips ao Neo4j, melhor performance

2. Processamento no Neo4j vs Python
   DECISÃO: Cálculos básicos no Neo4j, agregação final em Python
   RAZÃO: Neo4j otimiza traversal de grafo, Python dá flexibilidade

3. Snapshot de skills na auditoria
   DECISÃO: Sempre salvar snapshot completo
   RAZÃO: LGPD exige reprodutibilidade do cálculo para explicabilidade

4. Threshold de score mínimo
   DECISÃO: 40 pontos (configurável)
   RAZÃO: Abaixo disso a similaridade é muito baixa para ser útil
-----------------------------------------------------------------------------

Uso:
    from core.matching import MatchingEngine

    engine = MatchingEngine()
    resultados = engine.executar_matching(vaga_id=1)

    for r in resultados:
        print(f"{r['candidato_nome']}: {r['score']}")
        print(f"  Gaps: {r['gap_analysis']['texto_explicativo']}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
import logging

from django.db import transaction

from core.models import Vaga, Candidato, AuditoriaMatch
from core.neo4j_connection import run_query

logger = logging.getLogger(__name__)

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


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class MatchingEngine:
    """
    Motor de matching entre candidatos e vagas.

    Responsabilidades:
        1. Buscar vaga no PostgreSQL
        2. Executar query Cypher no Neo4j
        3. Calcular scores com algoritmo de 3 camadas
        4. Gerar gap analysis e texto explicativo
        5. Salvar auditoria no PostgreSQL

    Thread Safety:
        Esta classe é stateless - pode ser usada por múltiplas threads.
        O driver Neo4j já é thread-safe (singleton).

    Example:
        >>> engine = MatchingEngine()
        >>> resultados = engine.executar_matching(vaga_id=1, salvar_auditoria=True)
        >>> print(f"Encontrados {len(resultados)} candidatos")
    """

    def __init__(self, score_minimo: float = SCORE_MINIMO):
        """
        Inicializa o engine.

        Args:
            score_minimo: Score mínimo para incluir candidato nos resultados.
                         Default: 40.0
        """
        self.score_minimo = score_minimo
        logger.debug(f"MatchingEngine inicializado (versão {VERSAO_ALGORITMO})")

    def executar_matching(
        self,
        vaga_id: int,
        salvar_auditoria: bool = True,
        limite: int | None = None
    ) -> list[ResultadoMatch]:
        """
        Executa o matching completo para uma vaga.

        Este é o método principal - orquestra todo o fluxo.

        Args:
            vaga_id: ID da vaga no PostgreSQL
            salvar_auditoria: Se True, salva resultados em AuditoriaMatch
            limite: Número máximo de candidatos a retornar

        Returns:
            Lista de ResultadoMatch ordenada por score (desc)

        Raises:
            Vaga.DoesNotExist: Se vaga não encontrada
            Exception: Erros de conexão Neo4j
        """
        logger.info(f"Iniciando matching para vaga_id={vaga_id}")

        # 1. Buscar vaga no PostgreSQL
        vaga = Vaga.objects.get(pk=vaga_id)
        logger.debug(f"Vaga encontrada: {vaga.titulo}")

        # 2. Extrair skills da vaga
        skills_obrigatorias = vaga.skills_obrigatorias or []
        skills_desejaveis = vaga.skills_desejaveis or []

        if not skills_obrigatorias:
            logger.warning(f"Vaga {vaga_id} não tem skills obrigatórias definidas")
            return []

        # 3. Executar query no Neo4j
        dados_neo4j = self._buscar_candidatos_neo4j(
            skills_obrigatorias=skills_obrigatorias,
            skills_desejaveis=skills_desejaveis,
            area_vaga=vaga.area,
            senioridade_vaga=vaga.senioridade_desejada
        )

        logger.debug(f"Neo4j retornou {len(dados_neo4j)} candidatos")

        # 4. Calcular scores e gerar resultados
        resultados = self._calcular_scores(
            dados_neo4j=dados_neo4j,
            vaga=vaga,
            skills_obrigatorias=skills_obrigatorias,
            skills_desejaveis=skills_desejaveis
        )

        # 5. Filtrar por score mínimo
        resultados = [r for r in resultados if r.score_final >= self.score_minimo]

        # 6. Ordenar (score desc, depois critérios de desempate)
        resultados = self._ordenar_resultados(resultados)

        # 7. Aplicar limite se especificado
        if limite:
            resultados = resultados[:limite]

        logger.info(f"Matching concluído: {len(resultados)} candidatos acima do threshold")

        # 8. Salvar auditoria se solicitado
        if salvar_auditoria:
            self._salvar_auditoria(vaga, resultados)

        return resultados

    def _buscar_candidatos_neo4j(
        self,
        skills_obrigatorias: list[dict],
        skills_desejaveis: list[dict],
        area_vaga: str,
        senioridade_vaga: str
    ) -> list[dict]:
        """
        Executa query Cypher para buscar candidatos e suas skills.

        A query faz:
        1. Match de candidatos com pelo menos UMA skill obrigatória (ou similar)
        2. Coleta todas as skills do candidato com propriedades
        3. Coleta relações de similaridade relevantes
        4. Retorna área e senioridade do candidato

        Args:
            skills_obrigatorias: Lista de skills obrigatórias da vaga
            skills_desejaveis: Lista de skills desejáveis da vaga
            area_vaga: Área da vaga (ex: "Dados")
            senioridade_vaga: Senioridade desejada

        Returns:
            Lista de dicionários com dados dos candidatos do Neo4j
        """
        # Extrair nomes das skills para a query
        nomes_obrigatorias = [s['nome'] for s in skills_obrigatorias]
        nomes_desejaveis = [s['nome'] for s in skills_desejaveis]
        todas_skills = nomes_obrigatorias + nomes_desejaveis

        # Query Cypher otimizada
        # =====================
        # Decisão: usar OPTIONAL MATCH para skills e similaridades
        # Razão: candidato pode não ter todas as skills, mas queremos dados parciais
        #
        # Decisão: coletar similaridades na mesma query
        # Razão: evita roundtrip adicional, Neo4j otimiza isso bem
        #
        # IMPORTANTE: Neo4j armazena apenas uuid do candidato.
        # Nome, email, senioridade vêm do PostgreSQL (persistência poliglota)
        query = """
        // Buscar candidatos que têm pelo menos uma skill relevante (direta ou similar)
        MATCH (c:Candidato)

        // Coletar todas as skills do candidato
        OPTIONAL MATCH (c)-[tem:TEM_HABILIDADE]->(h:Habilidade)

        // Coletar área do candidato
        OPTIONAL MATCH (c)-[:ATUA_EM]->(area:Area)

        // Para cada skill, verificar se tem similar às skills da vaga
        OPTIONAL MATCH (h)-[sim:SIMILAR_A]-(h2:Habilidade)
        WHERE h2.nome IN $todas_skills

        WITH c, area,
             collect(DISTINCT {
                 nome: h.nome,
                 nivel: tem.nivel,
                 anos_experiencia: tem.anos_experiencia,
                 ano_ultima_utilizacao: tem.ano_ultima_utilizacao,
                 inferido: tem.inferido
             }) AS skills,
             collect(DISTINCT {
                 skill_candidato: h.nome,
                 skill_vaga: h2.nome,
                 peso: sim.peso
             }) AS similaridades

        // Filtrar para ter pelo menos uma skill relevante
        WHERE any(s IN skills WHERE s.nome IN $todas_skills)
           OR any(sim IN similaridades WHERE sim.skill_vaga IS NOT NULL)

        RETURN c.uuid AS candidato_id,
               area.nome AS candidato_area,
               skills,
               similaridades
        """

        parametros = {
            'todas_skills': todas_skills,
            'skills_obrigatorias': nomes_obrigatorias,
            'skills_desejaveis': nomes_desejaveis,
            'area_vaga': area_vaga,
        }

        try:
            resultados = run_query(query, parametros)
            return resultados
        except Exception as e:
            logger.error(f"Erro na query Neo4j: {e}")
            raise

    def _calcular_scores(
        self,
        dados_neo4j: list[dict],
        vaga: Vaga,
        skills_obrigatorias: list[dict],
        skills_desejaveis: list[dict]
    ) -> list[ResultadoMatch]:
        """
        Calcula scores para cada candidato usando o algoritmo de 3 camadas.

        IMPORTANTE: Neo4j retorna apenas uuid e skills.
        Dados do candidato (nome, email, senioridade) são buscados do PostgreSQL.

        Args:
            dados_neo4j: Dados dos candidatos vindos do Neo4j
            vaga: Objeto Vaga do Django
            skills_obrigatorias: Skills obrigatórias da vaga
            skills_desejaveis: Skills desejáveis da vaga

        Returns:
            Lista de ResultadoMatch com scores calculados
        """
        resultados = []

        # Criar mapa de skills da vaga para acesso rápido
        mapa_obrigatorias = {s['nome']: s.get('nivel_minimo', 1) for s in skills_obrigatorias}
        mapa_desejaveis = {s['nome']: s.get('nivel_minimo', 1) for s in skills_desejaveis}

        # Extrair UUIDs para buscar dados do PostgreSQL em batch
        uuids = [d['candidato_id'] for d in dados_neo4j if d.get('candidato_id')]

        # Buscar candidatos do PostgreSQL em uma única query (otimização)
        candidatos_pg = {
            str(c.id): c
            for c in Candidato.objects.filter(id__in=uuids)
        }

        for dados in dados_neo4j:
            try:
                candidato_uuid = dados.get('candidato_id')
                if not candidato_uuid:
                    continue

                # Buscar dados do PostgreSQL
                candidato_pg = candidatos_pg.get(str(candidato_uuid))
                if not candidato_pg:
                    logger.warning(f"Candidato {candidato_uuid} não encontrado no PostgreSQL")
                    continue

                # Enriquecer dados com informações do PostgreSQL
                dados_enriquecidos = {
                    **dados,
                    'candidato_nome': candidato_pg.nome,
                    'candidato_email': candidato_pg.email,
                    'candidato_senioridade': candidato_pg.senioridade,
                    'candidato_disponivel': candidato_pg.disponivel,
                }

                resultado = self._calcular_score_candidato(
                    dados=dados_enriquecidos,
                    vaga=vaga,
                    mapa_obrigatorias=mapa_obrigatorias,
                    mapa_desejaveis=mapa_desejaveis
                )
                resultados.append(resultado)
            except Exception as e:
                logger.warning(
                    f"Erro ao calcular score para candidato {dados.get('candidato_id')}: {e}"
                )
                continue

        return resultados

    def _calcular_score_candidato(
        self,
        dados: dict,
        vaga: Vaga,
        mapa_obrigatorias: dict[str, int],
        mapa_desejaveis: dict[str, int]
    ) -> ResultadoMatch:
        """
        Calcula score para um único candidato.

        Implementa as 3 camadas do algoritmo:

        CAMADA 1 (60%): Match direto de skills obrigatórias
        -------------------------------------------------
        Para cada skill obrigatória:
        - Se candidato tem a skill diretamente:
            - Aplica decaimento temporal: nivel_efetivo = nivel * (0.85 ^ anos_inativo)
            - Score = min(1.0, nivel_efetivo / nivel_minimo)
        - Se não tem, score = 0 (será tratado na Camada 2 ou Gap)

        CAMADA 2 (25%): Match por similaridade
        -------------------------------------
        Para skills obrigatórias que o candidato NÃO tem diretamente:
        - Busca skills similares que o candidato possui
        - Score = score_skill_similar * peso_similaridade
        - Ex: Tem Tableau (nível 4), vaga pede Power BI
              Se SIMILAR_A peso=0.8, contribui parcialmente

        CAMADA 3 (15%): Compatibilidade de perfil
        ----------------------------------------
        - Área (7.5%): +100% se área bate, 50% se não
        - Senioridade (7.5%): 100% se bate, penaliza gap
            - Sênior → Júnior: penaliza (overqualified)
            - Júnior → Sênior: penaliza mais (underqualified)

        Args:
            dados: Dados do candidato (Neo4j + PostgreSQL combinados)
            vaga: Objeto Vaga
            mapa_obrigatorias: {nome_skill: nivel_minimo}
            mapa_desejaveis: {nome_skill: nivel_minimo}

        Returns:
            ResultadoMatch com todos os scores e análises
        """
        # Dados já vêm enriquecidos do _calcular_scores (PostgreSQL + Neo4j)
        disponivel = dados.get('candidato_disponivel', True)

        # Preparar estruturas de dados
        skills_candidato = {s['nome']: s for s in dados.get('skills', []) if s['nome']}
        similaridades = dados.get('similaridades', [])

        # Criar mapa de similaridades: skill_vaga -> [(skill_candidato, peso)]
        mapa_similaridades: dict[str, list[tuple[str, float]]] = {}
        for sim in similaridades:
            if sim.get('skill_vaga') and sim.get('skill_candidato'):
                skill_vaga = sim['skill_vaga']
                if skill_vaga not in mapa_similaridades:
                    mapa_similaridades[skill_vaga] = []
                mapa_similaridades[skill_vaga].append(
                    (sim['skill_candidato'], sim.get('peso', 0.5))
                )

        # =================================================================
        # CAMADA 1: Match direto (60%)
        # =================================================================
        score_camada_1 = 0.0
        skills_matched = []
        skills_ausentes = []
        skills_abaixo_nivel = []

        for skill_nome, nivel_minimo in mapa_obrigatorias.items():
            if skill_nome in skills_candidato:
                # Candidato tem a skill diretamente
                skill_data = skills_candidato[skill_nome]
                nivel = skill_data.get('nivel', 0) or 0
                ano_uso = skill_data.get('ano_ultima_utilizacao', ANO_ATUAL) or ANO_ATUAL

                # Calcular decaimento temporal
                anos_inativo = max(0, ANO_ATUAL - ano_uso)
                nivel_efetivo = nivel * (FATOR_DECAIMENTO ** anos_inativo)

                # Score normalizado (0 a 1)
                score_skill = min(1.0, nivel_efetivo / nivel_minimo) if nivel_minimo > 0 else 1.0

                skills_matched.append(SkillMatch(
                    nome=skill_nome,
                    nivel_candidato=nivel,
                    nivel_minimo=nivel_minimo,
                    nivel_efetivo=nivel_efetivo,
                    anos_inativo=anos_inativo,
                    match_direto=True,
                    score_contribuicao=score_skill
                ))

                score_camada_1 += score_skill

                # Verificar se abaixo do nível
                if nivel_efetivo < nivel_minimo:
                    skills_abaixo_nivel.append({
                        'nome': skill_nome,
                        'nivel_atual': nivel,
                        'nivel_efetivo': round(nivel_efetivo, 1),
                        'nivel_minimo': nivel_minimo,
                        'anos_inativo': anos_inativo
                    })
            else:
                # Skill não encontrada diretamente, marcar como ausente
                # (pode ser preenchida na Camada 2 via similaridade)
                skills_ausentes.append(skill_nome)

        # Normalizar score da Camada 1 (média das skills)
        if mapa_obrigatorias:
            score_camada_1 = (score_camada_1 / len(mapa_obrigatorias)) * 100

        # =================================================================
        # CAMADA 2: Match por similaridade (25%)
        # =================================================================
        score_camada_2 = 0.0
        skills_cobertas_por_similaridade = []

        for skill_ausente in skills_ausentes[:]:  # Cópia para iterar e modificar
            if skill_ausente in mapa_similaridades:
                # Encontrar a melhor skill similar que o candidato possui
                melhor_score = 0.0
                melhor_match = None

                for skill_similar, peso in mapa_similaridades[skill_ausente]:
                    if skill_similar in skills_candidato:
                        skill_data = skills_candidato[skill_similar]
                        nivel = skill_data.get('nivel', 0) or 0
                        ano_uso = skill_data.get('ano_ultima_utilizacao', ANO_ATUAL) or ANO_ATUAL

                        anos_inativo = max(0, ANO_ATUAL - ano_uso)
                        nivel_efetivo = nivel * (FATOR_DECAIMENTO ** anos_inativo)

                        nivel_minimo = mapa_obrigatorias.get(skill_ausente, 1)
                        score_base = min(1.0, nivel_efetivo / nivel_minimo) if nivel_minimo > 0 else 1.0
                        score_com_similaridade = score_base * peso

                        if score_com_similaridade > melhor_score:
                            melhor_score = score_com_similaridade
                            melhor_match = SkillMatch(
                                nome=skill_ausente,
                                nivel_candidato=nivel,
                                nivel_minimo=nivel_minimo,
                                nivel_efetivo=nivel_efetivo * peso,
                                anos_inativo=anos_inativo,
                                match_direto=False,
                                skill_similar=skill_similar,
                                peso_similaridade=peso,
                                score_contribuicao=score_com_similaridade
                            )

                if melhor_match:
                    skills_matched.append(melhor_match)
                    score_camada_2 += melhor_score
                    skills_cobertas_por_similaridade.append(skill_ausente)

        # Remover skills cobertas por similaridade da lista de ausentes
        skills_ausentes = [s for s in skills_ausentes if s not in skills_cobertas_por_similaridade]

        # Normalizar Camada 2 (proporção de skills ausentes cobertas)
        total_poderiam_ser_cobertas = len(skills_ausentes) + len(skills_cobertas_por_similaridade)
        if total_poderiam_ser_cobertas > 0:
            score_camada_2 = (score_camada_2 / total_poderiam_ser_cobertas) * 100
        else:
            # Todas as skills foram match direto, Camada 2 não se aplica
            score_camada_2 = 100.0 if not skills_ausentes else 0.0

        # =================================================================
        # CAMADA 3: Compatibilidade de perfil (15%)
        # =================================================================

        # 3a. Match de área (50% da Camada 3 = 7.5% total)
        area_candidato = dados.get('candidato_area', '')
        area_match = 1.0 if area_candidato and area_candidato.lower() == vaga.area.lower() else 0.5

        # 3b. Match de senioridade (50% da Camada 3 = 7.5% total)
        senioridade_candidato = dados.get('candidato_senioridade', 'junior')
        senioridade_vaga = vaga.senioridade_desejada

        valor_candidato = SENIORIDADE_VALOR.get(senioridade_candidato, 1)
        valor_vaga = SENIORIDADE_VALOR.get(senioridade_vaga, 2)
        gap_senioridade = abs(valor_candidato - valor_vaga)

        # Penalização por gap de senioridade
        # Gap 0: 100%, Gap 1: 60%, Gap 2: 30%
        if gap_senioridade == 0:
            senioridade_match = 1.0
        elif gap_senioridade == 1:
            senioridade_match = 0.6
        else:
            senioridade_match = 0.3

        score_camada_3 = (
            (area_match * PESO_AREA + senioridade_match * PESO_SENIORIDADE) * 100
        )

        # =================================================================
        # SCORE FINAL
        # =================================================================
        score_final = (
            score_camada_1 * PESO_CAMADA_1 +
            score_camada_2 * PESO_CAMADA_2 +
            score_camada_3 * PESO_CAMADA_3
        )

        # =================================================================
        # GAP ANALYSIS
        # =================================================================

        # Skills desejáveis ausentes
        skills_desejaveis_ausentes = [
            s for s in mapa_desejaveis.keys()
            if s not in skills_candidato and s not in mapa_similaridades
        ]

        # Gerar texto explicativo
        texto_explicativo = self._gerar_texto_explicativo(
            score_final=score_final,
            skills_ausentes=skills_ausentes,
            skills_abaixo_nivel=skills_abaixo_nivel,
            skills_desejaveis_ausentes=skills_desejaveis_ausentes,
            area_match=area_match == 1.0,
            senioridade_match=senioridade_match,
            gap_senioridade=gap_senioridade,
            senioridade_candidato=senioridade_candidato,
            senioridade_vaga=senioridade_vaga
        )

        gap_analysis = GapAnalysis(
            skills_ausentes=skills_ausentes,
            skills_abaixo_nivel=skills_abaixo_nivel,
            skills_desejaveis_ausentes=skills_desejaveis_ausentes,
            texto_explicativo=texto_explicativo
        )

        # =================================================================
        # MONTAR SNAPSHOT PARA AUDITORIA
        # =================================================================
        snapshot = {
            'candidato_skills': [
                {
                    'nome': s['nome'],
                    'nivel': s.get('nivel'),
                    'ano_ultima_utilizacao': s.get('ano_ultima_utilizacao')
                }
                for s in dados.get('skills', []) if s['nome']
            ],
            'vaga_skills_obrigatorias': list(mapa_obrigatorias.keys()),
            'vaga_skills_desejaveis': list(mapa_desejaveis.keys()),
            'matches': [
                {
                    'skill': sm.nome,
                    'direto': sm.match_direto,
                    'similar_via': sm.skill_similar,
                    'score': sm.score_contribuicao
                }
                for sm in skills_matched
            ]
        }

        return ResultadoMatch(
            candidato_id=dados['candidato_id'],
            candidato_nome=dados['candidato_nome'],
            candidato_email=dados['candidato_email'],
            candidato_senioridade=senioridade_candidato,
            candidato_disponivel=disponivel,
            score_final=round(score_final, 2),
            score_camada_1=round(score_camada_1, 2),
            score_camada_2=round(score_camada_2, 2),
            score_camada_3=round(score_camada_3, 2),
            skills_matched=skills_matched,
            gap_analysis=gap_analysis,
            snapshot_skills=snapshot
        )

    def _gerar_texto_explicativo(
        self,
        score_final: float,
        skills_ausentes: list[str],
        skills_abaixo_nivel: list[dict],
        skills_desejaveis_ausentes: list[str],
        area_match: bool,
        senioridade_match: float,
        gap_senioridade: int,
        senioridade_candidato: str,
        senioridade_vaga: str
    ) -> str:
        """
        Gera texto explicativo humanizado sobre o match.

        Este texto é mostrado para recrutadores entenderem
        rapidamente os pontos fortes e gaps do candidato.
        """
        partes = []

        # Classificação geral
        if score_final >= 80:
            partes.append("Excelente match!")
        elif score_final >= 60:
            partes.append("Bom match com algumas ressalvas.")
        elif score_final >= 40:
            partes.append("Match parcial - avaliar caso a caso.")
        else:
            partes.append("Match baixo.")

        # Skills ausentes
        if skills_ausentes:
            if len(skills_ausentes) == 1:
                partes.append(f"Falta a skill obrigatória: {skills_ausentes[0]}.")
            else:
                partes.append(f"Faltam {len(skills_ausentes)} skills obrigatórias: {', '.join(skills_ausentes)}.")

        # Skills abaixo do nível
        if skills_abaixo_nivel:
            detalhes = []
            for s in skills_abaixo_nivel[:2]:  # Limitar a 2 para não ficar longo
                if s['anos_inativo'] > 0:
                    detalhes.append(
                        f"{s['nome']} (nível {s['nivel_atual']}, mas defasado há {s['anos_inativo']} anos)"
                    )
                else:
                    detalhes.append(
                        f"{s['nome']} (nível {s['nivel_atual']}, mínimo exigido: {s['nivel_minimo']})"
                    )
            partes.append(f"Abaixo do nível em: {'; '.join(detalhes)}.")

        # Senioridade
        if gap_senioridade > 0:
            if senioridade_candidato == 'senior' and senioridade_vaga != 'senior':
                partes.append(f"Candidato sênior para vaga de {senioridade_vaga} (possível overqualification).")
            elif senioridade_candidato == 'junior' and senioridade_vaga == 'senior':
                partes.append("Candidato júnior para vaga sênior (gap significativo).")

        # Área
        if not area_match:
            partes.append("Atua em área diferente da vaga.")

        # Skills desejáveis
        if skills_desejaveis_ausentes:
            partes.append(f"Não possui {len(skills_desejaveis_ausentes)} skill(s) desejável(is).")

        return " ".join(partes)

    def _ordenar_resultados(self, resultados: list[ResultadoMatch]) -> list[ResultadoMatch]:
        """
        Ordena resultados com critérios de desempate.

        Ordem:
        1. Score final (desc)
        2. Disponibilidade imediata (disponível primeiro)
        3. Menor gap de senioridade (não implementado aqui, já está no score)
        4. Data de cadastro mais recente (usaria o PG, simplificado aqui)
        """
        return sorted(
            resultados,
            key=lambda r: (
                -r.score_final,  # Score desc
                -int(r.candidato_disponivel),  # Disponível primeiro
            )
        )

    def _salvar_auditoria(self, vaga: Vaga, resultados: list[ResultadoMatch]) -> None:
        """
        Salva resultados na tabela AuditoriaMatch.

        Usa transaction.atomic para garantir consistência.
        Salva em batch para melhor performance.
        """
        if not resultados:
            logger.debug("Sem resultados para salvar na auditoria")
            return

        auditorias = []

        for resultado in resultados:
            try:
                candidato = Candidato.objects.get(pk=resultado.candidato_id)
            except Candidato.DoesNotExist:
                logger.warning(f"Candidato {resultado.candidato_id} não encontrado no PostgreSQL")
                candidato = None

            auditoria = AuditoriaMatch(
                vaga=vaga,
                candidato=candidato,
                score=Decimal(str(resultado.score_final)),
                snapshot_skills=resultado.snapshot_skills,
                versao_algoritmo=VERSAO_ALGORITMO,
                detalhes_calculo={
                    'camada_1_score': resultado.score_camada_1,
                    'camada_1_peso': PESO_CAMADA_1,
                    'camada_2_score': resultado.score_camada_2,
                    'camada_2_peso': PESO_CAMADA_2,
                    'camada_3_score': resultado.score_camada_3,
                    'camada_3_peso': PESO_CAMADA_3,
                    'score_final': resultado.score_final,
                    'gap_analysis': {
                        'skills_ausentes': resultado.gap_analysis.skills_ausentes,
                        'skills_abaixo_nivel': resultado.gap_analysis.skills_abaixo_nivel,
                        'skills_desejaveis_ausentes': resultado.gap_analysis.skills_desejaveis_ausentes,
                        'texto': resultado.gap_analysis.texto_explicativo
                    }
                }
            )
            auditorias.append(auditoria)

        # Salvar em batch
        with transaction.atomic():
            AuditoriaMatch.objects.bulk_create(auditorias)
            logger.info(f"Salvos {len(auditorias)} registros de auditoria para vaga {vaga.id}")


# =============================================================================
# FUNÇÕES AUXILIARES (para uso direto sem instanciar a classe)
# =============================================================================

def executar_matching_vaga(
    vaga_id: int,
    salvar_auditoria: bool = True,
    score_minimo: float = SCORE_MINIMO,
    limite: int | None = None
) -> list[ResultadoMatch]:
    """
    Função de conveniência para executar matching.

    Wrapper simples que instancia MatchingEngine e executa.

    Args:
        vaga_id: ID da vaga
        salvar_auditoria: Se salva na AuditoriaMatch
        score_minimo: Score mínimo para incluir
        limite: Máximo de resultados

    Returns:
        Lista de ResultadoMatch

    Example:
        >>> from core.matching import executar_matching_vaga
        >>> resultados = executar_matching_vaga(vaga_id=1)
    """
    engine = MatchingEngine(score_minimo=score_minimo)
    return engine.executar_matching(
        vaga_id=vaga_id,
        salvar_auditoria=salvar_auditoria,
        limite=limite
    )


def resultado_para_dict(resultado: ResultadoMatch) -> dict[str, Any]:
    """
    Converte ResultadoMatch para dicionário serializável.

    Útil para APIs REST ou serialização JSON.
    """
    return {
        'candidato_id': resultado.candidato_id,
        'candidato_nome': resultado.candidato_nome,
        'candidato_email': resultado.candidato_email,
        'candidato_senioridade': resultado.candidato_senioridade,
        'candidato_disponivel': resultado.candidato_disponivel,
        'score_final': resultado.score_final,
        'breakdown': {
            'camada_1': resultado.score_camada_1,
            'camada_2': resultado.score_camada_2,
            'camada_3': resultado.score_camada_3,
        },
        'gap_analysis': {
            'skills_ausentes': resultado.gap_analysis.skills_ausentes,
            'skills_abaixo_nivel': resultado.gap_analysis.skills_abaixo_nivel,
            'skills_desejaveis_ausentes': resultado.gap_analysis.skills_desejaveis_ausentes,
            'texto_explicativo': resultado.gap_analysis.texto_explicativo,
        }
    }
