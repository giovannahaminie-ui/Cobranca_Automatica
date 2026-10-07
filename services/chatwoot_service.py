"""
Integracao com a API do Chatwoot: busca/cria contato, cria conversa e
envia a mensagem de template (com anexos) para o cliente.

Docs:
- https://developers.chatwoot.com/api-reference/messages/create-new-message
- https://developers.chatwoot.com/api-reference/contacts

Nota: relatos da comunidade indicam que o campo `source_id` causa erro ao
criar conversa com template mesmo a doc oficial marcando como obrigatorio.
Se o POST /conversations falhar, o primeiro teste e remover esse campo.
"""
import requests
import config
import re

HEADERS = {
    "api_access_token": config.CHATWOOT_API_TOKEN,
    "Content-Type": "application/json",
}

BASE = f"{config.CHATWOOT_BASE_URL}/api/v1/accounts/{config.CHATWOOT_ACCOUNT_ID}"

def _normalizar_telefone(telefone: str) -> str:
    """Converte o telefone do sapiens"""
    digitos = re.sub(r"\D", "", telefone or "").lstrip("0")
    if digitos.startswith("55") and len(digitos) >= 12:
        return "+" + digitos
    return "+55" + digitos

def _e_fixo(tel: str) -> bool:
    local = _normalizar_telefone(tel)[5:]
    return len(local) == 8 and local[0] in "2345"

def telefone_valido_whatsapp(telefone) -> bool:
    """Tamanho valido (celular ou fixo). Fixo so funciona se tiver WhatsApp Business."""
    if not telefone:
        return False
    return len(_normalizar_telefone(telefone)) in (13, 14)


def escolher_telefone(*telefones):
    """Prefere celular (foncli, foncl2...); se nao houver, aceita fixo; None se nenhum serve."""
    validos = [t for t in telefones if telefone_valido_whatsapp(t)]
    for t in validos:
        if not _e_fixo(t):
            return t
    return validos[0] if validos else None

def _chave_telefone(tel: str) -> str:
    """DDD + ultimos 8 digitos (ignora o +55 e o 9o digito)."""
    d = re.sub(r"\D", "", tel or "")
    if d.startswith("55") and len(d) >= 12:
        d = d[2:]
    return d[:2] + d[-8:]


def _buscar_contato_por_telefone(telefone: str):
    resp = requests.get(
        f"{BASE}/contacts/search",
        headers=HEADERS,
        params={"q": telefone[-8:]},
        timeout=30,
    )
    resp.raise_for_status()
    chave = _chave_telefone(telefone)
    for contato in resp.json().get("payload", []):
        if _chave_telefone(contato.get("phone_number")) == chave:
            return contato["id"]
    return None


def buscar_ou_criar_contato(telefone: str, nome: str) -> int:
    telefone = _normalizar_telefone(telefone)
    if len(telefone) not in (13, 14):   # +55 + DDD + 8 ou 9 digitos
        raise ValueError(f"Telefone invalido para cobranca: {telefone!r}")

    contato_id = _buscar_contato_por_telefone(telefone)
    if contato_id:
        return contato_id

    resp = requests.post(
        f"{BASE}/contacts",
        headers=HEADERS,
        json={"name": nome, "phone_number": telefone, "inbox_id": config.CHATWOOT_INBOX_ID},
        timeout=30,
    )
    if resp.status_code >= 400:
        # ja existe (formato diferente) ou foi criado agora: tenta achar de novo
        contato_id = _buscar_contato_por_telefone(telefone)
        if contato_id:
            return contato_id
    resp.raise_for_status()
    return resp.json()["payload"]["contact"]["id"]


def criar_conversa(contact_id: int) -> int:
    resp = requests.post(
        f"{BASE}/conversations",
        headers=HEADERS,
        json={
            "inbox_id": config.CHATWOOT_INBOX_ID,
            "contact_id": contact_id,
            "status": "open",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]

def obter_ou_criar_conversa(contact_id: int) -> int:
    """Reaproveita a conversa mais recente do contato nesta caixa de entrada."""
    resp = requests.get(
        f"{BASE}/contacts/{contact_id}/conversations",
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    da_caixa = [
        c for c in resp.json().get("payload", [])
        if str(c.get("inbox_id")) == str(config.CHATWOOT_INBOX_ID)
    ]
    if not da_caixa:
        return criar_conversa(contact_id)

    conversa = max(da_caixa, key=lambda c: c["id"])
    if conversa.get("status") == "resolved":
        r = requests.post(
            f"{BASE}/conversations/{conversa['id']}/toggle_status",
            headers=HEADERS,
            json={"status": "open"},
            timeout=30,
        )
        r.raise_for_status()
    return conversa["id"]

def hospedar_pdf(conversation_id: int, pdf_bytes: bytes, nome_arquivo: str) -> str:
    """Sobe o PDF como NOTA PRIVADA na conversa, nao vai para o cliente e sim o chatwoot 
        apenas guarda o arquivo e devolve em uma URL pública.
    """
    resp = requests.post(
        f"{BASE}/conversations/{conversation_id}/messages", headers={"api_access_token": config.CHATWOOT_API_TOKEN},
        data={
            "content": f"Boleto {nome_arquivo} (arquivo interno da automacao)", 
            "message_type": "outgoing", 
            "private": "true",
        },
        files=[("attachments[]", (nome_arquivo, pdf_bytes, "application/pdf"))],
        timeout=60,
        )
    resp.raise_for_status()
    anexos = resp.json().get("attachments", [])
    if not anexos or not anexos[0].get("data_url"):
        raise RuntimeError("Chatwoot não devolveu data_url do boleto")
    return anexos[0]["data_url"].replace("/blobs/redirect/", "/blobs/proxy/")

def enviar_template_cobranca(conversation_id: int, template_name: str, idioma: str,
                              parametros_body: dict, url_boleto: str, nome_arquivo_boleto: str,
                              com_documento: bool = True, conteudo: str = ""):
    data = {
        "content": conteudo,
        "message_type": "outgoing",
        "private": "false",
        "template_params[name]": template_name,
        "template_params[category]": "UTILITY",
        "template_params[language]": idioma,
    }
    if com_documento:
        data["template_params[processed_params][header][media_url]"] = url_boleto
        data["template_params[processed_params][header][media_type]"] = "document"
        data["template_params[processed_params][header][media_name]"] = nome_arquivo_boleto
    for chave, valor in parametros_body.items():
        data[f"template_params[processed_params][body][{chave}]"] = valor

    resp = requests.post(
        f"{BASE}/conversations/{conversation_id}/messages",
        headers={"api_access_token": config.CHATWOOT_API_TOKEN},
        data=data,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()

def marcar_label(conversation_id: int, label: str = "cobranca-enviada"):
    resp = requests.post(
        f"{BASE}/conversations/{conversation_id}/labels",
        headers=HEADERS,
        json={"labels": [label]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()

def agente_da_cobranca(codemp, codfil):
    """RTL (emp 2, fil 1 e 2) -> Pollyane; todo o resto -> Sabrina."""
    if int(codemp) == 2 and int(codfil) in (1, 2):
        return config.CHATWOOT_AGENTE_RTL
    return config.CHATWOOT_AGENTE_PADRAO


def atribuir_conversa(conversation_id: int, agente_id: int):
    resp = requests.post(
        f"{BASE}/conversations/{conversation_id}/assignments",
        headers=HEADERS,
        json={"assignee_id": agente_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()

