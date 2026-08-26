"""
Integracao com o webservice IDownloadServico (eDocs) para baixar o PDF
da nota fiscal ja emitida.

Doc: https://documentacao.senior.com.br/webservices/edocs/_site/api/
     Senior.SapiensNfe.DataAccess.Dados.Documento.IDownloadServico.html

O metodo BaixarPdf retorna uma lista de PdfRetorno, cada um com:
    Conteudo               -> PDF em base64
    TipoDocumentoAuxiliar  -> 1 = documento principal (a NF em si)
                               2 = boleto/GNRE quando o proprio eDocs devolve o boleto junto
"""
import base64
from zeep import Client
import config

TIPO_DOCUMENTO_PRINCIPAL = 1


def _get_client():
    return Client(config.EDOCS_WSDL)


def baixar_pdf_nf(chave_acesso: str) -> bytes:
    """
    chave_acesso: chave de 44 digitos da NF-e/NFS-e.
    Retorna os bytes do PDF do documento principal.
    """
    client = _get_client()

    resultado = client.service.BaixarPdf(
        usuario=config.SENIOR_USER,
        senha=config.SENIOR_PASSWORD,
        chave=chave_acesso,
    )

    if not resultado.Sucesso:
        raise RuntimeError(f"Falha ao baixar PDF da NF {chave_acesso}: retorno sem sucesso")

    for pdf in resultado.Pdfs.PdfRetorno:
        if pdf.TipoDocumentoAuxiliar == TIPO_DOCUMENTO_PRINCIPAL:
            return base64.b64decode(pdf.Conteudo)

    raise RuntimeError(f"PDF principal nao encontrado no retorno para a NF {chave_acesso}")
