def gerar_texto_explicativo(
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
