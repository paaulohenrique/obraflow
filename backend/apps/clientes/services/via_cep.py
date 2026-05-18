"""ViaCEP integration placeholder.

Replace this module when the ViaCEP HTTP call is implemented.
"""
from typing import TypedDict


class CepData(TypedDict):
    cep: str
    rua: str
    bairro: str
    cidade: str
    estado: str


def get_address_by_cep(cep: str) -> CepData | None:
    """Fetch address data from ViaCEP API.

    Returns None when the CEP is not found or the service is unavailable.
    """
    # TODO: implement HTTP call to https://viacep.com.br/ws/{cep}/json/
    raise NotImplementedError("ViaCEP integration not yet implemented.")
