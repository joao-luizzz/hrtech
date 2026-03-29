"""
HRTech - Interview Neo4j Service
=================================

Neo4j integration for AI-powered interview generation.

This service handles Neo4j queries to extract skill gaps for a candidate
relative to a job position. These gaps are used as input to the OpenAI
prompt for personalized interview question generation.

Architecture:
- Wraps Neo4j queries in a service class for dependency injection/mocking
- Uses the singleton Neo4j driver from core.neo4j_connection
- Returns standardized data structure for AI prompt construction
- Handles connection errors gracefully with logging

Decisões Arquiteturais:
1. Service class instead of raw queries - enables testing with mocks
2. Singleton driver pattern - reuses Neo4j connection pool
3. Comprehensive error handling - logs without PII, re-raises with context
4. Type hints for all parameters and returns - ensures API clarity
"""

import logging
from typing import Dict, List, Optional

from core.neo4j_connection import get_neo4j_driver

logger = logging.getLogger(__name__)


class InterviewNeo4jService:
    """
    Service for Neo4j queries related to interview generation.
    
    Responsible for extracting skill gaps between a candidate's current
    skills and the requirements of a job position. This gap analysis
    is used to generate targeted interview questions.
    """

    def __init__(self):
        """Initialize service with Neo4j driver access."""
        self.driver = get_neo4j_driver()

    def get_candidate_skill_gaps(
        self,
        candidate_id: str,
        vaga_id: str
    ) -> Dict:
        """
        Get skill gaps for a candidate relative to a job position.
        
        Executes a Cypher query against Neo4j to:
        1. Find the job position (Vaga) and its required skills
        2. Find the candidate and their current skills
        3. Identify which required skills the candidate is missing or lacks
        4. Return structured gap data for interview prompt construction
        
        Args:
            candidate_id (str): UUID of candidate from PostgreSQL
            vaga_id (str): UUID of job position from PostgreSQL
        
        Returns:
            dict with structure:
            {
                'gaps': [
                    {
                        'nome': 'Python',
                        'nivel_minimo': 3,
                        'nivel_candidato': 1,
                        'gap': 2
                    },
                    ...
                ],
                'has_gaps': bool (True if gaps exist, False if 100% match),
                'total_required': int (total required skills for job),
                'total_matched': int (skills candidate has at required level),
            }
        
        Raises:
            Neo4jException: If connection fails or query times out
        """
        # Cypher query to extract candidate skill gaps
        # Strategy: Use OPTIONAL MATCH to collect skills even if candidate
        # has incomplete data, then filter to identify gaps
        query = """
        // Find the job position and its required skills
        MATCH (v:Vaga {uuid: $vaga_id})
        WITH v
        
        // Find the candidate
        MATCH (c:Candidato {uuid: $candidate_id})
        WITH v, c
        
        // Collect candidate's skills
        OPTIONAL MATCH (c)-[tem:TEM_HABILIDADE]->(h_cand:Habilidade)
        WITH v, c, 
             collect(DISTINCT {
                 nome: h_cand.nome,
                 nivel: coalesce(tem.nivel, 0),
                 anos_experiencia: tem.anos_experiencia
             }) AS candidate_skills
        
        // Parse required skills from vaga (stored as JSON in PostgreSQL)
        // For Neo4j, we'll extract from related Skill nodes
        OPTIONAL MATCH (v)-[requer:REQUER]->(h_req:Habilidade)
        WITH v, c, candidate_skills,
             collect(DISTINCT {
                 nome: h_req.nome,
                 nivel_minimo: coalesce(requer.nivel_minimo, 2)
             }) AS vaga_skills
        
        // Calculate gaps: skills required but missing or below level
        WITH candidate_skills, vaga_skills,
             [skill IN vaga_skills WHERE NOT any(cs IN candidate_skills WHERE cs.nome = skill.nome)] AS missing_skills,
             [skill IN vaga_skills WHERE any(cs IN candidate_skills WHERE cs.nome = skill.nome AND cs.nivel < skill.nivel_minimo)] AS below_level_skills
        
        RETURN {
            missing_skills: missing_skills,
            below_level_skills: below_level_skills,
            total_required: size(vaga_skills),
            candidate_skills: candidate_skills
        } AS result
        """
        
        parametros = {
            'candidate_id': candidate_id,
            'vaga_id': vaga_id,
        }
        
        try:
            logger.info(
                f"Extracting skill gaps: candidate={candidate_id[:8]}, vaga={vaga_id[:8]}"
            )
            
            with self.driver.session(database="neo4j") as session:
                result = session.run(query, parametros)
                records = [record.data() for record in result]
            
            if not records:
                # No data found - return empty gaps
                logger.warning(
                    f"No skill data found for candidate={candidate_id[:8]}, vaga={vaga_id[:8]}"
                )
                return {
                    'gaps': [],
                    'has_gaps': False,
                    'total_required': 0,
                    'total_matched': 0,
                }
            
            # Parse Neo4j response
            result_data = records[0].get('result', {})
            
            # Build gaps list combining missing and below-level skills
            gaps = []
            
            # Missing skills (candidate doesn't have them at all)
            for skill in result_data.get('missing_skills', []):
                gaps.append({
                    'nome': skill['nome'],
                    'nivel_minimo': skill.get('nivel_minimo', 2),
                    'nivel_candidato': 0,
                    'gap': skill.get('nivel_minimo', 2),  # Full gap
                })
            
            # Below-level skills (candidate has them but below required level)
            for skill in result_data.get('below_level_skills', []):
                # Find candidate's level for this skill
                candidate_level = 0
                for cs in result_data.get('candidate_skills', []):
                    if cs['nome'] == skill['nome']:
                        candidate_level = cs.get('nivel', 0)
                        break
                
                gaps.append({
                    'nome': skill['nome'],
                    'nivel_minimo': skill.get('nivel_minimo', 2),
                    'nivel_candidato': candidate_level,
                    'gap': skill.get('nivel_minimo', 2) - candidate_level,
                })
            
            total_required = result_data.get('total_required', 0)
            total_matched = total_required - len(gaps)
            
            return {
                'gaps': gaps,
                'has_gaps': len(gaps) > 0,
                'total_required': total_required,
                'total_matched': max(0, total_matched),
            }
            
        except Exception as e:
            logger.exception(
                f"Error extracting skill gaps: candidate={candidate_id[:8]}, vaga={vaga_id[:8]}"
            )
            raise
    
    def get_vaga_required_skills(self, vaga_id: str) -> List[Dict]:
        """
        Get required skills for a job position from Neo4j.
        
        Args:
            vaga_id (str): UUID of job position
        
        Returns:
            List of skill dictionaries with nome and nivel_minimo
        """
        query = """
        MATCH (v:Vaga {uuid: $vaga_id})
        OPTIONAL MATCH (v)-[requer:REQUER]->(h:Habilidade)
        RETURN {
            nome: h.nome,
            nivel_minimo: coalesce(requer.nivel_minimo, 2)
        } AS skill
        """
        
        try:
            with self.driver.session(database="neo4j") as session:
                result = session.run(query, {'vaga_id': vaga_id})
                return [record['skill'] for record in result if record['skill']]
        except Exception as e:
            logger.exception(f"Error fetching required skills for vaga={vaga_id[:8]}")
            raise
    
    def get_candidate_skills(self, candidate_id: str) -> List[Dict]:
        """
        Get current skills for a candidate from Neo4j.
        
        Args:
            candidate_id (str): UUID of candidate
        
        Returns:
            List of skill dictionaries with nome, nivel, and metadata
        """
        query = """
        MATCH (c:Candidato {uuid: $candidate_id})
        OPTIONAL MATCH (c)-[tem:TEM_HABILIDADE]->(h:Habilidade)
        RETURN {
            nome: h.nome,
            nivel: coalesce(tem.nivel, 0),
            anos_experiencia: tem.anos_experiencia,
            ano_ultima_utilizacao: tem.ano_ultima_utilizacao
        } AS skill
        """
        
        try:
            with self.driver.session(database="neo4j") as session:
                result = session.run(query, {'candidate_id': candidate_id})
                return [record['skill'] for record in result if record['skill']]
        except Exception as e:
            logger.exception(f"Error fetching candidate skills for candidate={candidate_id[:8]}")
            raise
