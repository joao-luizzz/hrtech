"""
HRTech - Serviço de Email
=========================

Gerencia envio de notificações por email.

Tipos de notificação:
1. CV processado com sucesso
2. Erro no processamento do CV
3. Mudança de etapa no processo seletivo
4. Nova vaga compatível com perfil

Configuração:
    DEBUG=True: emails vão para console
    DEBUG=False: usa SMTP configurado no settings.py
"""

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """
    Serviço para envio de emails transacionais.
    """

    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@hrtech.com')

    def send_email(self, to_email: str, subject: str, template: str, context: dict) -> bool:
        """
        Envia email usando template HTML.

        Args:
            to_email: Email do destinatário
            subject: Assunto do email
            template: Nome do template (sem extensão)
            context: Contexto para o template

        Returns:
            True se enviado com sucesso
        """
        try:
            # Renderiza HTML
            html_message = render_to_string(f'emails/{template}.html', context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=self.from_email,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False
            )

            logger.info(f"Email enviado para {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar email para {to_email}: {e}")
            return False

    def notify_cv_processed(self, candidato) -> bool:
        """
        Notifica candidato que CV foi processado com sucesso.
        """
        return self.send_email(
            to_email=candidato.email,
            subject='Seu curriculo foi processado - HRTech',
            template='cv_processado',
            context={
                'candidato': candidato,
                'dashboard_url': f"/candidato/{candidato.id}/",
            }
        )

    def notify_cv_error(self, candidato, error_message: str = None) -> bool:
        """
        Notifica candidato sobre erro no processamento.
        """
        return self.send_email(
            to_email=candidato.email,
            subject='Problema no processamento do seu curriculo - HRTech',
            template='cv_erro',
            context={
                'candidato': candidato,
                'error_message': error_message,
            }
        )

    def notify_etapa_changed(self, candidato, etapa_anterior: str, nova_etapa: str) -> bool:
        """
        Notifica candidato sobre mudança de etapa no processo.
        """
        etapas_display = dict(candidato.EtapaProcesso.choices)

        return self.send_email(
            to_email=candidato.email,
            subject='Atualizacao no seu processo seletivo - HRTech',
            template='etapa_alterada',
            context={
                'candidato': candidato,
                'etapa_anterior': etapas_display.get(etapa_anterior, etapa_anterior),
                'nova_etapa': etapas_display.get(nova_etapa, nova_etapa),
            }
        )


# Singleton
_email_service = None


def get_email_service() -> EmailService:
    """Retorna instância singleton do EmailService."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
