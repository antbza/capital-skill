# Configuração e Implantação no Google Cloud Functions (GCP)

Esta documentação descreve o passo a passo para criar e implantar a sua Cloud Function no GCP.

## Pré-requisitos
Certifique-se de que você já configurou a Service Account e o Google Drive conforme detalhado em [google_setup.md](google_setup.md). Você precisará de:
*   O ID da pasta do Drive (`DRIVE_FOLDER_ID`).
*   O JSON das credenciais em formato corrido ou Base64 (`GOOGLE_CREDENTIALS`).

---

## Opção A: Implantação via Console Web (Mais Fácil)

1.  Acesse o painel do [Google Cloud Functions](https://console.cloud.google.com/functions).
2.  Clique em **Criar Função** (Create Function) no topo da página.
3.  Preencha as configurações do **Ambiente de Execução** (Configuration):
    *   **Ambiente (Environment)**: Selecione **2nd gen** (2ª geração).
    *   **Nome da Função**: `alexa-extrato-reader`
    *   **Região**: Selecione `us-central1` (ou a região de sua preferência).
    *   **Gatilho (Trigger)**: Selecione **HTTPS**.
    *   **Autenticação**: Selecione **Permitir invocações não autenticadas** (Allow unauthenticated invocations). *Isso é necessário para que os servidores da Alexa consigam enviar requisições POST para a sua URL.*
4.  Clique na seção **Configurações de tempo de execução, build, conexões e segurança** (Runtime, build, connections and security settings) na mesma página para expandi-la:
    *   Acesse a aba **Variáveis de Ambiente** (Environment variables).
    *   Adicione duas variáveis de ambiente sob "Variáveis de ambiente do tempo de execução" (Runtime environment variables):
        *   **`DRIVE_FOLDER_ID`**: O ID da pasta do seu Google Drive.
        *   **`GOOGLE_CREDENTIALS`**: O JSON da sua Service Account (em uma linha só ou em Base64).
    *   (Opcional) Ajuste o **Timeout** para `15s` na mesma página, para dar tempo da função se comunicar com o Drive sem estourar o limite de tempo.
5.  Clique em **Próximo** (Next) no final da página.
6.  Na tela de código:
    *   **Runtime**: Selecione **Python 3.12** (ou Python 3.11).
    *   **Ponto de Entrada (Entry Point)**: Altere de `hello_http` para **`alexa_handler`** (o nome da nossa função no `main.py`).
    *   No painel esquerdo, você verá os arquivos do editor inline. Você pode:
        *   Selecionar **Carregar ZIP** (ZIP Upload) no topo de "Código fonte" (Source code) e subir um arquivo ZIP contendo apenas os 4 arquivos da pasta `cloud_function/` (`main.py`, `drive_service.py`, `excel_parser.py`, `requirements.txt`).
        *   *Ou* simplesmente copiar e colar o conteúdo dos arquivos diretamente nos arquivos correspondentes no editor web (adicione novos arquivos clicando no botão de "+" se necessário).
7.  Clique em **Implantar** (Deploy). O processo de criação e compilação leva cerca de 2 minutos.
8.  Uma vez finalizado, copie a **URL** exibida no topo da página. Ela terá uma estrutura semelhante a:
    `https://alexa-extrato-reader-xxxxxx-uc.a.run.app`
    *Esta URL será configurada como o endpoint na Developer Console da Alexa.*

---

## Opção B: Implantação via Linha de Comando (gcloud CLI)

Se você já possui o `gcloud SDK` instalado e configurado em sua máquina local, você pode fazer o deploy diretamente pelo terminal.

1.  Abra seu terminal no diretório do projeto: `c:\projetos\capital`
2.  Execute o seguinte comando para implantar a função contida na pasta `cloud_function`:
    ```bash
    gcloud functions deploy alexa-extrato-reader \
        --gen2 \
        --runtime=python312 \
        --region=us-central1 \
        --source=./cloud_function \
        --entry-point=alexa_handler \
        --trigger-http \
        --allow-unauthenticated \
        --set-env-vars DRIVE_FOLDER_ID="SEU_DRIVE_FOLDER_ID_AQUI",GOOGLE_CREDENTIALS="SEU_JSON_DE_CREDENCIAIS_AQUI"
    ```
3.  Após a conclusão, o comando imprimirá as informações da função na tela. Localize e copie o campo `uri` (que representa a URL HTTPS pública da função).

## Opção C: Implantação Contínua via GitHub Actions (Recomendado)

Você pode configurar o deploy automático sempre que fizer um push na branch `main` do seu repositório do GitHub.

### Passo 1: Configurar Secrets no Repositório do GitHub
Acesse a página do seu repositório no GitHub (`https://github.com/antbza/capital-skill`), vá em **Settings > Secrets and variables > Actions** e clique em **New repository secret** para criar as seguintes Secrets:

1. **`GCP_SA_KEY`**: O conteúdo completo do arquivo JSON de credenciais da sua Service Account (`capital-502320-0389474aebac.json`).
2. **`GOOGLE_CREDENTIALS`**: O JSON da sua Service Account codificado em Base64 ou texto plano (o mesmo valor que está no seu `.env` local).
3. **`DRIVE_FOLDER_ID`**: O ID da pasta do Google Drive onde estão os arquivos de extrato.
4. **`ALEXA_SKILL_ID`**: *(Opcional, recomendado para segurança)* O ID da sua Alexa Skill (ex: `amzn1.ask.skill.xxxx-xxxx`). Serve para a Cloud Function validar que a requisição partiu unicamente da sua Skill.


### Passo 2: Permissões Necessárias no GCP IAM
A Service Account utilizada precisa dos seguintes papéis no GCP:
*   **Administrador do Cloud Functions** (`roles/cloudfunctions.admin`) ou **Desenvolvedor do Cloud Functions** (`roles/cloudfunctions.developer`)
*   **Usuário de Conta de Serviço** (`roles/iam.serviceAccountUser`) no projeto e na conta de serviço padrão do Compute Engine.
*   **Criador de Builds do Cloud Build** (`roles/cloudbuild.builds.editor`)
*   **Administrador de Armazenamento** (`roles/storage.admin`)
*   **Escritor do Artifact Registry** (`roles/artifactregistry.writer`)

---

## Passo Extra: Configuração de Timeout e Recursos (Recomendado)
A leitura de planilhas XLSX e conexões HTTP com APIs do Google Drive podem eventualmente demorar de 2 a 5 segundos dependendo do tamanho da planilha.
Certifique-se de que a Cloud Function está configurada com:
*   **Memória RAM**: 256MB ou 512MB (padrão de 256MB de 2ª geração funciona perfeitamente).
*   **Timeout**: 15 a 30 segundos (evita que a função falhe prematuramente caso o Google Drive responda com lentidão).
