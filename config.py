import os
from dotenv import load_dotenv

load_dotenv()

# Oracle (Sapiens)
ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
ORACLE_DSN = os.getenv("ORACLE_DSN")
ORACLE_CLIENT_LIB_DIR = os.getenv("ORACLE_CLIENT_LIB_DIR")

# Sapiens SOAP
SENIOR_USER = os.getenv("SENIOR_USER")
SENIOR_PASSWORD = os.getenv("SENIOR_PASSWORD")
SENIOR_ENCRYPTION = int(os.getenv("SENIOR_ENCRYPTION", "0"))

EDOCS_WSDL = "https://SEU_SERVIDOR/edocs/IDownloadServico.svc?wsdl"  # ajustar host real
RELATORIO_WSDL = "http://192.168.10.235:8000/g5-senior-services/sapiens_Synccom_senior_g5_co_ger_relatorio?wsdl"

# Chatwoot
CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL")
CHATWOOT_ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID")
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN")
CHATWOOT_INBOX_ID = os.getenv("CHATWOOT_INBOX_ID")

# SQLite
SQLITE_PATH = os.getenv("SQLITE_PATH", "./cobranca.db")

# Janela de vencimento (dias) usada na query de titulos vencidos
DIAS_JANELA = int(os.getenv("DIAS_JANELA", "30"))
