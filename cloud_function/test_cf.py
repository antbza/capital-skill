import os
import json
import datetime
from unittest.mock import Mock
from openpyxl import Workbook

# Importa a Cloud Function e o parser
import main
from excel_parser import ExcelParser

def generate_test_xlsx(filepath):
    """
    Gera um arquivo de extrato XLSX fictício contendo transações relativas
    a "hoje" e "ontem" de forma dinâmica baseada na execução do teste.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Extrato"

    # Cabeçalho baseado no fornecido pelo usuário
    ws.append(["Data", "Lançamento", "Dcto.", "Crédito (R$)", "Débito (R$)", "Saldo (R$)"])

    # Obter datas relativas compatíveis com fuso horário UTC-3
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    brasilia_offset = datetime.timezone(datetime.timedelta(hours=-3))
    today = utc_now.astimezone(brasilia_offset).date()
    
    yesterday = today - datetime.timedelta(days=1)
    two_days_ago = today - datetime.timedelta(days=2)

    # 1. Saldo inicial há dois dias atrás
    ws.append([two_days_ago.strftime("%d/%m/%Y"), "SALDO ANTERIOR", "000000", 0.0, 0.0, 1000.00])
    
    # 2. Transação comum há dois dias atrás
    ws.append([two_days_ago.strftime("%d/%m/%Y"), "COMPRA SUPERMERCADO BARATO", "101010", 0.0, 150.00, 850.00])

    # 3. Transações de ontem
    ws.append([yesterday.strftime("%d/%m/%Y"), "PIX RECEBIDO - JOAO DA SILVA", "111222", 150.00, 0.0, 1000.00])
    ws.append([yesterday.strftime("%d/%m/%Y"), "PIX ENVIADO - PEDRO PEREIRA", "333444", 0.0, 50.00, 950.00])
    ws.append([yesterday.strftime("%d/%m/%Y"), "TARIFA MENSALIDADE", "999999", 0.0, 19.90, 930.10])

    # 4. Transações de hoje
    ws.append([today.strftime("%d/%m/%Y"), "PIX RECEBIDO - ANA LUIZA SOUZA", "555666", 300.00, 0.0, 1230.10])
    ws.append([today.strftime("%d/%m/%Y"), "COMPRA PADARIA PÃO QUENTE", "777888", 0.0, 15.00, 1215.10])

    wb.save(filepath)
    print(f"Planilha de teste local gerada com sucesso em: {filepath}")

def build_alexa_payload(intent_name, slots=None, session_attributes=None):
    """
    Constrói um payload JSON mockado de requisição de intenção da Alexa.
    """
    payload = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "SessionId.test",
            "application": {
                "applicationId": "amzn1.echo-sdk-ams.app.test"
            },
            "user": {
                "userId": "amzn1.ask.account.test"
            }
        },
        "context": {
            "System": {
                "application": {
                    "applicationId": "amzn1.echo-sdk-ams.app.test"
                },
                "user": {
                    "userId": "amzn1.ask.account.test"
                },
                "apiEndpoint": "https://api.amazonalexa.com",
                "apiAccessToken": "token"
            }
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "EdwRequestId.test",
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "intent": {
                "name": intent_name,
                "confirmationStatus": "NONE"
            }
        }
    }
    
    if slots:
        payload["request"]["intent"]["slots"] = slots
        
    if session_attributes:
        payload["session"]["attributes"] = session_attributes
        
    return payload

def run_tests():
    xlsx_path = "test_extrato.xlsx"
    
    # Gera a planilha se não existir
    generate_test_xlsx(xlsx_path)

    # Monkey Patching para fazer o main.get_parser ler o arquivo XLSX local
    def mock_get_parser():
        with open(xlsx_path, "rb") as f:
            return ExcelParser(f, xlsx_path)
            
    main.get_parser = mock_get_parser

    print("\n" + "="*45)
    print("INICIANDO TESTES DO GOOGLE CLOUD FUNCTION")
    print("="*45)

    # Helper para simular chamada HTTP POST à Cloud Function
    def call_alexa_cf(intent_name, slots=None, session_attributes=None):
        payload = build_alexa_payload(intent_name, slots, session_attributes)
        
        # Cria um request mockado do Flask
        req = Mock()
        req.method = "POST"
        req.get_json = Mock(return_value=payload)
        
        # Chama a cloud function
        response_body, status_code, headers = main.alexa_handler(req)
        
        assert status_code == 200, f"Status code retornado foi {status_code}"
        assert headers.get("Content-Type") == "application/json; charset=utf-8"
        
        # Converte a resposta em dicionário
        res_data = json.loads(response_body)
        
        # Extrai a fala em SSML e shouldEndSession
        output_ssml = res_data["response"]["outputSpeech"]["ssml"]
        should_end_session = res_data["response"].get("shouldEndSession", True)
        returned_session_attributes = res_data.get("sessionAttributes", {})
        return output_ssml, should_end_session, returned_session_attributes

    # Teste 1: GetBalanceIntent
    print("\n--- Teste 1: Qual o saldo da conta? (GetBalanceIntent) ---")
    ssml, should_end, session_attr = call_alexa_cf("GetBalanceIntent")
    print(f"Fala Alexa: '{ssml}'")
    assert "1215,10" in ssml, f"Erro no saldo. Fala: {ssml}"
    assert should_end is False, f"Deveria manter a sessão aberta. shouldEndSession: {should_end}"

    # Teste 2: GetPixTodayIntent
    print("\n--- Teste 2: Quais os pix de hoje? (GetPixTodayIntent) ---")
    ssml, should_end, session_attr = call_alexa_cf("GetPixTodayIntent")
    print(f"Fala Alexa: '{ssml}'")
    assert "300,00" in ssml, f"Erro no PIX de hoje. Fala: {ssml}"
    assert should_end is False, f"Deveria manter a sessão aberta. shouldEndSession: {should_end}"

    # Teste 3: GetPixYesterdayIntent
    print("\n--- Teste 3: Quantos pix ontem? (GetPixYesterdayIntent) ---")
    ssml, should_end, session_attr = call_alexa_cf("GetPixYesterdayIntent")
    print(f"Fala Alexa: '{ssml}'")
    assert "recebeu 1 PIX" in ssml and "enviou 1 PIX" in ssml, f"Erro no PIX de ontem. Fala: {ssml}"
    assert should_end is False, f"Deveria manter a sessão aberta. shouldEndSession: {should_end}"

    # Teste 4: GetPixSenderIntent (Valor R$ 150)
    print("\n--- Teste 4: Quem mandou o pix de R$ 150? (GetPixSenderIntent) ---")
    slots = {
        "valor": {
            "name": "valor",
            "value": "150",
            "confirmationStatus": "NONE"
        }
    }
    ssml, should_end, session_attr = call_alexa_cf("GetPixSenderIntent", slots)
    print(f"Fala Alexa: '{ssml}'")
    assert "JOAO DA SILVA" in ssml, f"Erro no remetente. Fala: {ssml}"
    assert should_end is False, f"Deveria manter a sessão aberta. shouldEndSession: {should_end}"

    # Teste 5: GetPixSenderIntent (Inexistente)
    print("\n--- Teste 5: Quem mandou o pix de R$ 999? (GetPixSenderIntent - Inexistente) ---")
    slots = {
        "valor": {
            "name": "valor",
            "value": "999",
            "confirmationStatus": "NONE"
        }
    }
    ssml, should_end, session_attr = call_alexa_cf("GetPixSenderIntent", slots)
    print(f"Fala Alexa: '{ssml}'")
    assert "Não encontrei nenhum PIX" in ssml, f"Deveria avisar que não encontrou o PIX. Fala: {ssml}"
    assert should_end is False, f"Deveria manter a sessão aberta. shouldEndSession: {should_end}"

    # Teste 6: GetPixIntent (Ontem - Recebidos)
    print("\n--- Teste 6: Quais os pix recebidos de ontem? (GetPixIntent - Recebidos) ---")
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    brasilia_offset = datetime.timezone(datetime.timedelta(hours=-3))
    yesterday = utc_now.astimezone(brasilia_offset).date() - datetime.timedelta(days=1)
    slots = {
        "data": {
            "name": "data",
            "value": yesterday.strftime("%Y-%m-%d")
        },
        "operacao": {
            "name": "operacao",
            "value": "recebidos"
        }
    }
    ssml, should_end, session_attr = call_alexa_cf("GetPixIntent", slots)
    print(f"Fala Alexa: '{ssml}'")
    assert "JOAO DA SILVA" in ssml and "recebeu" in ssml and "PEDRO PEREIRA" not in ssml, f"Erro nos PIX recebidos de ontem. Fala: {ssml}"
    assert should_end is False, f"Deveria manter a sessão aberta. shouldEndSession: {should_end}"

    # Teste 7: GetPixIntent (Ontem - Enviados)
    print("\n--- Teste 7: Quais os pix enviados de ontem? (GetPixIntent - Enviados) ---")
    slots = {
        "data": {
            "name": "data",
            "value": yesterday.strftime("%Y-%m-%d")
        },
        "operacao": {
            "name": "operacao",
            "value": "enviados"
        }
    }
    ssml, should_end, session_attr = call_alexa_cf("GetPixIntent", slots)
    print(f"Fala Alexa: '{ssml}'")
    assert "PEDRO PEREIRA" in ssml and "enviou" in ssml and "JOAO DA SILVA" not in ssml, f"Erro nos PIX enviados de ontem. Fala: {ssml}"
    assert should_end is False, f"Deveria manter a sessão aberta. shouldEndSession: {should_end}"

    # Teste 8: AMAZON.StopIntent (Finalizar sessão)
    print("\n--- Teste 8: Parar a Skill (AMAZON.StopIntent) ---")
    ssml, should_end, session_attr = call_alexa_cf("AMAZON.StopIntent")
    print(f"Fala Alexa: '{ssml}'")
    assert "Até logo!" in ssml, f"Erro ao parar a sessão. Fala: {ssml}"
    assert should_end is True, f"Deveria encerrar a sessão. shouldEndSession: {should_end}"

    # Teste 9: GetPixIntent (Contexto restaurado - detalhar sem especificar data)
    print("\n--- Teste 9: Detalhar sem especificar data, usando contexto anterior (GetPixIntent) ---")
    slots = {
        "detalhado": {
            "name": "detalhado",
            "value": "detalhar"
        }
    }
    session_attributes_input = {
        "last_data": "yesterday",
        "last_dia": None,
        "last_operacao": None
    }
    ssml, should_end, session_attr = call_alexa_cf("GetPixIntent", slots, session_attributes_input)
    print(f"Fala Alexa: '{ssml}'")
    assert "JOAO DA SILVA" in ssml and "PEDRO PEREIRA" in ssml, f"Deveria detalhar os PIX de ontem. Fala: {ssml}"
    assert should_end is False, f"Deveria manter a sessão aberta. shouldEndSession: {should_end}"
    assert session_attr.get("last_data") == "yesterday", f"Deveria manter o last_data como 'yesterday'. Atributos: {session_attr}"

    print("\n" + "="*45)
    print("TODOS OS TESTES DA CLOUD FUNCTION PASSARAM COM SUCESSO!")
    print("="*45)

if __name__ == "__main__":
    run_tests()
