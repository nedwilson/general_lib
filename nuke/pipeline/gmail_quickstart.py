#!/usr/bin/python

from __future__ import print_function

import ConfigParser
import sys
import os

# gmail/oauth

import httplib2
import oauth2client
import base64
import mimetypes

from oauth2client import client, tools
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import errors, discovery
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase

g_ih_show_cfg_path = None
g_ih_show_root = None
g_ih_show_code = None
g_config = None
g_show_code = ""
g_shared_root = ""
g_credentials_dir = ""
g_client_secret = ""
g_gmail_creds = ""
g_gmail_scopes = ""
g_application_name = ""

def main():

    try:
        g_ih_show_code = os.environ['IH_SHOW_CODE']
        g_ih_show_root = os.environ['IH_SHOW_ROOT']
        g_ih_show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
        g_config = ConfigParser.ConfigParser()
        g_config.read(g_ih_show_cfg_path)
        g_shared_root = g_config.get('shared_root', sys.platform)
        credentials_dir_dict = { 'pathsep' : os.path.sep, 'shared_root' : g_shared_root }
        g_credentials_dir = g_config.get('email', 'credentials_dir').format(**credentials_dir_dict)
        g_client_secret = g_config.get('email', 'client_secret')
        g_gmail_creds = g_config.get('email', 'gmail_creds')
        g_gmail_scopes = g_config.get('email', 'gmail_scopes')
        g_application_name = g_config.get('email', 'application_name')
        print("Globals initiliazed from config %s."%g_ih_show_cfg_path)
    except KeyError:
        e = sys.exc_info()
        print(e[1])
        print("This is most likely because this system has not been set up to run inside the In-House environment.")
    except ConfigParser.NoSectionError:
        e = sys.exc_info()
        print(e[1])
    except ConfigParser.NoOptionError:
        e = sys.exc_info()
        print(e[1])
    except:        
        e = sys.exc_info()
        print(e[1])

    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """

    credential_path = os.path.join(g_credentials_dir, g_gmail_creds)
    client_secret_path = os.path.join(g_credentials_dir, g_client_secret)

    if not os.path.exists(client_secret_path):
    	print("ERROR: You must first create the credentials.json file within Google\'s API tools.")
    	print("In a web browser, go here: https://developers.google.com/gmail/api/quickstart/python")
    	print("Then, rename it as client_secret.json and copy it here: %s"%client_secret_path)
    	exit()

    print("Searching for credential: %s"%credential_path)
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(client_secret_path, g_gmail_scopes)
        flow.user_agent = g_application_name
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)


    http_auth = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http_auth, cache_discovery=False)

    # Call the Gmail API
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    if not labels:
        print('No labels found.')
    else:
        print('Labels:')
        for label in labels:
            print(label['name'])

if __name__ == '__main__':
    main()