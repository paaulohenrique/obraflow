import hashlib

from rest_framework.exceptions import ValidationError


MAX_XML_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_MIMES = {"text/xml", "application/xml", "text/plain"}
ALLOWED_EXTENSIONS = {".xml"}


def validate_xml_file(arquivo) -> dict:
    """Valida um arquivo XML de NF-e e retorna metadados básicos.

    Verifica: extensão, MIME, tamanho, conteúdo não-vazio.
    Calcula sha256. Não faz parsing — apenas validação estrutural do arquivo.
    """
    nome = (arquivo.name or "").lower()
    ext = "." + nome.rsplit(".", 1)[-1] if "." in nome else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError({"arquivo": f"Extensão '{ext}' não permitida. Envie um arquivo .xml."})

    content_type = (getattr(arquivo, "content_type", "") or "").split(";")[0].strip().lower()
    if content_type and content_type not in ALLOWED_MIMES:
        raise ValidationError({"arquivo": f"Tipo de arquivo '{content_type}' não é XML."})

    arquivo.seek(0, 2)
    tamanho = arquivo.tell()
    arquivo.seek(0)

    if tamanho == 0:
        raise ValidationError({"arquivo": "Arquivo vazio."})
    if tamanho > MAX_XML_SIZE:
        raise ValidationError({"arquivo": f"Arquivo excede o limite de {MAX_XML_SIZE // 1024 // 1024}MB."})

    conteudo = arquivo.read()
    arquivo.seek(0)

    sha256 = hashlib.sha256(conteudo).hexdigest()

    return {
        "sha256": sha256,
        "tamanho_bytes": tamanho,
        "conteudo": conteudo,
    }
