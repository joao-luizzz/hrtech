"""Helpers for multi-tenant model tests."""

from core.models import Organization


def create_test_organization(nome='Test Organization', **kwargs):
    """Create an Organization for tests. Extra kwargs override defaults."""
    return Organization.objects.create(nome=nome, **kwargs)
