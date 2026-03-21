"""
HRTech - Services
=================

Serviços de integração externa:
- S3Service: Upload/download de CVs no AWS S3
- EmailService: Notificações por email
"""

from .s3_service import S3Service, get_s3_service
from .email_service import EmailService, get_email_service

__all__ = ['S3Service', 'get_s3_service', 'EmailService', 'get_email_service']
