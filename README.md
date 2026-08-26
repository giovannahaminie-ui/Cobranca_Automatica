# Cobrança Automática

Automação de cobrança: busca títulos vencidos no ERP Sapiens (Oracle), gera o PDF da NF e do boleto, envia pro cliente via WhatsApp utilizando número cadastrado na META e a plataforma (Chatwoot) detecta quando o cliente responde para os responsáveis darem continuidade no atendimento.

## Arquitetura

1. **Python/Flask** (este repositório) — expõe endpoints HTTP simples pra abstrair Oracle + webservices SOAP do Sapiens, pra que o n8n não precise lidar com SQL/SOAP diretamente.
2. **n8n** (Docker) — orquestra o fluxo: gatilho agendado → busca títulos vencidos → gera PDFs → envia cobrança → trata resposta do cliente.
3. **Chatwoot** (self-hosted via Docker) — canal de WhatsApp (API oficial do Meta), envia a mensagem com template aprovado e recebe respostas do cliente.
4. **SQLite local** (`cobranca.db`) — controla quais títulos já foram cobrados, evitando reenvio duplicado.

## Setup

### 1. Dependências
```bash
pip install -r requirements.txt
2. Oracle Instant Client (modo thick)
Necessário porque o Sapiens usa um password verifier antigo (0x939) não suportado pelo modo thin do python-oracledb.

Baixa o Instant Client Basic (Windows x64) da Oracle.
Aponta o caminho no .env (ORACLE_CLIENT_LIB_DIR) — não precisa mexer no PATH do Windows.
3. .env
Não é versionado no Git (contém credenciais) — precisa ser recriado manualmente em cada máquina/servidor novo. Variáveis necessárias:

# Oracle (Sapiens)
ORACLE_USER=
ORACLE_PASSWORD=
ORACLE_DSN=
ORACLE_CLIENT_LIB_DIR=

# Sapiens SOAP (edocs / relatorio) - mesmo usuario/senha do Sapiens
SENIOR_USER=
SENIOR_PASSWORD=
SENIOR_ENCRYPTION=0

# Chatwoot
CHATWOOT_BASE_URL=
CHATWOOT_ACCOUNT_ID=
CHATWOOT_API_TOKEN=
CHATWOOT_INBOX_ID=

# SQLite
SQLITE_PATH=./cobranca.db

# Janela de vencimento (dias) usada na query de titulos vencidos
DIAS_JANELA=30
4. Rodar
python app.py
Endpoints
Rota	Método	Descrição
/titulos-vencidos	GET	Lista títulos vencidos ainda não cobrados (usado pelo gatilho agendado do n8n)
/gerar-pdfs/<id_titulo>	POST	Gera o PDF do boleto (e da NF, se chave_acesso for enviada)
/enviar-cobranca/<id_titulo>	POST	Envia a cobrança (NF + boleto) pro cliente via Chatwoot/WhatsApp
/webhook/chatwoot	POST	Recebe eventos do Chatwoot (configurar como message_created), marca resposta do cliente no SQLite
Query dos títulos vencidos
sql/query_titulos_vencidos.sql — busca em sapiens.E301TCR (títulos), com joins pra E085CLI (cliente), E440NFC/E140NFV (nota fiscal) e E039POR (portador, de onde vem modblo — o modelo de bloqueto específico de cada portador).

⚠️ Antes de automatizar via gatilho agendado, o WHERE dessa query precisa ser genérico (sem codcli/numtit fixos de teste), senão só retorna sempre o mesmo título de teste.

Lições aprendidas (não repetir)
modelo do bloqueto varia por portador — não pode ser um valor fixo no .env. Vem da query (modblo), passado por título até o services/senior_boleto_service.py. Portadores sem modelo cadastrado retornam erro 422 tratado (boleto automático indisponível pra esses casos).
No node do n8n, o campo de URL (/gerar-pdfs/{{ $json.id_titulo }}) precisa estar em modo Expression — senão o n8n manda o texto literal {{ $json.id_titulo }} em vez do valor real, e o Sapiens quebra com "Access violation" tentando processar um título inválido.
Flask com debug=True não recarrega o .env sozinho — só recarrega arquivos .py (reloader). Depois de editar o .env, é preciso parar e rodar python app.py de novo.
Chatwoot Cloud (plano gratuito) não libera token de API — por isso migramos pra self-hosted via Docker.
Docker no Windows precisa WSL2 "moderno" (não a versão "de fábrica" do Windows) — em Windows Server/VM sem Microsoft Store, instala o .msi direto da página de releases do WSL no GitHub (github.com/microsoft/WSL/releases).
Rodando em VM, o Docker Desktop também exige "virtualização aninhada" habilitada no hypervisor (host) — não é algo que se resolve de dentro do Windows convidado. No VMware/vSphere: Edit Settings → VM Options → CPU Options → "Expose hardware assisted virtualization to the guest OS" (VM precisa estar desligada).
Evitar múltiplas cópias do projeto (ex: uma pasta local + uma de rede) — causa bugs difíceis de rastrear quando cada uma tem uma versão diferente do código/.env. Manter uma única fonte de verdade via Git.