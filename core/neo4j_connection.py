"""
HRTech - Conexão Neo4j (Singleton)
==================================

Gerencia conexão com Neo4j AuraDB usando o driver oficial.

Decisões Arquiteturais:
1. Singleton pattern - evita overhead de reconexão a cada request
2. Driver oficial ao invés de neomodel - mais controle sobre Cypher
3. Context manager para garantir fechamento de sessões
4. Retry automático para resiliência

Uso:
    from core.neo4j_connection import get_neo4j_driver
    
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN n LIMIT 10")
"""

from django.conf import settings
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)

# Singleton do driver
_driver = None


class Neo4jConnection:
    """
    Conexão Neo4j com suporte a context manager.

    Uso recomendado:
        with Neo4jConnection() as conn:
            rows = conn.run_query("MATCH (n) RETURN n LIMIT 10")
    """

    def __init__(self, database: str = "neo4j"):
        self.database = database
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=60,
        )
        self.driver.verify_connectivity()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.driver is not None:
            self.driver.close()
            self.driver = None

    def run_query(self, query: str, parameters: dict = None):
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def run_write_query(self, query: str, parameters: dict = None):
        with self.driver.session(database=self.database) as session:
            return session.execute_write(
                lambda tx: tx.run(query, parameters or {}).consume()
            )


def get_neo4j_driver():
    """
    Retorna o driver Neo4j como singleton.
    
    Inicializa na primeira chamada e reutiliza nas subsequentes.
    Thread-safe por design do driver Neo4j.
    """
    global _driver
    
    if _driver is None:
        logger.info("Inicializando conexão Neo4j...")
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            # Configurações de pool de conexões
            max_connection_lifetime=3600,  # 1 hora
            max_connection_pool_size=50,
            connection_acquisition_timeout=60,
        )
        # Verifica conectividade
        _driver.verify_connectivity()
        logger.info("Conexão Neo4j estabelecida com sucesso")
    
    return _driver


def close_neo4j_driver():
    """
    Fecha o driver Neo4j.
    
    Chamar no shutdown da aplicação (signal ou atexit).
    """
    global _driver
    
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Conexão Neo4j fechada")


def run_query(query: str, parameters: dict = None, database: str = "neo4j"):
    """
    Executa uma query Cypher e retorna os resultados.
    
    Wrapper conveniente para queries simples.
    Para transações complexas, use o driver diretamente.
    
    Args:
        query: Query Cypher
        parameters: Parâmetros da query
        database: Nome do database (default: neo4j)
    
    Returns:
        Lista de records
    """
    driver = get_neo4j_driver()

    try:
        with driver.session(database=database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    except Exception:
        logger.exception(
            "Erro ao executar query Neo4j (database=%s, params=%s)",
            database,
            bool(parameters),
        )
        raise


def run_write_query(query: str, parameters: dict = None, database: str = "neo4j"):
    """
    Executa uma query de escrita (CREATE, MERGE, DELETE) em transação.
    
    Args:
        query: Query Cypher de escrita
        parameters: Parâmetros da query
        database: Nome do database
    
    Returns:
        ResultSummary com estatísticas da operação
    """
    driver = get_neo4j_driver()

    try:
        with driver.session(database=database) as session:
            result = session.execute_write(
                lambda tx: tx.run(query, parameters or {}).consume()
            )
            return result
    except Exception:
        logger.exception(
            "Erro ao executar write query Neo4j (database=%s, params=%s)",
            database,
            bool(parameters),
        )
        raise
