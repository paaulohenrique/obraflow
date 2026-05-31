from config.celery import app


@app.task(bind=True, name="apps.boletos.tasks.processar_boleto_ocr", ignore_result=True)
def processar_boleto_ocr(self, boleto_id: str):
    from .services.boleto import falhar_ocr_boleto, iniciar_processamento_ocr
    from .services.ocr import OCRError, get_ocr_provider

    boleto, processamento = iniciar_processamento_ocr(
        boleto_id=boleto_id,
        task_id=getattr(self.request, "id", "") or "",
    )
    provider = get_ocr_provider()
    try:
        result = provider.extract_text_from_file(boleto.arquivo.path)
    except OCRError as exc:
        falhar_ocr_boleto(
            boleto_id=boleto.pk,
            processamento_id=processamento.pk,
            erro_codigo=exc.code,
            erro_mensagem=exc.message,
        )
        return
    except Exception as exc:
        falhar_ocr_boleto(
            boleto_id=boleto.pk,
            processamento_id=processamento.pk,
            erro_codigo=type(exc).__name__,
            erro_mensagem=str(exc),
        )
        return

    from .services.boleto import concluir_ocr_boleto

    concluir_ocr_boleto(
        boleto_id=boleto.pk,
        processamento_id=processamento.pk,
        result=result,
    )
