import logging

from config.celery import app

logger = logging.getLogger("apps.notificacoes")


@app.task(
    bind=True,
    name="apps.notificacoes.tasks.enviar_notificacao_whatsapp",
    max_retries=3,
    default_retry_delay=60,
    ignore_result=True,
    time_limit=30,
    soft_time_limit=25,
)
def enviar_notificacao_whatsapp(self, notificacao_id: str) -> None:
    from apps.notificacoes.models import Notificacao
    from apps.notificacoes.services.providers import WhatsAppError, get_whatsapp_provider
    from apps.notificacoes.services.whatsapp import NotificacaoError, executar_envio

    try:
        notificacao = Notificacao.objects.select_related("canal", "template").get(
            pk=notificacao_id
        )
    except Notificacao.DoesNotExist:
        logger.error("Notificacao %s não encontrada.", notificacao_id)
        return

    if notificacao.ja_enviada:
        logger.info(
            "Notificacao %s já processada (status=%s), ignorando.",
            notificacao_id,
            notificacao.status,
        )
        return

    provider = get_whatsapp_provider()

    try:
        executar_envio(notificacao=notificacao, provider=provider)
    except NotificacaoError as exc:
        logger.warning(
            "NotificacaoError %s [%s]: %s",
            notificacao_id,
            exc.code,
            exc.message,
        )
    except WhatsAppError as exc:
        logger.error(
            "WhatsAppError %s [%s]: %s — tentativa %d/%d",
            notificacao_id,
            exc.code,
            exc.message,
            self.request.retries + 1,
            self.max_retries + 1,
        )
        try:
            raise self.retry(
                exc=exc,
                countdown=60 * (2 ** self.request.retries),
            )
        except self.MaxRetriesExceededError:
            logger.error(
                "Notificacao %s esgotou retries após %d tentativas.",
                notificacao_id,
                self.max_retries + 1,
            )


@app.task(
    name="apps.notificacoes.tasks.enfileirar_notificacao",
    ignore_result=True,
)
def enfileirar_notificacao(notificacao_id: str) -> None:
    """Enfileira envio assíncrono da notificação."""
    enviar_notificacao_whatsapp.apply_async(
        args=[notificacao_id],
        queue="notificacoes",
    )
