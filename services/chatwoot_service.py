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

HEADERS = {
    "api_access_token": config.CHATWOOT_API_TOKEN,
    "Content-Type": "application/json",
}

BASE = f"{config.CHATWOOT_BASE_URL}/api/v1/accounts/{config.CHATWOOT_ACCOUNT_ID}"


def buscar_ou_criar_contato(telefone: str, nome: str) -> int:
    resp = requests.get(
        f"{BASE}/contacts/search",
        headers=HEADERS,
        params={"q": telefone},
        timeout=30,
    )
    resp.raise_for_status()
    resultados = resp.json().get("payload", [])
    if resultados:
        return resultados[0]["id"]

    resp = requests.post(
        f"{BASE}/contacts",
        headers=HEADERS,
        json={"name": nome, "phone_number": telefone, "inbox_id": config.CHATWOOT_INBOX_ID},
        timeout=30,
    )
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


def enviar_template_cobranca(conversation_id: int, template_name: str, idioma: str,
                              parametros_body: dict, pdf_boleto_bytes: bytes,
                              nome_arquivo_boleto: str):
    files = [
        ("attachments[]", (nome_arquivo_boleto, pdf_boleto_bytes, "application/pdf")),
    ]
    data = {
        "message_type": "outgoing",
        "private": "false",
        "template_params[name]": template_name,
        "template_params[category]": "UTILITY",
        "template_params[language]": idioma,
    }
    for chave, valor in parametros_body.items():
        data[f"template_params[processed_params][body][{chave}]"] = valor

    resp = requests.post(
        f"{BASE}/conversations/{conversation_id}/messages",
        headers={"api_access_token": config.CHATWOOT_API_TOKEN},
        data=data,
        files=files,
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
