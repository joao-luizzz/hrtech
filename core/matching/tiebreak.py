from core.matching.types import ResultadoMatch

def ordenar_resultados(resultados: list[ResultadoMatch]) -> list[ResultadoMatch]:
    """
    Ordena resultados com critérios de desempate.

    Ordem:
    1. Score final (desc)
    2. Disponibilidade imediata (disponível primeiro)
    3. Menor gap de senioridade (não implementado aqui, já está no score)
    4. Data de cadastro mais recente (usaria o PG, simplificado aqui)
    """
    # Usando sort com chave múltipla
    # Tuple: (-score, não_disponível (False=0, True=1), nome)
    # Como queremos o maior score primeiro, usamos -score_final
    # Como queremos disponível primeiro, usamos not disponivel (disponivel=True vira 0, False vira 1)
    
    resultados.sort(
        key=lambda r: (
            -r.score_final,
            not r.candidato_disponivel,
            r.candidato_nome
        )
    )
    
    return resultados
