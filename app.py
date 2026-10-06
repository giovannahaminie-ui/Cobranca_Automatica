from flask import Flask, jsonify, request
import config
from db import oracle_client, sqlite_client
from services import senior_nf_service, senior_boleto_service, chatwoot_service
from datetime import datetime
from email.utils import parsedate_to_datetime
import os
import re
import base64
import hmac, hashlib


app = Flask(__name__)
sqlite_client.init_db()


ORACLE_CLIENT_LIB_DIR = r"C:\Users\administrador\Downloads\instantclient-basic-windows.x64-23.26.3.0.0\instantclient_23_26"

#BOLETOS
BOLETOS_DIR = os.path.join(os.path.dirname(__file__), "boletos")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")

def _log_falha(id_titulo, etapa, erro):
    os.makedirs(LOGS_DIR, exist_ok=True)
    linha = f"{datetime.now().isoformat()} | titulo={id_titulo} | etapa={etapa} | erro={erro}\n"
    nome_arquivo = f"falhas_{datetime.now().strftime('%Y-%m')}.log"
    with open(os.path.join(LOGS_DIR, nome_arquivo), "a", encoding="utf-8") as f:
        f.write(linha)

def _fmt_valor(v):
    try:
        return f"{float(v):.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return v

def _fmt_data(d):
    if not d:
        return ""
    for parser in (parsedate_to_datetime, datetime.fromisoformat):
        try:
            return parser(d).strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            continue
    return str(d)

def _assinatura_valida(req):
    secret = os.getenv("CHATWOOT_WEBHOOK_SECRET")
    if not secret:
        return True
    ts = req.headers.get("X-ChatWoot-Timestamp", "")
    assinatura = req.headers.get("X-ChatWoot-Signature")
    if not assinatura:
        return False
    corpo = req.get_data(as_text=True)
    esperado = "sha256=" + hmac.new(
    secret.encode(), f"{ts}.{corpo}".encode(), hashlib.sha256
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
    etapa = request.args.get("etapa", 1, type=int)
    titulos = oracle_client.buscar_titulos_vencidos(dias_janela=dias)

    pendentes = []
    vistos = set()
    for t in titulos:
        chave = (t["codemp"], t["codfil"], t["id_titulo"])
        if chave in vistos:
            continue
        vistos.add(chave)

        t["etapa"] = etapa
        if not sqlite_client.ja_enviado(t["id_titulo"], etapa):
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
    etapa = body.get("etapa")
    try:
        pdf_boleto = senior_boleto_service.baixar_pdf_boleto(
            numero_titulo=id_titulo,
            codemp=body["codemp"],
            codfil=body["codfil"],
            codtpt=body["codtpt"],
        )

        pdf_nf_base64 = None
        chave_acesso = body.get("chave_acesso")
        if chave_acesso:
            pdf_nf = senior_nf_service.baixar_pdf_nf(chave_acesso)
            import base64
            pdf_nf_base64 = base64.b64encode(pdf_nf).decode()
    except Exception as e:
        sqlite_client.marcar_falha(id_titulo, e, etapa)
        _log_falha(id_titulo, etapa, e)
        return jsonify({"erro": str(e)}), 502
    import base64
    return jsonify({
        "pdf_nf_base64": pdf_nf_base64,
        "pdf_boleto_base64": base64.b64encode(pdf_boleto).decode(),
    })


@app.post("/enviar-cobranca/<id_titulo>")
def enviar_cobranca(id_titulo):
    """Envia a cobranca via API do Chatwoot. Escolhe o template pela etapa."""
    import base64
    body = request.get_json(force=True)
    etapa = int(body.get("etapa", 1))
    try:
        if sqlite_client.ja_enviado(id_titulo, etapa):
            return jsonify({"status": "ja_enviado", "etapa": etapa})
        pdf_boleto_bytes = base64.b64decode(body["pdf_boleto_base64"])
        nome_arquivo_boleto = "Boleto-" + re.sub(r"[^A-Za-z0-9._-]", "_", id_titulo) + ".pdf"
        _salvar_copia_boleto(nome_arquivo_boleto, pdf_boleto_bytes)

        vencimento = _fmt_data(body.get("vencimento"))
        valor_nf = _fmt_valor(body.get("valor"))

        if sqlite_client.ja_enviado(id_titulo, etapa):
            return jsonify({"status": "ja_enviado", "etapa": etapa})

        if etapa == 2:
            template_name = config.TEMPLATE_ETAPA_2
            parametros_body = {
                "1": body.get("nome_colaborador") or config.NOME_COLABORADOR,
                "2": id_titulo,
                "3": vencimento,
                "4": valor_nf,
            }
        else:
            template_name = config.TEMPLATE_ETAPA_1
            parametros_body = {
                "nome_cliente": body["cliente_nome"],
                "valor_nf": valor_nf,
                "vencimento": vencimento,
            }

        contact_id = chatwoot_service.buscar_ou_criar_contato(
            telefone=body["telefone"], nome=body["cliente_nome"]
        )
        conversation_id = chatwoot_service.obter_ou_criar_conversa(contact_id)
        url_boleto = chatwoot_service.hospedar_pdf(
            conversation_id, pdf_boleto_bytes, nome_arquivo_boleto
        )
        chatwoot_service.enviar_template_cobranca(
            conversation_id=conversation_id,
            template_name=template_name,
            idioma=body.get("idioma", "pt_BR"),
            parametros_body=parametros_body,
            url_boleto=url_boleto,
            nome_arquivo_boleto=nome_arquivo_boleto,
            com_documento=(etapa != 2),
            conteudo=f"Cobrança título {id_titulo} - {body['cliente_nome']} - Emp {body.get('codemp')}/Fil {body.get('codfil')} (cobrança {etapa})",
        )
        sqlite_client.marcar_enviado(id_titulo, etapa, conversation_id)
        try:
            chatwoot_service.marcar_label(conversation_id)
        except Exception as e:
            _log_falha(id_titulo, etapa, f"enviado, mas a etiqueta nao foi aplicada: {e}")
        return jsonify({"status": "enviado", "etapa": etapa, "conversation_id": conversation_id})
    except Exception as e:
        sqlite_client.marcar_falha(id_titulo, e, etapa)
        _log_falha(id_titulo, etapa, e)
        return jsonify({"erro": str(e)}), 502


@app.post("/webhook/chatwoot")
def webhook_chatwoot():
    """
    Recebe o webhook do Chatwoot (Settings > Integrations > Webhooks, eventos
    message_created e message_updated):
    - message_created (incoming): marca no SQLite quando o cliente responde.
    - message_updated (outgoing com falha): marca o titulo como nao_entregue.
    """
    if not _assinatura_valida(request):
        print("webhook recusado, cabecalhos:", {k: v for k, v in request.headers.items() if "chatwoot" in k.lower()})
        return jsonify({"erro": "assinatura inválida"}), 401
    payload = request.get_json(force=True)


    if (payload.get("event") == "message_updated"
            and payload.get("message_type") == "outgoing"
            and not payload.get("private")):
        erro = (payload.get("content_attributes") or {}).get("external_error")
        if payload.get("status") == "failed" or erro:
            conversation_id = (payload.get("conversation") or {}).get("id")
            if conversation_id:
                sqlite_client.marcar_nao_entregue(conversation_id, erro or "status failed")
                _log_falha(f"conversa {conversation_id}", "entrega", erro or "status failed")

    elif payload.get("message_type") == "incoming":
        conversation_id = payload.get("conversation", {}).get("id")
        if conversation_id:
            sqlite_client.marcar_respondido(conversation_id)

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5057, debug=False)
