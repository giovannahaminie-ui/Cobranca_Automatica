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

Como funciona na prática:

n8n está configurado disparando o fluxo de mensagens baseados nos dias de cobrança da etapa 1 e etapa 2:
- é realizado o select (sql) o fluxo separa e mantém apenas oque está de fato configurado conforme a agenda de envios de cobrança.
- é criado uma conversa no chatwoot com o tipo da etapa de cobrança.


- Arquivos:
- Sqlite = (banco de dados)
- n8n = automação
- chatwoot = chat aonde é enviada as mensagens
- número da Meta
- Foi criado um túnel para o serviço rodar no grok.
- Docker para hospedar o n8n e o chatwoot.