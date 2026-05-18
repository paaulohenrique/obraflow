import re


def clean_cnpj(value: str) -> str:
    return re.sub(r"\D", "", value)


def is_valid_cnpj(cnpj: str) -> bool:
    cnpj = clean_cnpj(cnpj)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False

    def _digit(cnpj, n):
        weights = list(range(n, 1, -1)) + list(range(9, 1, -1))
        s = sum(int(d) * w for d, w in zip(cnpj, weights))
        r = s % 11
        return "0" if r < 2 else str(11 - r)

    return cnpj[12] == _digit(cnpj[:12], 5) and cnpj[13] == _digit(cnpj[:13], 6)
