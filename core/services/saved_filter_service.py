"""
HRTech - Serviço de Filtros Salvos
==================================

Centraliza regras de negócio para salvar, listar, carregar e remover filtros do RH.
"""

import json
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404
from django.urls import reverse

from core.models import FiltroSalvo


class SavedFilterService:
    MAX_FILTER_NAME_LENGTH = 100

    @staticmethod
    def _build_parametros(parametros_json, current_get_params):
        if parametros_json:
            try:
                parametros = json.loads(parametros_json)
            except json.JSONDecodeError as exc:
                raise ValueError('Parâmetros inválidos') from exc

            if not isinstance(parametros, dict):
                raise ValueError('Parâmetros inválidos')

            return parametros

        if not current_get_params:
            return {}
        return {k: v for k, v in current_get_params.items() if k != 'page'}

    @classmethod
    def save_filter(cls, user, nome_filtro, parametros_json, current_get_params):
        nome_filtro = (nome_filtro or '').strip()

        if not nome_filtro:
            raise ValueError('Nome do filtro é obrigatório')

        if len(nome_filtro) > cls.MAX_FILTER_NAME_LENGTH:
            raise ValueError(
                f'Nome muito longo (máximo {cls.MAX_FILTER_NAME_LENGTH} caracteres)'
            )

        parametros = cls._build_parametros(parametros_json, current_get_params)

        filtro, created = FiltroSalvo.objects.update_or_create(
            usuario=user,
            nome=nome_filtro,
            defaults={
                'parametros': parametros,
            },
        )

        return filtro, created

    @staticmethod
    def list_filters(user):
        return list(
            FiltroSalvo.objects.filter(usuario=user).values(
                'id', 'nome', 'criado_em', 'vezes_usado', 'parametros'
            )
        )

    @staticmethod
    def build_redirect_url(user, filtro_id):
        filtro = get_object_or_404(FiltroSalvo, id=filtro_id, usuario=user)

        parametros = filtro.parametros
        query_string = urlencode(parametros, doseq=True)

        redirect_url = reverse('core:buscar_candidatos')
        if query_string:
            redirect_url += f'?{query_string}'

        return redirect_url

    @staticmethod
    def delete_filter(user, filtro_id):
        filtro = get_object_or_404(FiltroSalvo, id=filtro_id, usuario=user)
        nome = filtro.nome
        filtro.delete()
        return nome