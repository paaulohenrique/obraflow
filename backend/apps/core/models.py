import uuid
from django.db import models


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
    """Records every mutating action for compliance and debugging."""

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

    class Meta(BaseModel.Meta):
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type} {self.entity_id}"
