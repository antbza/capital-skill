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
    logger.info(f"Arquivo de extrato localizado no Drive: {file_name} (ID: {file_id})")
    
    file_stream = drive_service.download_file(file_id)
    return ExcelParser(file_stream, file_name)

def get_brasilia_today():
    import datetime
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    brasilia_offset = datetime.timezone(datetime.timedelta(hours=-3))
    return utc_now.astimezone(brasilia_offset).date()

def resolve_target_date(data_slot_value, dia_slot_value):
    import datetime
    today = get_brasilia_today()
    
    # 1. Se informou o dia do mês (dia_slot_value)
    if dia_slot_value:
        try:
            target_day = int(dia_slot_value)
            target_date = datetime.date(today.year, today.month, target_day)
            if target_date > today:
                raise ValueError("Futuro")
        except ValueError:
            if today.month == 1:
                prev_month = 12
                prev_year = today.year - 1
            else:
                prev_month = today.month - 1
                prev_year = today.year
            
            import calendar
            last_day = calendar.monthrange(prev_year, prev_month)[1]
            target_date = datetime.date(prev_year, prev_month, min(target_day, last_day))
            
        return target_date, target_date, False, f"no dia {target_date.strftime('%d/%m')}"

    # 2. Se informou a data (data_slot_value)
    if data_slot_value:
        val = str(data_slot_value).lower()
        if val in ("today", "hoje"):
            return today, today, False, "hoje"
        if val in ("yesterday", "ontem"):
            yest = today - datetime.timedelta(days=1)
            return yest, yest, False, "ontem"
            
        # Formato ISO completo: YYYY-MM-DD
        if len(val) == 10 and val.count('-') == 2:
            try:
                parts = val.split('-')
                target_date = datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
                
                # Se a data resolvida for no futuro, verifica se é um dia da semana (ex: quarta-feira)
                # e ajusta para a última ocorrência (passada) desse dia da semana
                if target_date > today:
                    target_date = target_date - datetime.timedelta(days=7)
                
                desc = "hoje" if target_date == today else ("ontem" if target_date == today - datetime.timedelta(days=1) else f"no dia {target_date.strftime('%d/%m')}")
                return target_date, target_date, False, desc
            except ValueError:
                pass
                
        # Formato de Semana: YYYY-Wxx (ex: 2026-W29)
        if '-w' in val:
            try:
                parts = val.split('-w')
                year = int(parts[0])
                week = int(parts[1][:2])
                
                start_date = datetime.date.fromisocalendar(year, week, 1)
                end_date = datetime.date.fromisocalendar(year, week, 7)
                return start_date, end_date, True, "esta semana"
            except Exception:
                pass
                
        # Formato de Mês: YYYY-MM (ex: 2026-07)
        if len(val) == 7 and val.count('-') == 1:
            try:
                parts = val.split('-')
                year = int(parts[0])
                month = int(parts[1])
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                start_date = datetime.date(year, month, 1)
                end_date = datetime.date(year, month, last_day)
                
                meses = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
                return start_date, end_date, True, f"no mês de {meses[month]}"
            except Exception:
                pass

    # Fallback padrão: hoje
    return today, today, False, "hoje"

