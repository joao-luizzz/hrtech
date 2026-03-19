"""
HRTech - Schemas Pydantic (Fase 3)
==================================

Validação estruturada das respostas da OpenAI.

CONTRATO ESTRITO - NÃO ADICIONAR MÉTODOS OU CAMPOS EXTRAS!

Arquitetura:
    - HabilidadeExtraida: representa uma skill extraída do CV
    - CVParseado: estrutura completa retornada pelo GPT-4o-mini
"""

from datetime import date
from typing import List
from pydantic import BaseModel, Field, field_validator


class HabilidadeExtraida(BaseModel):
    """
    Representa uma habilidade/skill extraída do currículo.

    CONTRATO ORIGINAL - NÃO MODIFICAR!
    """
    nome: str
    nivel: int = Field(..., ge=1, le=5)
    anos_experiencia: float = Field(..., ge=0)
    ano_ultima_utilizacao: int
    inferido: bool = Field(default=False)

    @field_validator('ano_ultima_utilizacao')
    @classmethod
    def validar_ano(cls, v: int) -> int:
        """Valida que o ano está em range razoável."""
        ano_atual = date.today().year
        if v > ano_atual or v < 1990:
            raise ValueError(f'Ano inválido: {v}')
        return v


class CVParseado(BaseModel):
    """
    Estrutura completa do currículo parseado pela OpenAI.

    CONTRATO ORIGINAL - NÃO MODIFICAR!
    """
    area_atuacao: str
    senioridade_inferida: str = Field(..., pattern=r'^(junior|pleno|senior)$')
    habilidades: List[HabilidadeExtraida]


# =============================================================================
# PROMPT PARA OPENAI
# =============================================================================

SCHEMA_INSTRUCOES = """
Você é um especialista em RH e análise de currículos técnicos.

Analise o currículo abaixo e extraia as informações no formato JSON especificado.

REGRAS IMPORTANTES:
1. area_atuacao: Identifique a área principal (Dados, Backend, Frontend, DevOps, Mobile, Fullstack)
2. senioridade_inferida: Baseie-se nos anos de experiência e complexidade dos projetos
   - junior: 0-2 anos ou projetos simples
   - pleno: 2-5 anos ou projetos de média complexidade
   - senior: 5+ anos ou projetos complexos/liderança
3. Para cada habilidade:
   - nome: Nome da tecnologia (ex: "Python", "React", "AWS")
   - nivel: 1 a 5 baseado na profundidade mencionada
   - anos_experiencia: Extraia ou estime baseado no período
   - ano_ultima_utilizacao: Use o ano do projeto mais recente; se não houver, use o ano atual
   - inferido: True se você INFERIU a informação (não estava explícita)

IMPORTANTE SOBRE ano_ultima_utilizacao:
- Se o CV mencionar "2020-2023" para um projeto com Python, ano_ultima_utilizacao = 2023
- Se não houver ano explícito, use o ano do projeto onde a skill aparece
- Se não houver projeto datado, use o ano atual e marque inferido=True

Retorne APENAS o JSON válido, sem markdown ou explicações.

Formato esperado:
{
    "area_atuacao": "string",
    "senioridade_inferida": "junior|pleno|senior",
    "habilidades": [
        {
            "nome": "string",
            "nivel": 1-5,
            "anos_experiencia": 0.0+,
            "ano_ultima_utilizacao": 1990-2026,
            "inferido": true|false
        }
    ]
}
"""
