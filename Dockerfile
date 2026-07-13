# Use a imagem oficial do Python slim para manter o container leve
FROM python:3.12-slim

# Evita que o Python grave arquivos .pyc no disco e faça buffer no stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos de dependência primeiro para aproveitar a cache de build do Docker
COPY cloud_function/requirements.txt .

# Instala as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da Cloud Function para o container
COPY cloud_function/ .

# Expõe a porta 8080 usada pelo Functions Framework
EXPOSE 8080

# Comando para iniciar a Cloud Function localmente via Functions Framework
CMD ["functions-framework", "--target=alexa_handler", "--signature-type=http", "--port=8080"]
