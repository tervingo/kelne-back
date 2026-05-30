"""
Ejecuta este script UNA VEZ para obtener el refresh token de Dropbox.
Luego añade DROPBOX_REFRESH_TOKEN=<token> en las variables de entorno de Render y en .env local.

Uso:  python setup_dropbox.py
"""
import os
from dotenv import load_dotenv
from dropbox import DropboxOAuth2FlowNoRedirect

load_dotenv()

APP_KEY    = 'gr6xmm34rgxsy6x'
APP_SECRET = os.getenv('DROPBOX_APP_SECRET')

if not APP_SECRET:
    print('ERROR: DROPBOX_APP_SECRET no encontrado en .env')
    exit(1)

auth_flow = DropboxOAuth2FlowNoRedirect(
    APP_KEY,
    consumer_secret=APP_SECRET,
    token_access_type='offline',
)

authorize_url = auth_flow.start()
print('\n1. Abre esta URL en tu navegador:')
print(f'\n   {authorize_url}\n')
print('2. Autoriza la aplicación y copia el código que aparece.')

auth_code = input('\n3. Pega el código aquí: ').strip()
result = auth_flow.finish(auth_code)

print('\n✓ Añade estas variables en .env y en Render:')
print(f'\n   DROPBOX_ACCESS_TOKEN={result.access_token}')
print(f'   DROPBOX_REFRESH_TOKEN={result.refresh_token}\n')
print('El access token expira en ~4 horas. El refresh token es permanente (para uso futuro).')
