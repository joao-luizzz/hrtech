import logging
from core.models import Vaga
from core.neo4j_connection import run_query
from core.matching.types import SCORE_MINIMO, ResultadoMatch, VERSAO_ALGORITMO
from core.matching.scoring import calcular_scores
from core.matching.tiebreak import ordenar_resultados
from core.matching.auditing import salvar_auditoria as salvar_auditoria_fn

logger = logging.getLogger(__name__)

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
    """

    def __init__(self, score_minimo: float = SCORE_MINIMO, organization=None, allow_global: bool = False):
        """
        Inicializa o engine.

        Args:
            score_minimo: Score mínimo para incluir candidato nos resultados.
                         Default: 40.0
            organization: Tenant para filtrar vagas (SECURITY: required para multi-tenant)
            allow_global: Se True, permite rodar matching sem tenant isolation (admin only).
        """
        if organization is None and not allow_global:
            raise ValueError("Organization é obrigatório para execução do matching (tenant isolation).")
        
        self.score_minimo = score_minimo
        self.organization = organization  # SECURITY: Tenant isolation
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
        # SECURITY: Filtrar por organization para tenant isolation
        if self.organization:
            vaga = Vaga.objects.get(pk=vaga_id, organization=self.organization)
        else:
            vaga = Vaga.objects.get(pk=vaga_id)
        logger.debug(f"Vaga encontrada: {vaga.titulo}")

        # 2. Extrair skills da vaga
        skills_obrigatorias = vaga.skills_obrigatorias or []
        skills_desejaveis = vaga.skills_desejaveis or []

        if not skills_obrigatorias:
            logger.warning(f"Vaga {vaga_id} não tem skills obrigatórias definidas")
            return []

        # 3. Executar query no Neo4j
        # SECURITY: Passar organization_id para filtro no Neo4j
        organization_id = str(self.organization.id) if self.organization else None
        
        dados_neo4j = self._buscar_candidatos_neo4j(
            skills_obrigatorias=skills_obrigatorias,
            skills_desejaveis=skills_desejaveis,
            area_vaga=vaga.area,
            senioridade_vaga=vaga.senioridade_desejada,
            organization_id=organization_id,
        )

        logger.debug(f"Neo4j retornou {len(dados_neo4j)} candidatos")

        # 4. Calcular scores e gerar resultados
        resultados = calcular_scores(
            dados_neo4j=dados_neo4j,
            vaga=vaga,
            skills_obrigatorias=skills_obrigatorias,
            skills_desejaveis=skills_desejaveis
        )

        # 5. Filtrar por score mínimo
        resultados = [r for r in resultados if r.score_final >= self.score_minimo]

        # 6. Ordenar (score desc, depois critérios de desempate)
        resultados = ordenar_resultados(resultados)

        # 7. Aplicar limite se especificado
        if limite:
            resultados = resultados[:limite]

        logger.info(f"Matching concluído: {len(resultados)} candidatos acima do threshold")

        # 8. Salvar auditoria se solicitado
        if salvar_auditoria:
            salvar_auditoria_fn(vaga, resultados)

        return resultados

    def _buscar_candidatos_neo4j(
        self,
        skills_obrigatorias: list[dict],
        skills_desejaveis: list[dict],
        area_vaga: str,
        senioridade_vaga: str,
        organization_id: str | None = None,  # SECURITY: Tenant isolation
    ) -> list[dict]:
        """
        Executa query Cypher para buscar candidatos e suas skills.
        """
        nomes_obrigatorias = [s['nome'] for s in skills_obrigatorias]
        nomes_desejaveis = [s['nome'] for s in skills_desejaveis]
        todas_skills = nomes_obrigatorias + nomes_desejaveis

        query = """
        // Buscar candidatos que têm pelo menos uma skill relevante (direta ou similar)
        // SECURITY: Filtrar por organization_id para tenant isolation
        MATCH (c:Candidato)
        WHERE ($organization_id IS NULL OR c.organization_id = $organization_id)

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
            'organization_id': organization_id,
        }

        try:
            resultados = run_query(query, parametros)
            return resultados
        except Exception as e:
            logger.error(f"Erro na query Neo4j: {e}")
            raise

