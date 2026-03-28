"""
HRTech - Services
=================

Serviços de integração externa:
- S3Service: Upload/download de CVs no AWS S3
- EmailService: Notificações por email
"""

from .s3_service import S3Service, get_s3_service
from .email_service import EmailService, get_email_service
from .cv_upload_service import CVUploadService
from .matching_service import MatchingService
from .pipeline_service import PipelineService
from .candidate_search_service import CandidateSearchService
from .export_service import ExportService
from .engagement_service import EngagementService
from .saved_filter_service import SavedFilterService
from .candidate_portal_service import CandidatePortalService

__all__ = [
	'S3Service',
	'get_s3_service',
	'EmailService',
	'get_email_service',
	'CVUploadService',
	'MatchingService',
	'PipelineService',
	'CandidateSearchService',
	'ExportService',
	'EngagementService',
	'SavedFilterService',
	'CandidatePortalService',
]
