import base64
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
import server


class AccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();server.DB=Path(cls.temp.name)/'test.sqlite3';server.initialize()
        class PrivateHandler(server.Handler):
            site_password='test-only-a-unique-passphrase'
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),PrivateHandler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.temp.cleanup()

    def request(self,path,method='GET',authorization=None):
        headers={'Content-Type':'application/json'}
        if authorization:headers['Authorization']=authorization
        c=http.client.HTTPConnection('127.0.0.1',self.http.server_port)
        c.request(method,path,'{}' if method=='POST' else None,headers)
        r=c.getresponse();status,meta,body=r.status,dict(r.getheaders()),r.read();c.close()
        return status,meta,body

    def auth(self,user='para',password='test-only-a-unique-passphrase'):
        return 'Basic '+base64.b64encode((user+':'+password).encode()).decode()

    def test_protects_page_assets_and_api(self):
        with server.connect() as db:before=db.execute('SELECT count(*) FROM sessions').fetchone()[0]
        for path,method in [('/','GET'),('/app.js','GET'),('/style.css','GET'),('/report.js','GET'),('/api/questions','GET'),('/api/create','POST'),('/api/status','POST'),('/api/export','POST')]:
            status,headers,body=self.request(path,method)
            self.assertEqual(status,401,(path,method))
            self.assertIn('Basic',headers['WWW-Authenticate'])
            self.assertEqual(headers['Cache-Control'],'no-store')
            self.assertNotIn('test-only-a-unique-passphrase',body.decode())
        with server.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],before)

    def test_correct_credentials_open_both_page_and_api(self):
        self.assertEqual(self.request('/',authorization=self.auth())[0],200)
        self.assertEqual(self.request('/api/questions',authorization=self.auth())[0],200)
        status,_,body=self.request('/api/create','POST',self.auth())
        self.assertEqual(status,201);self.assertIn('token',json.loads(body))

    def test_wrong_and_malformed_credentials_fail_without_errors(self):
        for header in [self.auth(password='wrong'),self.auth(user='other'),'Bearer abc','Basic !@#$','Basic '+base64.b64encode(b'nocolon').decode(),'Basic '+base64.b64encode(b'\xff:\xff').decode()]:
            self.assertEqual(self.request('/',authorization=header)[0],401)

    def test_health_check_has_no_private_data_and_needs_no_password(self):
        status,_,body=self.request('/health')
        self.assertEqual(status,200);self.assertEqual(json.loads(body),{'ok':True})
