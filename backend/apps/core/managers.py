from django.db import models


class ActiveManager(models.Manager):
    """Excludes soft-deleted records (deleted_at is not null).

    Apply to concrete models that should hide soft-deleted rows by default:

        class MyModel(BaseModel):
            objects = ActiveManager()
            all_objects = AllObjectsManager()

    Note: BaseModel intentionally does NOT apply this manager so that each
    concrete model can opt in explicitly, avoiding unexpected behaviour when
    admin, migrations, or third-party code uses the default manager.
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    """Returns all records including soft-deleted ones.

    Pair with ActiveManager when a model needs both a filtered default
    manager and an escape hatch for admin / recovery queries:

        class MyModel(BaseModel):
            objects = ActiveManager()          # default: no soft-deleted
            all_objects = AllObjectsManager()  # bypass when needed
    """

    def get_queryset(self):
        return super().get_queryset()
