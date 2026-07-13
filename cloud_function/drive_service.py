import os
import io
import json
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

class GoogleDriveService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']
        self.creds = self._load_credentials()
        self.service = build('drive', 'v3', credentials=self.creds)

    def _load_credentials(self):
        """
        Carrega as credenciais da Service Account do Google Cloud.
        Suporta o JSON em texto plano ou codificado em Base64 na variável de ambiente GOOGLE_CREDENTIALS.
        """
        creds_raw = os.environ.get('GOOGLE_CREDENTIALS')
        if not creds_raw:
            raise ValueError("A variável de ambiente GOOGLE_CREDENTIALS não foi configurada.")

        try:
            # Tenta decodificar de Base64 caso o usuário tenha salvo dessa forma
            creds_data = json.loads(base64.b64decode(creds_raw).decode('utf-8'))
        except Exception:
            # Caso contrário, tenta ler como JSON direto
            try:
                creds_data = json.loads(creds_raw)
            except Exception as e:
                raise ValueError(f"Erro ao ler as credenciais do Google Drive. Verifique se o JSON está correto: {e}")

        return service_account.Credentials.from_service_account_info(
            creds_data, scopes=self.scopes
        )

    def get_latest_excel_file(self, folder_id):
        """
        Busca o arquivo de extrato (.xlsx) mais recente em uma pasta específica do Google Drive.
        Retorna uma tupla (file_id, file_name).
        """
        query = (
            f"'{folder_id}' in parents and "
            "mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and "
            "trashed = false"
        )
        
        results = self.service.files().list(
            q=query,
            orderBy="modifiedTime desc",
            pageSize=1,
            fields="files(id, name)"
        ).execute()

        files = results.get('files', [])
        if not files:
            raise FileNotFoundError(f"Nenhum arquivo XLSX encontrado na pasta do Drive com ID: {folder_id}")

        return files[0]['id'], files[0]['name']

    def download_file(self, file_id):
        """
        Faz o download do arquivo de ID informado do Google Drive e retorna um fluxo de bytes (BytesIO).
        """
        request = self.service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            
        file_stream.seek(0)
        return file_stream
