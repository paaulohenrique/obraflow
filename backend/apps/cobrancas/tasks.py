import logging

from config.celery import app

logger = logging.getLogger("apps.cobrancas")


@app.task(
    name="apps.cobrancas.tasks.executar_automacoes_cobranca",
    ignore_result=True,
    time_limit=600,
    soft_time_limit=540,
)
def executar_automacoes_cobranca() -> None:
    from apps.cobrancas.models import ConfiguracaoCobranca
    from apps.cobrancas.services import executar_automacoes_cobranca as executar_empresa

    configuracoes = (
        ConfiguracaoCobranca.objects.filter(
            ativo=True,
            company__deleted_at__isnull=True,
            company__is_active=True,
            deleted_at__isnull=True,
        )
        .select_related("company")
        .order_by("company_id")
    )

    for configuracao in configuracoes:
        resultado = executar_empresa(company=configuracao.company)
        logger.info(
            "Automação de cobrança company=%s notificacoes=%s falhas=%s",
            configuracao.company_id,
            resultado.quantidade,
            len(resultado.falhas),
        )
