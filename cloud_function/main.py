import os
import logging
import functions_framework
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.serialize import DefaultSerializer
from ask_sdk_model import Response, RequestEnvelope

from drive_service import GoogleDriveService
from excel_parser import ExcelParser

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_parser():
    """
    Função auxiliar para obter o parser de Excel carregando o arquivo
    mais recente da pasta configurada no Google Drive.
    """
    folder_id = os.environ.get("DRIVE_FOLDER_ID")
    if not folder_id:
        raise ValueError("A variável de ambiente DRIVE_FOLDER_ID não está configurada.")
    
    drive_service = GoogleDriveService()
    file_id, file_name = drive_service.get_latest_excel_file(folder_id)
    logger.info(f"Arquivo XLSX de extrato localizado no Drive: {file_name} (ID: {file_id})")
    
    file_stream = drive_service.download_file(file_id)
    return ExcelParser(file_stream)

# --- Handlers da Alexa ---

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak_output = (
            "Olá! Sou seu assistente de extrato bancário no Google Cloud. "
            "Você pode me perguntar sobre seu saldo, os PIX de hoje, de ontem, ou quem enviou um PIX específico. "
            "Como posso ajudar?"
        )
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class GetBalanceIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetBalanceIntent")(handler_input)

    def handle(self, handler_input):
        try:
            parser = get_parser()
            balance = parser.get_balance()
            speak_output = f"O saldo atual da sua conta é de R$ {balance:.2f}."
            speak_output = speak_output.replace(".", ",")
        except Exception as e:
            logger.error(f"Erro no GetBalanceIntent: {e}", exc_info=True)
            speak_output = "Desculpe, ocorreu um erro ao consultar o seu saldo no extrato do Google Drive."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .set_should_end_session(True)
                .response
        )

class GetPixTodayIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetPixTodayIntent")(handler_input)

    def handle(self, handler_input):
        try:
            parser = get_parser()
            pix_list = parser.get_today_pix_received()
            
            if not pix_list:
                speak_output = "Você não recebeu nenhum PIX hoje até o momento."
            else:
                total_val = sum(p["valor"] for p in pix_list)
                if len(pix_list) == 1:
                    speak_output = f"Hoje você recebeu um PIX de R$ {total_val:.2f}."
                else:
                    speak_output = f"Hoje você recebeu {len(pix_list)} PIX, totalizando R$ {total_val:.2f}. "
                    detalhes = []
                    for p in pix_list:
                        detalhes.append(f"de R$ {p['valor']:.2f} com descrição {p['descricao']}")
                    speak_output += "Os lançamentos foram: " + " e ".join(detalhes) + "."
                
                speak_output = speak_output.replace(".", ",")
        except Exception as e:
            logger.error(f"Erro no GetPixTodayIntent: {e}", exc_info=True)
            speak_output = "Desculpe, ocorreu um erro ao consultar os PIX de hoje."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .set_should_end_session(True)
                .response
        )

class GetPixYesterdayIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetPixYesterdayIntent")(handler_input)

    def handle(self, handler_input):
        try:
            parser = get_parser()
            summary = parser.get_yesterday_pix_summary()
            
            if summary["total_count"] == 0:
                speak_output = "Ontem você não teve nenhuma transação por PIX."
            else:
                partes = []
                if summary["count_received"] > 0:
                    partes.append(f"recebeu {summary['count_received']} PIX no total de R$ {summary['total_received']:.2f}")
                if summary["count_sent"] > 0:
                    partes.append(f"enviou {summary['count_sent']} PIX no total de R$ {summary['total_sent']:.2f}")
                
                speak_output = "Ontem você " + " e ".join(partes) + "."
                speak_output = speak_output.replace(".", ",")
        except Exception as e:
            logger.error(f"Erro no GetPixYesterdayIntent: {e}", exc_info=True)
            speak_output = "Desculpe, ocorreu um erro ao consultar os PIX de ontem."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .set_should_end_session(True)
                .response
        )

class GetPixSenderIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetPixSenderIntent")(handler_input)

    def handle(self, handler_input):
        try:
            slots = handler_input.request_envelope.request.intent.slots
            valor_slot = slots.get("valor")
            
            if not valor_slot or valor_slot.value is None:
                speak_output = "Não consegui entender o valor. Por favor, diga quem mandou o PIX e informe o valor."
                return (
                    handler_input.response_builder
                        .speak(speak_output)
                        .ask("Qual o valor do PIX que você deseja consultar?")
                        .response
                )
            
            valor = float(valor_slot.value)
            parser = get_parser()
            sender_info = parser.find_pix_sender(valor)
            
            if not sender_info:
                speak_output = f"Não encontrei nenhum PIX recebido no valor de R$ {valor:.2f}."
            else:
                speak_output = (
                    f"O PIX de R$ {sender_info['valor']:.2f} foi enviado por "
                    f"{sender_info['remetente']} no dia {sender_info['data']}."
                )
            
            speak_output = speak_output.replace(".", ",")
        except Exception as e:
            logger.error(f"Erro no GetPixSenderIntent: {e}", exc_info=True)
            speak_output = "Desculpe, ocorreu um erro ao consultar o remetente do PIX."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .set_should_end_session(True)
                .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = (
            "Você pode me perguntar: qual o meu saldo? Quais os PIX de hoje? "
            "Quantos PIX eu recebi ontem? Ou de quem foi o PIX de 50 reais? "
            "O que você deseja saber?"
        )
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        speak_output = "Até logo!"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        logger.info(f"Sessão encerrada com motivo: {handler_input.request_envelope.request.reason}")
        return handler_input.response_builder.response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(f"Exceção não tratada: {exception}", exc_info=True)
        speak_output = "Desculpe, tive um problema para processar o seu comando. Por favor, tente novamente."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# --- Registro de Handlers na Skill Builder ---

sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GetBalanceIntentHandler())
sb.add_request_handler(GetPixTodayIntentHandler())
sb.add_request_handler(GetPixYesterdayIntentHandler())
sb.add_request_handler(GetPixSenderIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

# Compila a skill e inicializa o serializador
skill = sb.create()
serializer = DefaultSerializer()

# --- Gatilho HTTP do Google Cloud Functions (Functions Framework) ---

@functions_framework.http
def alexa_handler(request):
    """
    Entrypoint HTTP da Cloud Function. Recebe a requisição POST JSON vinda da Alexa,
    delega ao SDK e retorna a resposta formatada em JSON.
    """
    if request.method != "POST":
        return "Método Não Permitido", 405

    request_json = request.get_json(silent=True)
    if not request_json:
        return "JSON Inválido", 400

    try:
        # Importante: O ask-sdk-core do Python espera um objeto RequestEnvelope do SDK
        # e não um dicionário Python simples. Portanto, precisamos desserializá-lo primeiro.
        import json
        request_envelope = serializer.deserialize(
            json.dumps(request_json), RequestEnvelope
        )
        
        # Invoca a skill Alexa usando o objeto desserializado
        response_envelope = skill.invoke(request_envelope=request_envelope, context=None)
        
        # Serializa para dicionário e converte para string JSON
        response_dict = serializer.serialize(response_envelope)
        response_json = json.dumps(response_dict)
        
        return response_json, 200, {"Content-Type": "application/json; charset=utf-8"}
    except Exception as e:
        logger.error(f"Erro na execução da Cloud Function: {e}", exc_info=True)
        return "Erro interno ao processar requisição", 500, {"Content-Type": "text/plain; charset=utf-8"}
