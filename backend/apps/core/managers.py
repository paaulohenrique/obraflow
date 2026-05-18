from django.db import models


class ActiveManager(models.Manager):
    """Default manager — excludes soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    """Bypass soft-delete filter when needed."""

    def get_queryset(self):
        return super().get_queryset()
