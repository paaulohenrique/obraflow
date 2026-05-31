import uuid
from django.db import models


class ImmutableQuerySet(models.QuerySet):
    """QuerySet that blocks bulk deletions — used by AuditLog."""

    def delete(self):
        raise RuntimeError("AuditLog é imutável e não pode ser removido.")


class ImmutableManager(models.Manager):
    def get_queryset(self):
        return ImmutableQuerySet(self.model, using=self._db)


class BaseModel(models.Model):
    """Abstract base for every ObraFlow entity.

    Provides UUID PK, audit timestamps and soft-delete.
    Multi-tenant isolation is enforced via a ForeignKey to Empresa on each
    concrete domain model — not as a loose UUID field here.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def soft_delete(self):
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active", "updated_at"])

    def restore(self):
        self.deleted_at = None
        self.is_active = True
        self.save(update_fields=["deleted_at", "is_active", "updated_at"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class AuditLog(BaseModel):
    """Records every mutating action for compliance and debugging.

    Immutability contract: AuditLog records must never be modified or deleted.
    soft_delete() and delete() raise RuntimeError to enforce this at the ORM
    level. The Django admin is configured read-only and without delete actions.
    """

    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_RESTORE = "RESTORE"
    ACTIONS = [
        (ACTION_CREATE, "Criação"),
        (ACTION_UPDATE, "Atualização"),
        (ACTION_DELETE, "Exclusão"),
        (ACTION_RESTORE, "Restauração"),
    ]

    objects = ImmutableManager()

    user = models.ForeignKey(
        "accounts.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=10, choices=ACTIONS)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=64, blank=True, default="")

    class Meta(BaseModel.Meta):
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type} {self.entity_id}"

    def soft_delete(self):
        raise RuntimeError("AuditLog é imutável e não pode ser removido.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("AuditLog é imutável e não pode ser removido.")
