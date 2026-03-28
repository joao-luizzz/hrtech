"""
HRTech - Serviço de Engajamento RH
==================================

Centraliza operações de comentários e favoritos em candidatos.
"""

from django.shortcuts import get_object_or_404
from django.db.models import Q

from core.models import Candidato, Vaga, Comentario, Favorito


class EngagementService:
    MAX_COMMENT_LENGTH = 4000

    @staticmethod
    def create_comment(candidato_id, autor, texto, tipo='nota', vaga_id=None, privado=False):
        if not texto:
            raise ValueError('Texto é obrigatório')
        if len(texto) > EngagementService.MAX_COMMENT_LENGTH:
            raise ValueError(
                f'Texto muito longo. Máximo: {EngagementService.MAX_COMMENT_LENGTH} caracteres.'
            )

        valid_types = {choice[0] for choice in Comentario.Tipo.choices}
        if tipo not in valid_types:
            raise ValueError('Tipo de comentário inválido')

        candidato = get_object_or_404(Candidato, pk=candidato_id)

        vaga = None
        if vaga_id:
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
    def list_comments_context(candidato_id, user):
        candidato = get_object_or_404(Candidato, pk=candidato_id)

        comentarios = Comentario.objects.filter(candidato=candidato)
        comentarios = comentarios.filter(
            Q(privado=False) | Q(autor=user)
        ).select_related('autor', 'vaga').order_by('-created_at')

        vagas = Vaga.objects.filter(status=Vaga.Status.ABERTA).order_by('titulo')

        return {
            'candidato': candidato,
            'comentarios': comentarios,
            'vagas': vagas,
        }

    @staticmethod
    def delete_comment(comentario_id, user):
        comentario = get_object_or_404(Comentario, pk=comentario_id)
        if comentario.autor != user and not user.is_superuser:
            return False

        comentario.delete()
        return True

    @staticmethod
    def toggle_favorite(candidato_id, user, vaga_id=None):
        candidato = get_object_or_404(Candidato, pk=candidato_id)

        vaga = None
        if vaga_id:
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
    def list_user_favorites(user):
        return Favorito.objects.filter(
            usuario=user
        ).select_related('candidato', 'vaga').order_by('-created_at')