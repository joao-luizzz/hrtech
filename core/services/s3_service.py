"""
HRTech - Serviço de Storage S3
==============================

Gerencia upload e download de CVs no AWS S3.

Decisões de Segurança:
1. Bucket SEMPRE privado - nunca público
2. Acesso APENAS via presigned URLs com TTL curto (15 min)
3. CVs organizados por UUID do candidato
4. LGPD: deletar CV quando candidato é deletado

Uso:
    from core.services.s3_service import S3Service

    service = S3Service()

    # Upload
    s3_key = service.upload_cv(file, candidato_id)

    # Download (URL temporária)
    url = service.get_presigned_url(s3_key)

    # Delete
    service.delete_cv(s3_key)
"""

import logging
import uuid
import hashlib
import shutil
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class S3Service:
    """
    Serviço para gerenciar arquivos no AWS S3.

    Thread-safe: cada instância cria seu próprio client.
    """

    def __init__(self):
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.region = settings.AWS_S3_REGION_NAME
        self.presigned_ttl = settings.AWS_PRESIGNED_URL_TTL

        # Verifica se credenciais estão configuradas
        self.enabled = bool(
            settings.AWS_ACCESS_KEY_ID and
            settings.AWS_SECRET_ACCESS_KEY
        )

        if self.enabled:
            self.client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )
            self.s3 = self.client
        else:
            self.client = None
            self.s3 = None
            logger.warning("S3 não configurado - usando storage local")

    @staticmethod
    def _safe_cv_ref(s3_key: str) -> str:
        """Retorna referência não sensível para logs."""
        digest = hashlib.sha256((s3_key or '').encode('utf-8')).hexdigest()[:10]
        return f"cv_ref={digest}"

    def upload_cv(self, file, candidato_id: str) -> str:
        """
        Faz upload de um CV para o S3.

        Args:
            file: Arquivo Django (UploadedFile)
            candidato_id: UUID do candidato

        Returns:
            s3_key: Chave do arquivo no S3

        Raises:
            ClientError: Se upload falhar
        """
        # Gera nome único para o arquivo
        safe_filename = f"cv_{uuid.uuid4().hex[:8]}.pdf"
        s3_key = f"cvs/{candidato_id}/{safe_filename}"

        if not self.enabled:
            # Fallback para storage local
            return self._upload_local(file, candidato_id, safe_filename)

        try:
            # Upload com metadata
            self.client.upload_fileobj(
                file,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'application/pdf',
                    'Metadata': {
                        'candidato_id': candidato_id,
                    }
                }
            )

            logger.info("CV uploaded para S3 (%s)", self._safe_cv_ref(s3_key))
            return s3_key

        except ClientError as e:
            logger.error(f"Erro no upload S3: {e}")
            raise

    def _upload_local(self, file, candidato_id: str, filename: str) -> str:
        """
        Fallback: salva arquivo localmente quando S3 não está configurado.
        """
        cv_dir = Path(settings.MEDIA_ROOT) / 'cvs' / candidato_id
        cv_dir.mkdir(parents=True, exist_ok=True)

        cv_path = cv_dir / filename

        with open(cv_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        s3_key = f"cvs/{candidato_id}/{filename}"
        logger.info("CV salvo localmente (%s)", self._safe_cv_ref(s3_key))
        return s3_key

    def get_presigned_url(self, s3_key: str, expiration: int = None) -> str:
        """
        Gera URL temporária para download do CV.

        Args:
            s3_key: Chave do arquivo no S3
            expiration: Tempo de expiração em segundos (default: 15 min)

        Returns:
            URL temporária para download

        LGPD: URLs expiram automaticamente, sem acesso permanente ao CV.
        """
        if expiration is None:
            expiration = self.presigned_ttl

        if not self.enabled:
            # Fallback: retorna URL local
            return f"{settings.MEDIA_URL}{s3_key}"

        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url

        except ClientError as e:
            logger.error(f"Erro ao gerar presigned URL: {e}")
            raise

    def download_to_temp_file(self, s3_key: str, temp_path: str) -> str:
        """
        Baixa arquivo do S3 para um caminho temporário local.

        Args:
            s3_key: Chave do arquivo no S3
            temp_path: Caminho absoluto local de destino

        Returns:
            Caminho local onde o arquivo foi salvo
        """
        if not self.enabled:
            source_path = Path(settings.MEDIA_ROOT) / s3_key
            Path(temp_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, temp_path)
            logger.info("CV copiado do storage local para temp (%s)", self._safe_cv_ref(s3_key))
            return temp_path

        try:
            self.s3.download_file(self.bucket_name, s3_key, temp_path)
            logger.info("CV baixado do S3 para temp (%s)", self._safe_cv_ref(s3_key))
            return temp_path
        except ClientError as e:
            logger.error(f"Erro ao baixar CV do S3: {e}")
            raise

    def delete_cv(self, s3_key: str) -> bool:
        """
        Deleta um CV do S3.

        Args:
            s3_key: Chave do arquivo no S3

        Returns:
            True se deletado com sucesso

        LGPD: Usado para exercer direito ao esquecimento.
        """
        if not self.enabled:
            # Fallback: deleta arquivo local
            return self._delete_local(s3_key)

        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info("CV deletado do S3 (%s)", self._safe_cv_ref(s3_key))
            return True

        except ClientError as e:
            logger.error(f"Erro ao deletar CV do S3: {e}")
            return False

    def _delete_local(self, s3_key: str) -> bool:
        """
        Fallback: deleta arquivo local.
        """
        try:
            cv_path = Path(settings.MEDIA_ROOT) / s3_key
            if cv_path.exists():
                cv_path.unlink()
                logger.info("CV deletado localmente (%s)", self._safe_cv_ref(s3_key))
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar CV local: {e}")
            return False

    def cv_exists(self, s3_key: str) -> bool:
        """
        Verifica se um CV existe no S3.
        """
        if not self.enabled:
            cv_path = Path(settings.MEDIA_ROOT) / s3_key
            return cv_path.exists()

        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError:
            return False


# Singleton para uso global
_s3_service = None


def get_s3_service() -> S3Service:
    """
    Retorna instância singleton do S3Service.
    """
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service
