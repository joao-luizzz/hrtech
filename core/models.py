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
5. Profile com roles - separação de permissões RH vs Candidato
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """
    Perfil estendido do usuário com role e configurações.

    Roles:
    - candidato: Pode ver próprio perfil e matches
    - rh: Pode gerenciar vagas, ver todos candidatos, rodar matching
    - admin: Acesso total (superuser)
    """

    class Role(models.TextChoices):
        CANDIDATO = 'candidato', 'Candidato'
        RH = 'rh', 'Recrutador (RH)'
        ADMIN = 'admin', 'Administrador'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CANDIDATO
    )

    # Configurações pessoais
    receber_notificacoes = models.BooleanField(
        default=True,
        help_text="Receber notificações por email"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

    def __str__(self):
        return f"{self.user.email} ({self.get_role_display()})"

    @property
    def is_rh(self):
        return self.role in [self.Role.RH, self.Role.ADMIN]

    @property
    def is_candidato(self):
        return self.role == self.Role.CANDIDATO


# Signal para criar Profile automaticamente quando User é criado
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


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

    # Choices para etapa do processo seletivo (pipeline RH)
    class EtapaProcesso(models.TextChoices):
        TRIAGEM = 'triagem', 'Triagem'
        ENTREVISTA_RH = 'entrevista_rh', 'Entrevista RH'
        TESTE_TECNICO = 'teste_tecnico', 'Teste Técnico'
        ENTREVISTA_TECNICA = 'entrevista_tecnica', 'Entrevista Técnica'
        PROPOSTA = 'proposta', 'Proposta'
        CONTRATADO = 'contratado', 'Contratado'
        REJEITADO = 'rejeitado', 'Rejeitado'
        DESISTIU = 'desistiu', 'Desistiu'
    
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

    # Etapa do processo seletivo (pipeline RH) - separado do status_cv
    etapa_processo = models.CharField(
        max_length=20,
        choices=EtapaProcesso.choices,
        default=EtapaProcesso.TRIAGEM,
        help_text="Etapa atual no processo seletivo"
    )

    # Tags do candidato (relacionamento M2M)
    tags = models.ManyToManyField(
        'Tag',
        through='CandidatoTag',
        related_name='candidatos',
        blank=True
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


class HistoricoAcao(models.Model):
    """
    Log de ações realizadas por usuários do sistema.

    Registra:
    - Quem fez a ação
    - Qual ação foi feita
    - Em qual entidade (candidato, vaga)
    - Quando foi feita
    - Detalhes adicionais (JSON)

    LGPD: Este log é essencial para auditoria de acesso a dados pessoais.
    """

    class TipoAcao(models.TextChoices):
        # Ações em Candidatos
        CANDIDATO_CRIADO = 'candidato_criado', 'Candidato criado'
        CANDIDATO_EDITADO = 'candidato_editado', 'Candidato editado'
        CANDIDATO_DELETADO = 'candidato_deletado', 'Candidato deletado'
        CANDIDATO_CV_UPLOAD = 'cv_upload', 'CV enviado'
        CANDIDATO_CV_VISUALIZADO = 'cv_visualizado', 'CV visualizado'
        CANDIDATO_ETAPA_ALTERADA = 'etapa_alterada', 'Etapa alterada'
        # Ações em Vagas
        VAGA_CRIADA = 'vaga_criada', 'Vaga criada'
        VAGA_EDITADA = 'vaga_editada', 'Vaga editada'
        VAGA_DELETADA = 'vaga_deletada', 'Vaga deletada'
        VAGA_STATUS_ALTERADO = 'vaga_status', 'Status da vaga alterado'
        # Ações de Matching
        MATCHING_EXECUTADO = 'matching', 'Matching executado'
        # Ações de Autenticação
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='historico_acoes'
    )

    tipo_acao = models.CharField(
        max_length=30,
        choices=TipoAcao.choices
    )

    # Referências opcionais às entidades afetadas
    candidato = models.ForeignKey(
        Candidato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico'
    )

    vaga = models.ForeignKey(
        Vaga,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico'
    )

    # Detalhes adicionais (ex: de qual etapa para qual etapa)
    detalhes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detalhes da ação em JSON"
    )

    # IP do usuário (para auditoria de segurança)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico de Ação'
        verbose_name_plural = 'Histórico de Ações'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['usuario', 'created_at']),
            models.Index(fields=['tipo_acao', 'created_at']),
            models.Index(fields=['candidato', 'created_at']),
        ]

    def __str__(self):
        user_str = self.usuario.email if self.usuario else '[Sistema]'
        return f"{user_str} - {self.get_tipo_acao_display()} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"


