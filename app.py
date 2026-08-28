from flask import Flask, jsonify, request
import config
from db import oracle_client, sqlite_client
from services import senior_nf_service, senior_boleto_service, chatwoot_service
import os
import base64
import hmac, hashlib

app = Flask(__name__)
sqlite_client.init_db()


#BOLETOS
BOLETOS_DIR = os.path.join(os.path.dirname(__file__), "boletos")

def _assinatura_valida(req):
    secret = os.getenv("CHATWOOT_WEBHOOK_SECRET")
    if not secret:
        return True
    ts = req.headers.get("X-ChatWoot-Timestamp", "")
    assinatura = req.headers.get("X-ChatWoot-Signatue")
    corpo = req.get_data(as_text=True)
    esperado = "sha256=" + hmac.new(
        secret.encode(), f"{ts}.{corpo}".encode(), hashlib.sha3256
    ).hexdigest()
    return hmac.compare_digest(esperado, assinatura)

def _salvar_copia_boleto(nome_arquivo, conteudo):
    os.makedirs(BOLETOS_DIR, exist_ok=True)
    with open(os.path.join(BOLETOS_DIR, nome_arquivo), "wb") as f:
        f.write(conteudo)

@app.get("/titulos-vencidos")
def titulos_vencidos():
    """Lista os titulos vencidos ainda nao cobrados (usado pelo n8n no gatilho agendado)."""
    dias = request.args.get("dias_janela", config.DIAS_JANELA, type=int)
    titulos = oracle_client.buscar_titulos_vencidos(dias_janela=dias)

    pendentes = []
    for t in titulos:
        if not sqlite_client.ja_enviado(t["id_titulo"]):
            sqlite_client.registrar_titulo(t)
            pendentes.append(t)

    return jsonify(pendentes)

@app.post("/gerar-pdfs/<id_titulo>")
def gerar_pdfs(id_titulo):
    """
    Gera os PDFs da NF e do boleto para um titulo.
    Espera no corpo: chave_acesso (NF), codemp, codfil, codtpt.

    TODO: confirmar a assinatura exata de BaixarPdf no WSDL do ambiente
    (o parametro pode ser chave de acesso OU numero+serie+empresa+filial,
    depende da versao do eDocs). Ajustar senior_nf_service conforme o retorno real.
    """
    body = request.get_json(force=True)
    try:

        modelo =body.get("modblo")
        if not modelo:
            sqlite_client.marcar_falha(id_titulo, "Portador sem modelo de bloqueto cadastrado")
            return jsonify({"erro": "Portador sem modelo de bloqueto cadastrado, boleto automatico indisponível"}), 422

        pdf_boleto = senior_boleto_service.baixar_pdf_boleto(
            numero_titulo=id_titulo,
            codemp=body["codemp"],
            codfil=body["codfil"],
            codtpt=body["codtpt"],
            codcrt=body["codcrt"],
            codpor=body["codpor"],
            codsnf=body["codsnf"],
            modelo=modelo,
        )

        pdf_nf_base64 = None
        chave_acesso = body.get("chave_acesso")
        if chave_acesso:
            pdf_nf = senior_nf_service.baixar_pdf_nf(chave_acesso)
            import base64
            pdf_nf_base64 = base64.b64encode(pdf_nf).decode()
    except Exception as e:
        sqlite_client.marcar_falha(id_titulo, e)
        return jsonify({"erro": str(e)}), 502
    import base64
    return jsonify({
        "pdf_nf_base64": pdf_nf_base64,
        "pdf_boleto_base64": base64.b64encode(pdf_boleto).decode(),
    })


@app.post("/enviar-cobranca/<id_titulo>")
def enviar_cobranca(id_titulo):
    """
    Recebe os dados do cliente + PDFs (ja gerados) e envia a cobranca via API do
    Chatwoot, mantendo o disparo automatico e a resposta do cliente na mesma conversa.
    """
    import base64
    body = request.get_json(force=True)
    try:
        pdf_boleto_bytes = base64.b64decode(body["pdf_boleto_base64"])
        nome_arquivo_boleto = f"Boleto-{id_titulo}.pdf"
        _salvar_copia_boleto(nome_arquivo_boleto, pdf_boleto_bytes)

        contact_id = chatwoot_service.buscar_ou_criar_contato(
            telefone=body["telefone"], nome=body["cliente_nome"]
        )
        conversation_id = chatwoot_service.criar_conversa(contact_id)
        url_boleto = chatwoot_service.hospedar_pdf(
            conversation_id, pdf_boleto_bytes, nome_arquivo_boleto
        )
        chatwoot_service.enviar_template_cobranca(
            conversation_id=conversation_id,
            template_name=body["template_name"],
            idioma=body.get("idioma", "pt_BR"),
            parametros_body=body["parametros_body"],
            url_boleto=url_boleto,
            nome_arquivo_boleto=f"Boleto-{id_titulo}.pdf",
        )
        chatwoot_service.marcar_label(conversation_id)
        sqlite_client.marcar_enviado(id_titulo, conversation_id)
        return jsonify({"status": "enviado", "conversation_id": conversation_id})
    except Exception as e:
        sqlite_client.marcar_falha(id_titulo, e)
        return jsonify({"erro": str(e)}), 502


@app.post("/webhook/chatwoot")
def webhook_chatwoot():
    """
    Recebe o webhook do Chatwoot (Settings > Integrations > Webhooks, evento
    message_created) para marcar no SQLite quando o cliente responde.
    """
    if not _assinatura_valida(request):
        return jsonify({"erro": "assinatura inválida"}), 401
    payload = request.get_json(force=True)

    if payload.get("message_type") == "incoming":
        conversation_id = payload.get("conversation", {}).get("id")
        if conversation_id:
            sqlite_client.marcar_respondido(conversation_id)

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
