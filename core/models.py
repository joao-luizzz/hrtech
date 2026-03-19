"""
HRTech - Models
===============

Arquitetura de Persistência Poliglota:
- Este arquivo define os models PostgreSQL (dados transacionais)
- Neo4j armazena o grafo de habilidades (ver core/neo4j_connection.py)
- UUID é a chave de sincronia entre os dois bancos

Decisões Arquiteturais Importantes:
1. UUID como PK em Candidato - mesmo valor usado no Neo4j
2. SET_NULL em AuditoriaMatch - preserva histórico mesmo após deleção (LGPD)
3. JSONField para skills - flexibilidade sem normalização excessiva
4. Status de CV como choices - facilita tracking do pipeline Celery
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Candidato(models.Model):
    """
    Representa um candidato no sistema.
    
    O UUID é compartilhado com Neo4j para manter sincronia entre bancos.
    Dados de habilidades ficam no grafo Neo4j, não aqui.
    
    Fluxo LGPD de deleção:
    1. Deletar do PostgreSQL (este model)
    2. Deletar nó correspondente no Neo4j
    3. Deletar CV do S3
    """
    
    # Choices para senioridade - usado tanto aqui quanto em Vaga
    class Senioridade(models.TextChoices):
        JUNIOR = 'junior', 'Júnior'
        PLENO = 'pleno', 'Pleno'
        SENIOR = 'senior', 'Sênior'
    
    # Choices para status do processamento de CV
    class StatusCV(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'           # Nenhum CV enviado
        RECEBIDO = 'recebido', 'Recebido'           # Upload feito, task na fila
        PROCESSANDO = 'processando', 'Lendo PDF'    # pdfplumber/Tesseract rodando
        EXTRAINDO = 'extraindo', 'Extraindo habilidades'  # GPT-4o-mini rodando
        CONCLUIDO = 'concluido', 'Concluído'        # Sucesso
        ERRO = 'erro', 'Erro no processamento'      # Falha
    
    # UUID como PK - mesmo valor será usado no Neo4j
    # Decisão: UUIDField ao invés de AutoField para facilitar dual-write
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID compartilhado com Neo4j"
    )
    
    # Vinculo com User do Django (opcional - candidato pode não ter conta)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='candidato'
    )
    
    # Dados básicos
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20, blank=True)
    
    # Perfil profissional
    senioridade = models.CharField(
        max_length=10,
        choices=Senioridade.choices,
        default=Senioridade.JUNIOR
    )
    anos_experiencia = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(50)],
        help_text="Anos totais de experiência profissional"
    )
    
    # Disponibilidade para início
    disponivel = models.BooleanField(
        default=True,
        help_text="Disponível para início imediato"
    )
    
    # Storage do CV no S3
    # Decisão: guardar apenas a key, não a URL completa
    # URLs são geradas via presigned URL com TTL de 15 min
    cv_s3_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="Key do arquivo no S3 (ex: cvs/uuid/arquivo.pdf)"
    )
    
    # Status do processamento do CV (para polling HTMX)
    status_cv = models.CharField(
        max_length=15,
        choices=StatusCV.choices,
        default=StatusCV.PENDENTE
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Candidato'
        verbose_name_plural = 'Candidatos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nome} ({self.senioridade})"


class Vaga(models.Model):
    """
    Representa uma vaga de emprego.
    
    Skills são armazenadas como JSONField para flexibilidade.
    O matching real acontece no Neo4j via relação REQUER.
    
    Estrutura esperada do JSONField:
    skills_obrigatorias = [
        {"nome": "Python", "nivel_minimo": 3},
        {"nome": "SQL", "nivel_minimo": 2}
    ]
    """
    
    class Senioridade(models.TextChoices):
        JUNIOR = 'junior', 'Júnior'
        PLENO = 'pleno', 'Pleno'
        SENIOR = 'senior', 'Sênior'
    
    class Status(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        ABERTA = 'aberta', 'Aberta'
        PAUSADA = 'pausada', 'Pausada'
        FECHADA = 'fechada', 'Fechada'
    
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    
    # Área de atuação - será nó no Neo4j
    area = models.CharField(
        max_length=100,
        help_text="Ex: Dados, Backend, Frontend, DevOps"
    )
    
    senioridade_desejada = models.CharField(
        max_length=10,
        choices=Senioridade.choices,
        default=Senioridade.PLENO
    )
    
    # Skills como JSON - estrutura flexível
    # Decisão: JSONField ao invés de M2M com through model
    # Razão: facilita importação de vagas de sistemas externos
    skills_obrigatorias = models.JSONField(
        default=list,
        help_text='[{"nome": "Python", "nivel_minimo": 3}]'
    )
    skills_desejaveis = models.JSONField(
        default=list,
        help_text='[{"nome": "Docker", "nivel_minimo": 1}]'
    )
    
    # Quem criou a vaga
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='vagas_criadas'
    )
    
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.RASCUNHO
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Vaga'
        verbose_name_plural = 'Vagas'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.titulo} ({self.area} - {self.senioridade_desejada})"


class AuditoriaMatch(models.Model):
    """
    Registro imutável de cada matching realizado.
    
    CRÍTICO PARA LGPD:
    - Usa SET_NULL nas FKs para preservar histórico mesmo após deleção
    - Snapshot completo das skills no momento do match
    - Versão do algoritmo para reprodutibilidade
    
    Decisão: on_delete=SET_NULL (NUNCA CASCADE)
    Razão: Se candidato exercer direito ao esquecimento, o registro
    de auditoria permanece (anonimizado) para compliance
    """
    
    # FKs com SET_NULL - preserva histórico
    vaga = models.ForeignKey(
        Vaga,
        on_delete=models.SET_NULL,
        null=True,
        related_name='auditorias'
    )
    candidato = models.ForeignKey(
        Candidato,
        on_delete=models.SET_NULL,
        null=True,
        related_name='auditorias'
    )
    
    # Score calculado (0-100)
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Snapshot imutável das skills no momento do match
    # Estrutura: {"candidato_skills": [...], "vaga_skills": [...], "matches": [...]}
    snapshot_skills = models.JSONField(
        help_text="Snapshot completo das skills no momento do cálculo"
    )
    
    # Versão do algoritmo para reprodutibilidade
    versao_algoritmo = models.CharField(
        max_length=20,
        default='1.0.0',
        help_text="Versão do algoritmo de matching usado"
    )
    
    # Detalhes do cálculo para transparência
    detalhes_calculo = models.JSONField(
        default=dict,
        help_text="Breakdown: camada1_score, camada2_score, camada3_score"
    )
    
    # Timestamp imutável
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Auditoria de Match'
        verbose_name_plural = 'Auditorias de Match'
        ordering = ['-created_at']
        # Index composto para queries frequentes
        indexes = [
            models.Index(fields=['vaga', 'score']),
            models.Index(fields=['candidato', 'created_at']),
        ]
    
    def __str__(self):
        vaga_str = self.vaga.titulo if self.vaga else '[Vaga deletada]'
        cand_str = self.candidato.nome if self.candidato else '[Candidato deletado]'
        return f"{cand_str} → {vaga_str}: {self.score}"
