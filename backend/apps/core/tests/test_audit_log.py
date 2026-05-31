"""Tests for AuditLog immutability constraints (instance + queryset level)
and AuditLogAdmin read-only configuration.
"""
import pytest

from apps.core.admin import AuditLogAdmin
from apps.core.models import AuditLog


_ENTITY_ID = "00000000-0000-0000-0000-000000000001"


@pytest.mark.django_db
class TestAuditLogImmutability:
    def _make_log(self, admin_user):
        return AuditLog.objects.create(
            user=admin_user,
            action=AuditLog.ACTION_CREATE,
            entity_type="Test",
            entity_id=_ENTITY_ID,
        )

    # ── instance-level ────────────────────────────────────────────────────────

    def test_soft_delete_raises_runtime_error(self, admin_user):
        log = self._make_log(admin_user)
        with pytest.raises(RuntimeError, match="imutável"):
            log.soft_delete()

    def test_delete_raises_runtime_error(self, admin_user):
        log = self._make_log(admin_user)
        with pytest.raises(RuntimeError, match="imutável"):
            log.delete()

    # ── queryset-level ────────────────────────────────────────────────────────

    def test_queryset_filter_delete_raises_runtime_error(self, admin_user):
        log = self._make_log(admin_user)
        with pytest.raises(RuntimeError, match="imutável"):
            AuditLog.objects.filter(pk=log.pk).delete()

    def test_queryset_all_delete_raises_runtime_error(self, admin_user):
        self._make_log(admin_user)
        with pytest.raises(RuntimeError, match="imutável"):
            AuditLog.objects.all().delete()

    # ── creation and reads still work ────────────────────────────────────────

    def test_audit_log_is_created_normally(self, admin_user):
        log = self._make_log(admin_user)
        assert log.pk is not None
        assert AuditLog.objects.filter(pk=log.pk).exists()

    def test_audit_log_queryset_filter_works(self, admin_user):
        log = self._make_log(admin_user)
        result = AuditLog.objects.filter(entity_type="Test").first()
        assert result is not None
        assert result.pk == log.pk

    def test_audit_log_str(self, admin_user):
        log = self._make_log(admin_user)
        assert AuditLog.ACTION_CREATE in str(log)
        assert "Test" in str(log)

    def test_record_remains_after_blocked_delete(self, admin_user):
        log = self._make_log(admin_user)
        try:
            AuditLog.objects.filter(pk=log.pk).delete()
        except RuntimeError:
            pass
        assert AuditLog.objects.filter(pk=log.pk).exists()


# ── AuditLogAdmin read-only enforcement ───────────────────────────────────────

class TestAuditLogAdmin:
    """Verifies admin permissions without needing a running Django admin site."""

    def _admin(self):
        return AuditLogAdmin(AuditLog, None)

    def test_has_no_add_permission(self):
        assert self._admin().has_add_permission(request=None) is False

    def test_has_no_change_permission(self):
        assert self._admin().has_change_permission(request=None) is False

    def test_has_no_change_permission_with_obj(self):
        assert self._admin().has_change_permission(request=None, obj=object()) is False

    def test_has_no_delete_permission(self):
        assert self._admin().has_delete_permission(request=None) is False

    def test_has_no_delete_permission_with_obj(self):
        assert self._admin().has_delete_permission(request=None, obj=object()) is False