def execute_pix_query(data_val, dia_val, detalhado_val, operacao_val=None):
    start_date, end_date, is_range, date_desc = resolve_target_date(data_val, dia_val)
    parser = get_parser()
    
    # Resolve tipo de operação
    filter_tipo = None
    if operacao_val:
        op = str(operacao_val).lower()
        if any(w in op for w in ["receb", "entrad", "cred", "créd", "ganh"]):
            filter_tipo = "recebido"
        elif any(w in op for w in ["envi", "said", "saíd", "deb", "déb", "pag", "gast"]):
            filter_tipo = "enviado"
            
    pix_list = []
    count_received = 0
    total_received = 0.0
    count_sent = 0
    total_sent = 0.0
    
    for t in parser.transactions:
        if start_date <= t["data"] <= end_date:
            desc = t["lancamento"].upper()
            if "PIX" in desc:
                tipo = None
                valor = 0.0
                if t["credito"] > 0:
                    tipo = "recebido"
                    valor = t["credito"]
                elif t["debito"] > 0:
                    tipo = "enviado"
                    valor = t["debito"]
                
                if tipo:
                    if filter_tipo and tipo != filter_tipo:
                        continue
                        
                    if tipo == "recebido":
                        count_received += 1
                        total_received += valor
                    else:
                        count_sent += 1
                        total_sent += valor
                        
                    orig_desc = t["lancamento"]
                    cleaned = orig_desc
                    prefixes = [
                        "PIX RECEBIDO DE ", "PIX RECEBIDO - ", "PIX RECEBIDO: ", "PIX RECEBIDO ",
                        "PIX ENVIADO PARA ", "PIX ENVIADO - ", "PIX ENVIADO: ", "PIX ENVIADO ",
                        "PIX TRANSF DE ", "PIX TRANSF PARA ", "PIX TRANSF - ", "PIX TRANSF ",
                        "PIX CR DE ", "PIX CR ", "PIX CREDITO DE ", "PIX CREDITO ",
                        "PIX DEB DE ", "PIX DEB ", "PIX DEBITO PARA ", "PIX DEBITO ",
                        "PIX RECEB ", "PIX REC "
                    ]
                    for p in prefixes:
                        if cleaned.upper().startswith(p):
                            cleaned = cleaned[len(p):].strip()
                            break
                    
                    pix_list.append({
                        "tipo": tipo,
                        "valor": valor,
                        "remetente": cleaned,
                        "hora": t.get("hora"),
                        "data": t["data"]
                    })
                    
    if not pix_list:
        if filter_tipo == "recebido":
            return f"Você não recebeu nenhum PIX {date_desc}."
        elif filter_tipo == "enviado":
            return f"Você não enviou nenhum PIX {date_desc}."
        else:
            return f"Você não teve nenhuma transação por PIX {date_desc}."
        
    # Verifica se quer detalhado (se explicitou ou se o resultado é menor/igual a 5 itens)
    forcar_detalhado = False
    if detalhado_val:
        d_val = str(detalhado_val).lower()
        if any(w in d_val for w in ["detalh", "especific", "complet"]):
            forcar_detalhado = True
            
    quer_detalhes = forcar_detalhado or (len(pix_list) <= 5)
    
    if not quer_detalhes:
        if filter_tipo == "recebido":
            speak_output = f"No período de {date_desc}, você recebeu {count_received} PIX, totalizando R$ {total_received:.2f}. Se quiser ouvir os detalhes de cada um, peça para detalhar."
        elif filter_tipo == "enviado":
            speak_output = f"No período de {date_desc}, você enviou {count_sent} PIX, totalizando R$ {total_sent:.2f}. Se quiser ouvir os detalhes de cada um, peça para detalhar."
        else:
            partes = []
            if count_received > 0:
                partes.append(f"recebeu {count_received} PIX no total de R$ {total_received:.2f}")
            if count_sent > 0:
                partes.append(f"enviou {count_sent} PIX no total de R$ {total_sent:.2f}")
            speak_output = f"No período de {date_desc}, você " + " e ".join(partes) + ". Se quiser ouvir os detalhes de cada um, peça para detalhar."
    else:
        if len(pix_list) == 1:
            p = pix_list[0]
            time_desc = f" às {p['hora'].strftime('%H:%M')}" if p.get("hora") else ""
            if p["tipo"] == "recebido":
                speak_output = f"Você recebeu um PIX de R$ {p['valor']:.2f} de {p['remetente']}{time_desc} {date_desc}."
            else:
                speak_output = f"Você enviou um PIX de R$ {p['valor']:.2f} para {p['remetente']}{time_desc} {date_desc}."
        else:
            if filter_tipo == "recebido":
                speak_output = f"No período de {date_desc}, você recebeu {count_received} PIX, totalizando R$ {total_received:.2f}. "
            elif filter_tipo == "enviado":
                speak_output = f"No período de {date_desc}, você enviou {count_sent} PIX, totalizando R$ {total_sent:.2f}. "
            else:
                partes_resumo = []
                if count_received > 0:
                    partes_resumo.append(f"recebeu {count_received} PIX")
                if count_sent > 0:
                    partes_resumo.append(f"enviou {count_sent} PIX")
                total_geral = sum(p['valor'] for p in pix_list)
                speak_output = f"No período de {date_desc}, você " + " e ".join(partes_resumo) + f", totalizando R$ {total_geral:.2f}. "
                
            detalhes = []
            for p in pix_list:
                time_desc = f" às {p['hora'].strftime('%H:%M')}" if p.get("hora") else ""
                day_desc = f" no dia {p['data'].strftime('%d/%m')}" if is_range else ""
                if filter_tipo == "recebido":
                    detalhes.append(f"um de R$ {p['valor']:.2f} de {p['remetente']}{time_desc}{day_desc}")
                elif filter_tipo == "enviado":
                    detalhes.append(f"um de R$ {p['valor']:.2f} para {p['remetente']}{time_desc}{day_desc}")
                else:
                    if p["tipo"] == "recebido":
                        detalhes.append(f"um recebido de R$ {p['valor']:.2f} de {p['remetente']}{time_desc}{day_desc}")
                    else:
                        detalhes.append(f"um enviado de R$ {p['valor']:.2f} para {p['remetente']}{time_desc}{day_desc}")
            speak_output += "Os lançamentos foram: " + " e ".join(detalhes) + "."
            
    return speak_output.replace(".", ",")


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
            speak_output = execute_pix_query("today", None, None)
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
            speak_output = execute_pix_query("yesterday", None, None)
        except Exception as e:
            logger.error(f"Erro no GetPixYesterdayIntent: {e}", exc_info=True)
            speak_output = "Desculpe, ocorreu um erro ao consultar os PIX de ontem."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .set_should_end_session(True)
                .response
        )

class GetPixIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetPixIntent")(handler_input)

    def handle(self, handler_input):
        try:
            slots = handler_input.request_envelope.request.intent.slots
            data_slot = slots.get("data")
            dia_slot = slots.get("dia")
            detalhado_slot = slots.get("detalhado")
            operacao_slot = slots.get("operacao")
            
            data_val = data_slot.value if data_slot else None
            dia_val = dia_slot.value if dia_slot else None
            detalhado_val = detalhado_slot.value if detalhado_slot else None
            operacao_val = operacao_slot.value if operacao_slot else None
            
            speak_output = execute_pix_query(data_val, dia_val, detalhado_val, operacao_val)
        except Exception as e:
            logger.error(f"Erro no GetPixIntent: {e}", exc_info=True)
            speak_output = "Desculpe, ocorreu um erro ao consultar as transações de PIX."

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
sb.add_request_handler(GetPixIntentHandler())
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

    # Valida o ID da Skill (se configurado nas variáveis de ambiente) para fins de segurança
    allowed_skill_id = os.environ.get("ALEXA_SKILL_ID")
    if allowed_skill_id:
        req_skill_id = None
        try:
            req_skill_id = request_json.get("session", {}).get("application", {}).get("applicationId")
            if not req_skill_id:
                req_skill_id = request_json.get("context", {}).get("System", {}).get("application", {}).get("applicationId")
        except Exception:
            pass
            
        if req_skill_id != allowed_skill_id:
            logger.warning(f"Chamada rejeitada: Skill ID incorreto ou ausente ({req_skill_id})")
            return "Acesso Proibido", 403

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
