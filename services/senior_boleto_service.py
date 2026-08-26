"""
Integracao com o webservice com.senior.g5.co.ger.relatorio, porta BloquetoFinanceiro,
para gerar o PDF do boleto de um titulo financeiro.

Doc: https://documentacao.senior.com.br/goup/5.10.3/webservices/com_senior_g5_co_ger_relatorio.htm

Campos obrigatorios para bloqueto do financeiro: numTit, codTpt, codEmp, codFil, codPor, codCrt.
formato = "PDF" retorna o blob em base64 no campo 'arquivo' (nao informar 'caminhoArq' nem 'impressora').
"""
import base64
from zeep import Client
import config


def _get_client():
    return Client(config.RELATORIO_WSDL)


def baixar_pdf_boleto(numero_titulo: str, codemp: int, codfil: int, codtpt: str,
                       codcrt: str, codpor: str, codsnf: str) -> bytes:
    client = _get_client()

    resultado = client.service.BloquetoFinanceiro(
        user=config.SENIOR_USER,
        password=config.SENIOR_PASSWORD,
        encryption=config.SENIOR_ENCRYPTION,
        parameters={
            "modelo": config.BOLETO_MODELO,
            "codTpt": codtpt,
            "numTit": numero_titulo,
            "codEmp": codemp,
            "codFil": codfil,
            "codPor": codpor,
            "codCrt": codcrt,
            "codSnf": codsnf,
            "formato": "PDF",
        },
    )

    if resultado.retorno != "OK":
        raise RuntimeError(f"Falha ao gerar boleto do titulo {numero_titulo}: {resultado.retorno}")

    return base64.b64decode(resultado.arquivo)