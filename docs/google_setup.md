# Configuração do Google Cloud e API do Google Drive

Esta documentação descreve o passo a passo para criar uma conta de serviço no Google Cloud e dar permissão para a AWS Lambda ler os arquivos do seu Google Drive.

## Passo 1: Criar um Projeto no Google Cloud
1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. No menu superior esquerdo (ao lado do logotipo do Google Cloud), clique no seletor de projetos e selecione **Novo Projeto**.
3. Dê um nome ao seu projeto (ex: `Alexa-Extrato-Drive`) e clique em **Criar**.
4. Certifique-se de que o novo projeto está selecionado no menu superior.

## Passo 2: Habilitar a Google Drive API
1. No console do Google Cloud, use a barra de pesquisa no topo e digite **"Google Drive API"**.
2. Clique no resultado **Google Drive API** sob a categoria "Marketplace" ou "APIs e Serviços".
3. Clique no botão **Ativar** (Enable).

## Passo 3: Criar uma Service Account (Conta de Serviço)
1. No menu lateral esquerdo do console, passe o mouse sobre **IAM e administrador** e clique em **Contas de serviço**.
2. No topo da página, clique em **+ Criar conta de serviço**.
3. Preencha os detalhes:
   * **Nome da conta de serviço**: `alexa-extrato-reader`
   * **ID da conta de serviço**: será gerado automaticamente.
   * **Descrição**: `Leitura de arquivos de extrato para a skill Alexa.`
4. Clique em **Criar e Continuar**.
5. Na etapa de papéis (roles), você pode deixar em branco ou atribuir o papel de **Leitor de Projeto** (opcional, pois a permissão de arquivos no Drive será feita diretamente na pasta). Clique em **Continuar**.
6. Clique em **Concluído**.

## Passo 4: Criar e Baixar a Chave de Credenciais (JSON)
1. Na lista de Contas de Serviço, localize a conta que acabou de criar (`alexa-extrato-reader@...`).
2. Clique nos três pontinhos sob a coluna **Ações** daquela conta e selecione **Gerenciar chaves** (Manage keys).
3. Clique em **Adicionar chave** > **Criar nova chave**.
4. Selecione o tipo de chave **JSON** e clique em **Criar**.
5. O download de um arquivo contendo a chave privada em formato JSON será iniciado automaticamente. **Guarde este arquivo em local seguro**, pois ele contém as credenciais de acesso e não poderá ser baixado novamente.

## Passo 5: Compartilhar a pasta do Google Drive
1. Abra o seu Google Drive e acesse a pasta onde os arquivos de extrato XLSX serão armazenados.
2. Copie o e-mail da sua Service Account (encontrado no arquivo JSON baixado no campo `client_email` ou na lista de Contas de Serviço do Google Cloud).
   * Exemplo de e-mail: `alexa-extrato-reader@nome-do-projeto.iam.gserviceaccount.com`
3. Clique com o botão direito na pasta do Google Drive, selecione **Compartilhar**.
4. Cole o e-mail da Service Account no campo de compartilhamento.
5. Defina a permissão como **Leitor** (Viewer) e desmarque a opção "Enviar notificação" (não é necessário).
6. Clique em **Compartilhar**.

## Passo 6: Obter o ID da Pasta do Drive
1. Entre na pasta compartilhada no Google Drive.
2. Observe a URL no seu navegador. Ela terá a seguinte estrutura:
   `https://drive.google.com/drive/folders/ID_DA_PASTA_AQUI`
3. O código alfanumérico ao final da URL (após `folders/`) é o seu **DRIVE_FOLDER_ID**. Copie e guarde esse valor, pois ele será configurado na AWS Lambda.

---

## Preparando a Credencial para a AWS Lambda
A AWS Lambda precisará ler a credencial do arquivo JSON. Para evitar quebras de linha e caracteres especiais nas variáveis de ambiente da Lambda, você pode usar uma das duas abordagens:

### Opção A: Texto corrido (JSON puro)
Remova as quebras de linha do arquivo JSON gerado deixando todo o conteúdo em uma única linha.
Exemplo: `{"type": "service_account", "project_id": ...}`

### Opção B: Codificação em Base64 (Recomendado)
Você pode converter todo o arquivo JSON para uma string Base64. A Lambda está configurada para decodificar Base64 automaticamente se necessário.
Para converter o arquivo JSON para Base64:
* **No Windows (PowerShell)**:
  ```powershell
  [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("caminho\para\seu\arquivo-credenciais.json"))
  ```
* **No macOS/Linux (Terminal)**:
  ```bash
  base64 -i caminho/para/seu/arquivo-credenciais.json
  ```
Copie a string resultante gerada e utilize-a na variável de ambiente `GOOGLE_CREDENTIALS` na AWS Lambda.