def registrar_acao(usuario, tipo_acao, candidato=None, vaga=None, detalhes=None, ip_address=None):
    """
    Helper function para registrar ações no histórico.

    Uso:
        registrar_acao(
            usuario=request.user,
            tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_ETAPA_ALTERADA,
            candidato=candidato,
            detalhes={'de': 'triagem', 'para': 'entrevista_rh'},
            ip_address=get_client_ip(request)
        )
    """
    return HistoricoAcao.objects.create(
        usuario=usuario if usuario and usuario.is_authenticated else None,
        tipo_acao=tipo_acao,
        candidato=candidato,
        vaga=vaga,
        detalhes=detalhes or {},
        ip_address=ip_address
    )


class Comentario(models.Model):
    """
    Comentários/notas do RH sobre candidatos.

    Permite que recrutadores adicionem observações durante o processo seletivo.
    Útil para comunicação entre membros da equipe de RH.
    """

    class Tipo(models.TextChoices):
        NOTA = 'nota', 'Nota'
        FEEDBACK = 'feedback', 'Feedback de Entrevista'
        ALERTA = 'alerta', 'Alerta'
        POSITIVO = 'positivo', 'Ponto Positivo'
        NEGATIVO = 'negativo', 'Ponto de Atenção'

    candidato = models.ForeignKey(
        Candidato,
        on_delete=models.CASCADE,
        related_name='comentarios'
    )

    autor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='comentarios_feitos'
    )

    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        default=Tipo.NOTA
    )

    texto = models.TextField(
        help_text="Conteúdo do comentário"
    )

    # Opcional: vincular a uma vaga específica
    vaga = models.ForeignKey(
        Vaga,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comentarios'
    )

    # Privacidade: comentário visível apenas para o autor ou para todos do RH
    privado = models.BooleanField(
        default=False,
        help_text="Se marcado, apenas o autor pode ver"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
        ordering = ['-created_at']

    def __str__(self):
        autor_str = self.autor.email if self.autor else '[Deletado]'
        return f"{autor_str} sobre {self.candidato.nome}: {self.texto[:50]}..."


class Favorito(models.Model):
    """
    Candidatos favoritos por usuário e vaga.

    Permite que recrutadores marquem candidatos como favoritos
    para fácil acesso posterior.
    """

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favoritos'
    )

    candidato = models.ForeignKey(
        Candidato,
        on_delete=models.CASCADE,
        related_name='favoritado_por'
    )

    vaga = models.ForeignKey(
        Vaga,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='favoritos'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Favorito'
        verbose_name_plural = 'Favoritos'
        unique_together = ['usuario', 'candidato', 'vaga']

    def __str__(self):
        return f"{self.usuario.email} ⭐ {self.candidato.nome}"


class Tag(models.Model):
    """
    Tags customizáveis para organizar candidatos.

    Permite criar categorias flexíveis como:
    - "Entrevista Urgente", "Talento Top", "Indicação"
    - Por projeto, por cliente, por característica, etc.

    Tags podem ter cores para fácil identificação visual.
    """

    class Cor(models.TextChoices):
        AZUL = 'primary', 'Azul'
        VERDE = 'success', 'Verde'
        VERMELHO = 'danger', 'Vermelho'
        AMARELO = 'warning', 'Amarelo'
        ROXO = 'purple', 'Roxo'
        ROSA = 'pink', 'Rosa'
        LARANJA = 'orange', 'Laranja'
        CINZA = 'secondary', 'Cinza'
        CIANO = 'info', 'Ciano'
        ESCURO = 'dark', 'Escuro'

    nome = models.CharField(
        max_length=50,
        help_text="Nome da tag (ex: 'Talento Top', 'Urgente')"
    )

    cor = models.CharField(
        max_length=20,
        choices=Cor.choices,
        default=Cor.AZUL,
        help_text="Cor para exibição visual"
    )

    descricao = models.TextField(
        blank=True,
        help_text="Descrição opcional do que significa essa tag"
    )

    # Quem criou a tag (para permitir tags privadas no futuro)
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tags_criadas'
    )

    # Tags podem ser globais (todos veem) ou privadas (só criador)
    global_tag = models.BooleanField(
        default=True,
        help_text="Tag visível para toda equipe RH"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['nome']
        unique_together = ['nome', 'criado_por']

    def __str__(self):
        return f"🏷️ {self.nome}"


class CandidatoTag(models.Model):
    """
    Relacionamento M2M entre Candidato e Tag com metadados.

    Permite rastrear quem aplicou a tag e quando.
    """

    candidato = models.ForeignKey(
        Candidato,
        on_delete=models.CASCADE,
        related_name='candidato_tags'
    )

    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='candidato_tags'
    )

    aplicado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tags_aplicadas'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tag do Candidato'
        verbose_name_plural = 'Tags dos Candidatos'
        unique_together = ['candidato', 'tag']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.candidato.nome} → {self.tag.nome}"
