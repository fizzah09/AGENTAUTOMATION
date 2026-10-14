"""Optional, in-memory OAuth 2 Gmail integration using only Python stdlib.
No email is sent automatically. Use OAuth with the operator's own TEST Gmail account.
"""
import base64
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from datetime import datetime, timezone
from email.utils import parseaddr

READ_SCOPE='https://www.googleapis.com/auth/gmail.readonly'
SEND_SCOPE='https://www.googleapis.com/auth/gmail.send'
ENTERPRISE_MODE=os.environ.get('AEGIS_ENTERPRISE_MODE')=='1'
REDIRECT='http://127.0.0.1:8765/api/gmail/callback'

class GmailConnection:
    def __init__(self):
        self.client_id=os.environ.get('AEGIS_GOOGLE_CLIENT_ID','')
        self.client_secret=os.environ.get('AEGIS_GOOGLE_CLIENT_SECRET','')
        self.oauth_state=None
        self.access_token=None
        self.refresh_token=None
        self.expires_at=0
        self.account=None
        self.granted_scopes=set()

    def configure(self, client_id, secret):
        if not client_id.endswith('.apps.googleusercontent.com') or not secret:
            raise ValueError('Provide a valid Google OAuth client ID and secret from Google Cloud Console.')
        self.client_id=client_id.strip()
        self.client_secret=secret.strip()
        self.disconnect()

    def disconnect(self):
        self.access_token=None; self.refresh_token=None; self.expires_at=0; self.account=None; self.oauth_state=None
        self.granted_scopes=set()

    def status(self):
        import storage
        enabled=bool(ENTERPRISE_MODE and storage.delivery_setting())
        allowed=SEND_SCOPE in self.granted_scopes
        return {'configured':bool(self.client_id and self.client_secret),
                'connected':bool(self.access_token or self.refresh_token),
                'account':self.account or '',
                'enterprise_mode':ENTERPRISE_MODE,
                'delivery_requested':storage.delivery_setting() if ENTERPRISE_MODE else False,
                'send_permission_granted':allowed,
                'sending_enabled':enabled and allowed and bool(self.access_token or self.refresh_token),
                'redirect_uri':REDIRECT}

    def authorization_url(self):
        if not self.client_id or not self.client_secret:
            raise ValueError('First configure Gmail OAuth credentials in Settings.')
        self.oauth_state=secrets.token_urlsafe(32)
        query=urllib.parse.urlencode({'client_id':self.client_id,'redirect_uri':REDIRECT,
          'response_type':'code','access_type':'offline','prompt':'consent',
          'scope':READ_SCOPE+((' '+SEND_SCOPE) if ENTERPRISE_MODE else ''),'state':self.oauth_state})
        return 'https://accounts.google.com/o/oauth2/v2/auth?'+query

    def post_token(self,data):
        req=urllib.request.Request('https://oauth2.googleapis.com/token',
          data=urllib.parse.urlencode(data).encode(),
          headers={'Content-Type':'application/x-www-form-urlencoded'},method='POST')
        return self.call(req)

    def call(self,req):
        try:
            with urllib.request.urlopen(req,timeout=22) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw=e.read(1000).decode('utf-8','replace')
            try: desc=json.loads(raw).get('error_description') or json.loads(raw).get('error',{}).get('message') or raw
            except (ValueError,AttributeError): desc=raw
            raise ValueError(f'Google API returned HTTP {e.code}: {desc}') from e
        except urllib.error.URLError as e:
            raise ValueError('Could not reach Google API. Check internet and firewall.') from e

    def callback(self,code,state):
        if not self.oauth_state or not secrets.compare_digest(str(state),self.oauth_state):
            raise ValueError('Login session expired or security state did not match. Try Connect again.')
        self.oauth_state=None
        d=self.post_token({'code':code,'client_id':self.client_id,
          'client_secret':self.client_secret,'redirect_uri':REDIRECT,'grant_type':'authorization_code'})
        self.access_token=d['access_token']; self.refresh_token=d.get('refresh_token')
        self.granted_scopes=set(d.get('scope','').split())
        self.expires_at=time.time()+int(d.get('expires_in',3500))-90
        profile=self.api('GET','/profile')
        self.account=profile.get('emailAddress','')
        return self.account

    def token(self):
        if self.access_token and time.time()<self.expires_at: return self.access_token
        if self.refresh_token:
            d=self.post_token({'client_id':self.client_id,'client_secret':self.client_secret,
                               'refresh_token':self.refresh_token,'grant_type':'refresh_token'})
            self.access_token=d['access_token'];self.expires_at=time.time()+int(d.get('expires_in',3500))-90
            return self.access_token
        raise ValueError('Gmail is not connected. Connect in Settings first.')

    def api(self,method,path,payload=None):
        url='https://gmail.googleapis.com/gmail/v1/users/me'+path
        body=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(url,data=body,method=method,headers={
            'Authorization':'Bearer '+self.token(), 'Content-Type':'application/json'})
        return self.call(req)

    def fetch_messages(self,limit=10):
        listing=self.api('GET','/messages?'+urllib.parse.urlencode({'maxResults':limit,'q':'in:inbox'}))
        out=[]
        for row in listing.get('messages',[]):
            msg=self.api('GET','/messages/'+urllib.parse.quote(row['id'])+'?format=full')
            headers={h['name'].lower():h['value'] for h in msg.get('payload',{}).get('headers',[])}
            sender_name,sender_address=parseaddr(headers.get('from',''))
            def text_part(p):
                if p.get('mimeType')=='text/plain' and p.get('body',{}).get('data'):
                    try:return base64.urlsafe_b64decode(p['body']['data']+'===').decode('utf-8','replace')
                    except ValueError:return ''
                for x in p.get('parts',[]):
                    val=text_part(x)
                    if val:return val
                return ''
            def attachment_info(payload):
                found=[]
                if payload.get('filename'):
                    found.append({'name':payload.get('filename','')[:140],
                     'mime_type':payload.get('mimeType',''),
                     'size':payload.get('body',{}).get('size',0)})
                for part in payload.get('parts',[]):
                    found.extend(attachment_info(part))
                return found[:20]
            out.append({'id':'G'+msg['id'], 'from_name':sender_name or sender_address or 'Gmail Sender',
               'from_email':sender_address,'subject':headers.get('subject','(No subject)'),
               'body':text_part(msg.get('payload',{})) or msg.get('snippet',''),
               'gmail_message_id':msg['id'],'thread_id':msg.get('threadId',''),
               'received_at':datetime.fromtimestamp(int(msg.get('internalDate',0))/1000,timezone.utc).isoformat() if msg.get('internalDate') else '',
               'attachments':attachment_info(msg.get('payload',{}))})
        return out

    def send(self,recipient,subject,body,thread_id=''):
        status=self.status()
        if not status['enterprise_mode']:
            raise ValueError('Launch RUN.bat in enterprise mode to use Gmail delivery.')
        if not status['delivery_requested']:
            raise ValueError('Enable Live Email Delivery in Settings before sending.')
        if not status['send_permission_granted']:
            raise ValueError('Gmail send permission is missing. Reconnect Gmail and grant the requested send permission.')
        if not status['connected']:
            raise ValueError('Connect your Google account before sending.')
        name,addr=parseaddr(recipient)
        if not addr or '@' not in addr or any(c in addr for c in '\r\n'):
            raise ValueError('Recipient email address is missing or invalid.')
        m=EmailMessage();m['To']=addr;m['Subject']='Re: '+subject.removeprefix('Re: ').replace('\r',' ').replace('\n',' ')
        m.set_content(body)
        encoded=base64.urlsafe_b64encode(m.as_bytes()).decode().rstrip('=')
        payload={'raw':encoded}
        if thread_id:payload['threadId']=thread_id
        result=self.api('POST','/messages/send',payload)
        if not result.get('id'):
            raise ValueError('Gmail did not accept the send request. Do not mark the message sent.')
        return result


gmail=GmailConnection()
