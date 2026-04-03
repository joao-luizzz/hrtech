"""
HRTech - Serviço de Engajamento RH
==================================

Centraliza operações de comentários e favoritos em candidatos.

SECURITY: Todas as operações validam organization para tenant isolation.
"""

from django.shortcuts import get_object_or_404
from django.db.models import Q

from core.models import Candidato, Vaga, Comentario, Favorito


class EngagementService:
    MAX_COMMENT_LENGTH = 4000

    @staticmethod
    def create_comment(candidato_id, autor, texto, tipo='nota', vaga_id=None, privado=False, organization=None):
        """
        Cria comentário em um candidato.
        
        SECURITY: Se organization for passado, valida que candidato pertence à org.
        """
        if not texto:
            raise ValueError('Texto é obrigatório')
        if len(texto) > EngagementService.MAX_COMMENT_LENGTH:
            raise ValueError(
                f'Texto muito longo. Máximo: {EngagementService.MAX_COMMENT_LENGTH} caracteres.'
            )

        valid_types = {choice[0] for choice in Comentario.Tipo.choices}
        if tipo not in valid_types:
            raise ValueError('Tipo de comentário inválido')

        # SECURITY: Filtrar por organization se fornecido
        if organization:
            candidato = get_object_or_404(Candidato, pk=candidato_id, organization=organization)
        else:
            candidato = get_object_or_404(Candidato, pk=candidato_id)

        vaga = None
        if vaga_id:
            # SECURITY: Vaga também deve pertencer à mesma organization
            if organization:
                vaga = Vaga.objects.filter(pk=vaga_id, organization=organization).first()
            else:
                vaga = Vaga.objects.filter(pk=vaga_id).first()

        comentario = Comentario.objects.create(
            candidato=candidato,
            autor=autor,
            tipo=tipo,
            texto=texto,
            vaga=vaga,
            privado=privado,
        )
        return comentario

    @staticmethod
    def list_comments_context(candidato_id, user, organization=None):
        """
        Lista comentários de um candidato.
        
        SECURITY: Se organization for passado, valida que candidato pertence à org.
        """
        # SECURITY: Filtrar por organization se fornecido
        if organization:
            candidato = get_object_or_404(Candidato, pk=candidato_id, organization=organization)
        else:
            candidato = get_object_or_404(Candidato, pk=candidato_id)

        comentarios = Comentario.objects.filter(candidato=candidato)
        comentarios = comentarios.filter(
            Q(privado=False) | Q(autor=user)
        ).select_related('autor', 'vaga').order_by('-created_at')

        # SECURITY: Filtrar vagas por organization
        if organization:
            vagas = Vaga.objects.filter(organization=organization, status=Vaga.Status.ABERTA).order_by('titulo')
        else:
            vagas = Vaga.objects.filter(status=Vaga.Status.ABERTA).order_by('titulo')

        return {
            'candidato': candidato,
            'comentarios': comentarios,
            'vagas': vagas,
        }

    @staticmethod
    def delete_comment(comentario_id, user, organization=None):
        """
        Deleta comentário.
        
        SECURITY: Valida que comentário pertence a candidato da organization.
        """
        comentario = get_object_or_404(Comentario, pk=comentario_id)
        
        # SECURITY: Verificar organization do candidato
        if organization and comentario.candidato.organization != organization:
            return False
        
        if comentario.autor != user and not user.is_superuser:
            return False

        comentario.delete()
        return True

    @staticmethod
    def toggle_favorite(candidato_id, user, vaga_id=None, organization=None):
        """
        Toggle favorito em candidato.
        
        SECURITY: Se organization for passado, valida que candidato pertence à org.
        """
        # SECURITY: Filtrar por organization se fornecido
        if organization:
            candidato = get_object_or_404(Candidato, pk=candidato_id, organization=organization)
        else:
            candidato = get_object_or_404(Candidato, pk=candidato_id)

        vaga = None
        if vaga_id:
            # SECURITY: Vaga também deve pertencer à mesma organization
            if organization:
                vaga = Vaga.objects.filter(pk=vaga_id, organization=organization).first()
            else:
                vaga = Vaga.objects.filter(pk=vaga_id).first()

        favorito, created = Favorito.objects.get_or_create(
            usuario=user,
            candidato=candidato,
            vaga=vaga,
        )

        if not created:
            favorito.delete()
            return False

        return True

    @staticmethod
    def list_user_favorites(user, organization=None):
        """
        Lista favoritos do usuário.
        
        SECURITY: Se organization for passado, filtra por candidatos da org.
        """
        queryset = Favorito.objects.filter(usuario=user)
        
        # SECURITY: Filtrar por organization
        if organization:
            queryset = queryset.filter(candidato__organization=organization)
        
        return queryset.select_related('candidato', 'vaga').order_by('-created_at')