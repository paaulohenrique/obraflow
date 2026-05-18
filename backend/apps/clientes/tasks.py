import logging

from config.celery import app

logger = logging.getLogger("apps.clientes")


@app.task(bind=True, max_retries=3, default_retry_delay=60, queue="notificacoes")
def notificar_cliente_bloqueado(self, cliente_id: str):
    """Placeholder — send WhatsApp/email notification when a customer is blocked."""
    logger.info("Notificação de bloqueio pendente para cliente %s", cliente_id)


@app.task(bind=True, max_retries=3, default_retry_delay=300, queue="cobrancas")
def verificar_inadimplencia(self, company_id: str | None = None):
    """Placeholder — scheduled task to flag overdue customers."""
    logger.info("Verificação de inadimplência para empresa %s", company_id)


@app.task(bind=True, queue="relatorios")
def exportar_clientes_csv(self, company_id: str | None, user_id: str):
    """Placeholder — generates a CSV export of all customers."""
    logger.info("Exportação de clientes solicitada por %s", user_id)
