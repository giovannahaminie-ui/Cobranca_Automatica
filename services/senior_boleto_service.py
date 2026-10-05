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
                       codcrt=None, codpor=None, codsnf=None, modelo=None) -> bytes:
    client = _get_client()

    entrada = f'<ECodEmp={codemp}><ECodFil={codfil}><ECodTpt={codtpt}><ENumTit="{numero_titulo}">'

    resultado = client.service.Executar(
        user=config.SENIOR_USER,
        password=config.SENIOR_PASSWORD,
        encryption=config.SENIOR_ENCRYPTION,
        parameters={
            "prRelatorio": config.RELATORIO_BOLETO,
            "prEntrada": entrada,
            "prExecFmt": "tefFile",
            "prSaveFormat": "tsfPDF",
            "prEntranceIsXML": "F",
        },
    )

    erro = (getattr(resultado, "erroExecucao", None) or "").strip()
    if erro:
        raise RuntimeError(f"Falha ao gerar boleto do titulo {numero_titulo}: {erro}")

    pdf = base64.b64decode(resultado.prRetorno or "")
    if not pdf.startswith(b"%PDF"):
        raise RuntimeError(
            f"O relatorio do titulo {numero_titulo} nao retornou um PDF valido "
            "(relatorio cancelado ou vazio)"
        )
    return pdf