"""Tests for Organization multi-tenant model and business properties."""

from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from core.models import Candidato, Organization, Tag
from core.tests.tenant_helpers import create_test_organization


class OrganizationModelTests(TestCase):
    def test_neo4j_tenant_prefix_matches_str(self):
        org = create_test_organization()
        self.assertEqual(org.neo4j_tenant_prefix, str(org.id))

    def test_trial_ativo_false_when_not_trial_plan(self):
        org = create_test_organization(plano=Organization.Plano.STARTER)
        self.assertFalse(org.trial_ativo)

    def test_trial_ativo_true_when_trial_and_future_expiry(self):
        org = create_test_organization(
            plano=Organization.Plano.TRIAL,
            trial_expira_em=timezone.now() + timedelta(days=1),
        )
        self.assertTrue(org.trial_ativo)

    def test_trial_ativo_false_when_trial_expired(self):
        org = create_test_organization(
            plano=Organization.Plano.TRIAL,
            trial_expira_em=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(org.trial_ativo)

    def test_esta_ativo_false_when_inactive(self):
        org = create_test_organization(ativo=False, plano=Organization.Plano.STARTER)
        self.assertFalse(org.esta_ativo)

    def test_esta_ativo_false_when_trial_expired(self):
        org = create_test_organization(
            ativo=True,
            plano=Organization.Plano.TRIAL,
            trial_expira_em=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(org.esta_ativo)

    def test_esta_ativo_true_when_paid_plan(self):
        org = create_test_organization(plano=Organization.Plano.PRO)
        self.assertTrue(org.esta_ativo)


class TagUniqueTogetherTests(TestCase):
    def test_same_nome_allowed_across_organizations(self):
        org_a = create_test_organization(nome='Org A')
        org_b = create_test_organization(nome='Org B')
        Tag.objects.create(nome='Urgente', organization=org_a)
        Tag.objects.create(nome='Urgente', organization=org_b)
        self.assertEqual(Tag.objects.filter(nome='Urgente').count(), 2)

    def test_duplicate_nome_same_organization_raises(self):
        org = create_test_organization()
        Tag.objects.create(nome='Urgente', organization=org)
        with self.assertRaises(IntegrityError):
            Tag.objects.create(nome='Urgente', organization=org)


class CandidatoEmailUniquenessTests(TestCase):
    """Email is unique per organization, not globally."""

    def test_same_email_allowed_in_different_organizations(self):
        org_a = create_test_organization(nome='Org A')
        org_b = create_test_organization(nome='Org B')
        Candidato.objects.create(
            nome='A',
            email='dup@example.com',
            organization=org_a,
        )
        Candidato.objects.create(
            nome='B',
            email='dup@example.com',
            organization=org_b,
        )
        self.assertEqual(
            Candidato.objects.filter(email='dup@example.com').count(),
            2,
        )

    def test_duplicate_email_same_organization_raises(self):
        org = create_test_organization()
        Candidato.objects.create(
            nome='Primeiro',
            email='once@example.com',
            organization=org,
        )
        with self.assertRaises(IntegrityError):
            Candidato.objects.create(
                nome='Segundo',
                email='once@example.com',
                organization=org,
            )
