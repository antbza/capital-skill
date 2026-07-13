# Configuração da Alexa Skill

Esta documentação descreve o passo a passo para criar e configurar a Skill Alexa privada para interagir com a sua Google Cloud Function.

## Passo 1: Acessar a Alexa Developer Console
1. Acesse o [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
2. Faça login com a sua conta da Amazon (preferencialmente a mesma que está vinculada aos seus dispositivos Alexa físicos para facilitar o teste).

## Passo 2: Criar uma Nova Skill
1. Clique em **Create Skill** no canto superior direito.
2. Defina os seguintes campos:
   * **Skill name**: `Meu Extrato`
   * **Primary locale**: `Portuguese (Brazil)`
3. Na seção **Choose a model to add to your skill**, selecione **Custom**.
4. Na seção **Choose a method to host your skill's backend resources**, selecione **Provision your own** (isso nos permite apontar para a nossa própria URL HTTPS pública).
5. Clique em **Create skill** no topo.
6. Na etapa de seleção de template, escolha **Start from scratch** (Começar do zero) e clique em **Create skill**.

## Passo 3: Importar o Modelo de Interação
Vamos carregar as intenções e frases de ativação que criamos em nosso arquivo JSON.
1. No menu lateral esquerdo, sob **Interaction Model**, clique em **JSON Editor**.
2. Apague todo o conteúdo padrão que estiver no editor de texto.
3. Abra o arquivo `alexa/interaction_model.json` gerado neste projeto, copie todo o seu conteúdo e cole no editor da console Alexa.
4. Clique em **Save Model** (Salvar modelo) no topo da tela.
5. Clique em **Build Model** (Construir modelo) no topo. Aguarde alguns instantes até que a construção seja concluída (uma notificação aparecerá informando o sucesso).

## Passo 4: Configurar o Endpoint (Vincular à Cloud Function)
Agora vincularemos a Skill ao backend no Google Cloud.
1. No menu lateral esquerdo, clique em **Endpoint**.
2. Selecione a opção **HTTPS**.
3. No campo **Default Region**, cole a **URL** da sua Google Cloud Function que você gerou no passo anterior (ex: `https://alexa-extrato-reader-xxxxxx-uc.a.run.app`).
4. Logo abaixo, no seletor de certificado SSL (**SSL Certificate Type**), selecione a opção:
   `My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority`
   *(Esta opção é necessária e compatível com as URLs padrão fornecidas pelo Google Cloud Cloud Run/Functions).*
5. Clique em **Save Endpoints** no topo.

## Passo 5: Copiar o ID da Skill
1. Ainda na tela de **Endpoint**, você verá o campo **Your Skill ID** (ex: `amzn1.ask.skill.12345678-abcd-...`). Copie este valor se desejar futuramente implementar alguma lógica de validação do ID da skill no seu código.

## Passo 6: Testar no Simulador da Alexa
1. Na barra de navegação superior da Developer Console, clique na aba **Test**.
2. No menu suspenso de ativação do teste, mude de "Off" para **Development**.
3. Na caixa de texto de chat ou clicando no ícone do microfone, digite ou fale a frase de ativação da Skill:
   > "abrir meu extrato"
4. A Alexa responderá com a mensagem de boas-vindas do LaunchRequest.
5. Em seguida, experimente as perguntas de teste:
   * *"qual o saldo da conta?"*
   * *"quais os pix de hoje?"*
   * *"quantos pix tiveram ontem?"*
   * *"quem mandou o pix de 150 reais?"* (caso esteja testando com a planilha fictícia)

## Utilização em Dispositivos Físicos (Echo / Fire TV)
Como esta Skill está em modo de desenvolvimento (Development) e associada à sua conta de desenvolvedor, **ela já está ativa de forma privada em todos os seus dispositivos Alexa vinculados à mesma conta da Amazon**.
* Você pode testar diretamente no seu Echo físico dizendo: *"Alexa, abrir meu extrato"*.
* Não é necessário publicar a Skill na loja pública para usá-la no seu dia a dia. Ela permanecerá privada e segura.
