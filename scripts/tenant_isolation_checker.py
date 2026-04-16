#!/usr/bin/env python
"""
HRTech - Tenant Isolation Security Checker
============================================

Script para fazer auditoria de segurança de tenant isolation em produção.
Detecta patterns que indicam possíveis vulnerabilidades IDOR.

Uso:
    python manage.py shell < tenant_isolation_checker.py
"""

import logging
from django.db.models import Q
from core.models import (
    Organization, User, Profile, Candidato, HistoricoAcao,
    Comentario, Favorito, AuditoriaMatch, Vaga
)

logger = logging.getLogger(__name__)


class TenantIsolationChecker:
    """Auditor de segurança para tenant isolation."""

    def __init__(self):
        self.findings = {
            'CRITICAL': [],
            'MAJOR': [],
            'MINOR': []
        }

    def check_all(self):
        """Executa todos os checks."""
        print("\n" + "="*80)
        print("TENANT ISOLATION SECURITY CHECKER")
        print("="*80 + "\n")

        self.check_historico_acoes_orphaned()
        self.check_candidatos_orphaned()
        self.check_comentarios_orphaned()
        self.check_favoritos_orphaned()
        self.check_users_without_org()
        self.check_cross_tenant_references()
        self.check_candidatos_duplicate_emails()

        self.print_report()

    def check_historico_acoes_orphaned(self):
        """Verifica HistoricoAcao sem organization."""
        orphaned = HistoricoAcao.objects.filter(organization__isnull=True)
        if orphaned.exists():
            self.findings['CRITICAL'].append(
                f"🔴 CRITICAL: {orphaned.count()} HistoricoAcao records without organization"
            )
            logger.critical(f"Found {orphaned.count()} HistoricoAcao orphaned records")

    def check_candidatos_orphaned(self):
        """Verifica Candidato sem organization (esperado apenas para públicos)."""
        orphaned = Candidato.objects.filter(
            organization__isnull=True
        ).exclude(user__isnull=False)  # Apenas candidatos sem user vinculado (públicos)

        if orphaned.count() > 100:  # Aviso se há muitos
            self.findings['MAJOR'].append(
                f"⚠️  MAJOR: {orphaned.count()} public Candidato records (sem organização)"
            )

    def check_comentarios_orphaned(self):
        """Verifica Comentario sem organização."""
        orphaned = Comentario.objects.filter(
            candidato__organization__isnull=True
        )
        if orphaned.exists():
            self.findings['CRITICAL'].append(
                f"🔴 CRITICAL: {orphaned.count()} Comentario records with orphaned candidates"
            )

    def check_favoritos_orphaned(self):
        """Verifica Favorito apontando para candidato de outra organização."""
        # Isso seria possível se houver múltiplas orgs com mesmo candidato
        cross_org = 0
        for favorito in Favorito.objects.select_related('usuario', 'candidato'):
            user_org = getattr(favorito.usuario.profile, 'organization', None)
            cand_org = favorito.candidato.organization
            if user_org and cand_org and user_org != cand_org:
                cross_org += 1

        if cross_org > 0:
            self.findings['CRITICAL'].append(
                f"🔴 CRITICAL: {cross_org} Favorito records pointing to cross-tenant candidates"
            )

    def check_users_without_org(self):
        """Verifica Users sem organização (deveria ser apenas superadmin)."""
        users_without_org = User.objects.filter(
            profile__organization__isnull=True
        ).exclude(is_superuser=True)

        if users_without_org.exists():
            self.findings['MAJOR'].append(
                f"⚠️  MAJOR: {users_without_org.count()} non-superuser users without organization"
            )

    def check_cross_tenant_references(self):
        """Verifica referências cross-tenant perigosas."""
        # Vaga referenciada em AuditoriaMatch de candidato de outra org
        cross_refs = 0
        for match in AuditoriaMatch.objects.select_related('candidato', 'vaga').filter(
            candidato__organization__isnull=False,
            vaga__organization__isnull=False
        ):
            if match.candidato.organization != match.vaga.organization:
                cross_refs += 1
                logger.warning(
                    f"Cross-tenant match: candidato_org={match.candidato.organization.id}, "
                    f"vaga_org={match.vaga.organization.id}"
                )

        if cross_refs > 0:
            self.findings['CRITICAL'].append(
                f"🔴 CRITICAL: {cross_refs} cross-tenant AuditoriaMatch records found"
            )

    def check_candidatos_duplicate_emails(self):
        """Verifica candidatos com mesmo email em organizações diferentes."""
        # Query para encontrar emails duplicados com organization diferente
        emails_by_org = {}
        for candidato in Candidato.objects.filter(organization__isnull=False):
            if candidato.email not in emails_by_org:
                emails_by_org[candidato.email] = []
            emails_by_org[candidato.email].append(candidato.organization_id)

        duplicates = {
            email: orgs for email, orgs in emails_by_org.items()
            if len(set(orgs)) > 1
        }

        if duplicates:
            self.findings['MAJOR'].append(
                f"⚠️  MAJOR: {len(duplicates)} emails duplicated across organizations (possible enumeration vector)"
            )

    def print_report(self):
        """Imprime relatório."""
        print("\n" + "="*80)
        print("FINDINGS REPORT")
        print("="*80 + "\n")

        total = sum(len(v) for v in self.findings.values())
        if total == 0:
            print("✅ PASS - No tenant isolation vulnerabilities detected!\n")
            return

        for severity, findings in self.findings.items():
            if findings:
                print(f"\n{severity} ({len(findings)}):")
                for finding in findings:
                    print(f"  {finding}")

        print(f"\n{'='*80}")
        print(f"TOTAL FINDINGS: {total}")
        print("="*80 + "\n")

        if self.findings['CRITICAL']:
            print("🚫 CRITICAL - Deploy blocked until fixed!")
            return False

        return True


if __name__ == '__main__':
    checker = TenantIsolationChecker()
    checker.check_all()
