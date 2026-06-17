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
        vaga_skills: List[Dict]
    ) -> Dict:
        """
        Get skill gaps for a candidate relative to a job position.
        
        Calculates the gaps in Python by fetching the candidate's current skills
        from Neo4j and comparing them to the required skills passed in.
        
        Args:
            candidate_id (str): UUID of candidate from PostgreSQL
            vaga_skills (List[Dict]): Required skills for the job from PostgreSQL
        
        Returns:
            dict with structure:
            {
                'gaps': [...],
                'has_gaps': bool,
                'total_required': int,
                'total_matched': int,
            }
        """
        try:
            candidate_skills = self.get_candidate_skills(candidate_id)
            
            # Map candidate skills for quick lookup (normalized name -> level)
            cand_skills_map = {}
            for s in candidate_skills:
                if s.get('nome'):
                    cand_skills_map[s['nome'].strip().lower()] = s.get('nivel', 0)
                    
            gaps = []
            for req_skill in vaga_skills:
                req_name = req_skill.get('nome', '').strip()
                if not req_name:
                    continue
                
                req_level = req_skill.get('nivel_minimo', 2)
                req_name_lower = req_name.lower()
                
                if req_name_lower not in cand_skills_map:
                    # Skill is missing completely
                    gaps.append({
                        'nome': req_name,
                        'nivel_minimo': req_level,
                        'nivel_candidato': 0,
                        'gap': req_level,
                    })
                else:
                    cand_level = cand_skills_map[req_name_lower]
                    if cand_level < req_level:
                        # Candidate has the skill but below required level
                        gaps.append({
                            'nome': req_name,
                            'nivel_minimo': req_level,
                            'nivel_candidato': cand_level,
                            'gap': req_level - cand_level,
                        })
                        
            total_required = len(vaga_skills)
            total_matched = total_required - len(gaps)
            
            return {
                'gaps': gaps,
                'has_gaps': len(gaps) > 0,
                'total_required': total_required,
                'total_matched': max(0, total_matched),
            }
        except Exception as e:
            logger.exception(
                f"Error extracting skill gaps: candidate={candidate_id[:8]}"
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
