"""Registra o numero de WhatsApp na Cloud API da Meta (ativa o nome de exibicao aprovado).

Uso:  python registrar_numero.py

Le META_TOKEN do .env (ou pede no terminal) e mostra o status do nome de exibicao.
So registra se voce responder 's', e pede o PIN de 6 digitos.
O token da Meta NAO e o CHATWOOT_API_TOKEN: e o campo "Chave da API" da caixa de
WhatsApp no Chatwoot.
"""
import getpass
import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

GRAPH = "https://graph.facebook.com/v21.0"
WABA_ID = "1037261412607689"  # Retifica Tiete
PHONE_NUMBER_ID = "1242645462267726"  # +55 43 3377-0081


def chamar(metodo, url, token, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo)
    req.add_header("Authorization", f"Bearer {token}")
    if dados:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"erro_http": e.code, "resposta": json.loads(e.read() or b"{}")}


def main():
    token = (os.getenv("META_TOKEN") or "").strip()
    if not token:
        token = getpass.getpass("META_TOKEN nao esta no .env. Cole o token da Meta: ").strip()
    print(f"Token: {len(token)} caracteres, comeca com '{token[:3]}' (token da Meta costuma ter 150+ e comecar com 'EA')")
    waba = WABA_ID

    url = f"{GRAPH}/{waba}/phone_numbers?fields=id,display_phone_number,verified_name,name_status,new_display_name"
    numeros = chamar("GET", url, token)
    print("\nNumeros da conta:")
    print(json.dumps(numeros, indent=2, ensure_ascii=False))

    dados = numeros.get("data") or []
    if not dados:
        print("\nNenhum numero encontrado (verifique token e ID da WABA).")
        return

    phone_id = PHONE_NUMBER_ID
    if input(f"\nRegistrar o numero {phone_id}? (s/n): ").strip().lower() != "s":
        print("Cancelado.")
        return

    pin = getpass.getpass("PIN de 6 digitos (o existente, ou um novo): ").strip()
    resp = registrar(phone_id, token, pin)
    print("\nResposta:", json.dumps(resp, indent=2, ensure_ascii=False))

    # 133005 = o numero ja tem um PIN diferente: redefine e tenta de novo
    codigo = (resp.get("resposta") or {}).get("error", {}).get("code")
    if codigo == 133005:
        if input("\nPIN incorreto. Definir um PIN NOVO e registrar de novo? (s/n): ").strip().lower() != "s":
            return
        novo = getpass.getpass("PIN novo de 6 digitos (anote!): ").strip()
        r1 = chamar("POST", f"{GRAPH}/{phone_id}", token, {"pin": novo})
        print("\nDefinir PIN:", json.dumps(r1, indent=2, ensure_ascii=False))
        if r1.get("success"):
            r2 = registrar(phone_id, token, novo)
            print("\nRegistro:", json.dumps(r2, indent=2, ensure_ascii=False))


def registrar(phone_id, token, pin):
    return chamar("POST", f"{GRAPH}/{phone_id}/register", token,
                  {"messaging_product": "whatsapp", "pin": pin})


if __name__ == "__main__":
    main()
