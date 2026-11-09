import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
import server


def answers():
    result=[]
    for q in server.QUESTIONS:
        kind=q['type']
        result.append('Короткий пример ответа.' if kind=='text' else [q['options'][0]] if kind=='multi' else 3 if kind=='bipolar' else 0 if kind=='number' else 'Нет' if 'flag' in q else q['options'][0])
    return result


def profiles():
    return {'a':dict(gender='Она',sign='Рак',name='Луна'),'b':dict(gender='Он',sign='Лев',name='Солнце')}


class FlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();server.DB=Path(cls.temp.name)/'test.sqlite3';server.initialize()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.temp.cleanup()

    def request(self,path,data=None):
        c=http.client.HTTPConnection('127.0.0.1',self.http.server_port)
        c.request('POST' if data is not None else 'GET',path,json.dumps(data) if data is not None else None,{'Content-Type':'application/json'})
        r=c.getresponse();status,body=r.status,r.read();c.close();return status,json.loads(body)

    def test_two_participants_and_private_flags(self):
        status,pair=self.request('/api/create',{});self.assertEqual(status,201)
        a=dict(id=pair['id'],token=pair['token']);b=dict(id=pair['id'],token=pair['invite'])
        aa=answers();aa[-1]='Да';aa[0]='<script>alert(1)</script>'
        self.assertEqual(self.request('/api/status',dict(a,token='bad'))[0],404)
        self.assertEqual(self.request('/api/submit',dict(a,answers=aa))[0],400)
        status,waiting=self.request('/api/submit',dict(a,answers=aa,profile=profiles()['a']))
        self.assertEqual(status,200);self.assertFalse(waiting['ready']);self.assertEqual(len(waiting['private_safety']['flags']),1)
        other=self.request('/api/status',b)[1];self.assertNotIn('private_safety',other);self.assertNotIn('analysis',other)
        self.assertEqual(self.request('/api/submit',dict(a,answers=aa,profile=profiles()['a']))[0],409)
        status,rb=self.request('/api/submit',dict(b,answers=answers(),profile=profiles()['b']))
        self.assertEqual(status,200);self.assertTrue(rb['ready'])
        ra=self.request('/api/status',a)[1];self.assertEqual(ra['analysis']['topics'],rb['analysis']['topics'])
        self.assertEqual(len(ra['analysis']['topics']),9)
        self.assertEqual(rb['analysis']['profiles']['a']['name'],'Луна')
        self.assertEqual(rb['analysis']['private_safety']['flags'],[])
        self.assertEqual(len(ra['analysis']['private_safety']['flags']),1)
        self.assertEqual(sum(len(t['comparisons']) for t in rb['analysis']['topics']),45)
        self.assertNotIn('Физическая агрессия',json.dumps(rb,ensure_ascii=False))
        self.assertEqual(rb['analysis']['topics'][0]['comparisons'][0]['a'],aa[0])
        self.assertEqual(self.request('/api/delete',b)[0],200)
        self.assertEqual(self.request('/api/status',a)[0],404)

    def test_exports_preserve_all_answers_and_isolate_private_data(self):
        _,pair=self.request('/api/create',{})
        a=dict(id=pair['id'],token=pair['token']);b=dict(id=pair['id'],token=pair['invite'])
        self.assertEqual(self.request('/api/export',dict(a,scope='mine'))[0],409)
        aa,bb=answers(),answers();aa[0]='Точный текст.\nВторая строка: «привет».';aa[10]=['Времени вдвоём','Доверия'];aa[19]=server.SKIP;aa[-5:]=['Да']*5
        self.assertEqual(self.request('/api/submit',dict(a,answers=aa,profile=profiles()['a']))[0],200)
        status,mine=self.request('/api/export',dict(a,scope='mine'))
        self.assertEqual(status,200);self.assertEqual(len(mine['questions']),50)
        self.assertEqual([p['role'] for p in mine['participants']],['a'])
        self.assertEqual(mine['questions'][0]['answers']['a']['value'],aa[0])
        self.assertEqual(mine['questions'][10]['answers']['a']['value'],aa[10])
        self.assertEqual(mine['questions'][18]['answers']['a']['value'],0)
        self.assertEqual(mine['questions'][19]['answers']['a'],dict(value=None,skipped=True))
        self.assertTrue(all(q['private'] for q in mine['questions'][-5:]))
        self.assertEqual(self.request('/api/export',dict(a,scope='shared'))[0],409)
        self.assertEqual(self.request('/api/export',dict(b,scope='mine'))[0],409)
        self.assertEqual(self.request('/api/submit',dict(b,answers=bb,profile=profiles()['b']))[0],200)
        _,shared=self.request('/api/export',dict(a,scope='shared'))
        self.assertEqual(len(shared['questions']),45)
        self.assertFalse(any(q['private'] for q in shared['questions']))
        for i,q in enumerate(shared['questions']):
            self.assertEqual(q['number'],i+1)
            self.assertEqual(q['question'],server.QUESTIONS[i]['text'])
            self.assertEqual(set(q['answers']),{'a','b'})
            self.assertEqual(q['answers']['a']['value'],None if aa[i]==server.SKIP else aa[i])
            self.assertEqual(q['answers']['b']['value'],bb[i])
        _,other_mine=self.request('/api/export',dict(b,scope='mine'))
        self.assertEqual([p['role'] for p in other_mine['participants']],['b'])
        self.assertTrue(all(q['answers']['b']['value']=='Нет' for q in other_mine['questions'][-5:]))
        wire=json.dumps(shared,ensure_ascii=False)
        self.assertNotIn(pair['token'],wire);self.assertNotIn(pair['invite'],wire);self.assertNotIn(pair['id'],wire)
        self.assertEqual(self.request('/api/export',dict(a,scope='all'))[0],400)
        self.assertEqual(self.request('/api/export',dict(a,token='bad',scope='mine'))[0],404)
        self.request('/api/delete',a)
        self.assertEqual(self.request('/api/export',dict(b,scope='mine'))[0],404)

    def test_validation(self):
        self.assertTrue(server.valid_answers(answers()));self.assertTrue(server.valid_answers([server.SKIP]*50))
        invalid=[(0,''),(0,'x'*1501),(0,{}),(10,[]),(10,['Unknown']),(10,[{},'Времени вдвоём']),(10,['Времени вдвоём']*2),(10,['Времени вдвоём','Меня всё устраивает']),(15,['Мы почти не ссоримся','Предлагает поговорить']),(18,True),(18,15),(18,-1),(20,0),(20,8),(20,3.5),(20,True),(30,'wrong')]
        for i,value in invalid:
            aa=answers();aa[i]=value;self.assertFalse(server.valid_answers(aa),(i,value))
        self.assertFalse(server.valid_answers([1]*18));self.assertFalse(server.valid_answers(None))

    def test_perspective_and_conflict_mirror(self):
        a,b=answers(),answers();a[17]='Я';b[17]='Партнёр'
        self.assertTrue(server.analyze(a,b,'a',profiles())['topics'][3]['comparisons'][2]['alignment'])
        b[17]='Я';self.assertFalse(server.analyze(a,b,'a',profiles())['topics'][3]['comparisons'][2]['alignment'])
        a[16]=['Берёт паузу и возвращается к разговору'];b[15]=a[16][:]
        a[15]=['Предлагает поговорить'];b[16]=['Повышает голос']
        mirror=server.analyze(a,b,'a',profiles())['conflict_mirror']
        self.assertEqual(mirror['a']['common'],a[16]);self.assertEqual(mirror['b']['common'],[])

    def test_analysis_boundaries_and_plan(self):
        a,b=answers(),answers();a[10]=['Времени вдвоём','Доверия'];b[10]=['Доверия']
        a[20]=1;b[20]=7;a[21]=3;b[21]=4
        a[40]='Нет';b[41]='Нет'
        result=server.analyze(a,b,'a',profiles());s=result['summary']
        self.assertEqual(s['common_wishes'],['Доверия']);self.assertEqual(len(s['differences']),1)
        self.assertEqual(s['differences'][0]['gap'],6)
        self.assertEqual(len(s['green']),3);self.assertEqual(len(s['needs']),2)
        self.assertIn('обещание',s['plan'][0])
        self.assertNotIn(server.QUESTIONS[40]['green'],result['angels']['b'])
        self.assertNotIn(server.QUESTIONS[41]['green'],result['angels']['a'])
        self.assertTrue(result['topics'][4]['comparisons'][1]['alignment'])

    def test_skips_and_uncertainty_do_not_become_scores(self):
        a,b=[server.SKIP]*50,[server.SKIP]*50
        result=server.analyze(a,b,'a',profiles())
        self.assertEqual(result['summary']['comparable'],0);self.assertEqual(result['summary']['aligned'],0)
        self.assertEqual(result['summary']['green'],[]);self.assertEqual(result['private_safety']['answered'],0)
        self.assertEqual(result['angels'],{'a':[],'b':[]});self.assertEqual(result['quotes'],[])
        a,b=answers(),answers();a[30]='Зависит от ситуации';a[40]='Не знаю'
        result=server.analyze(a,b,'a',profiles())
        self.assertIsNone(result['topics'][6]['comparisons'][0]['alignment'])
        self.assertIsNone(result['topics'][8]['comparisons'][0]['alignment'])

    def test_horoscope_does_not_change_analysis(self):
        p=profiles();one=server.analyze(answers(),answers(),'a',p)['summary']
        p['a']['sign']='';p['b']['sign']='Телец'
        self.assertEqual(one,server.analyze(answers(),answers(),'a',p)['summary'])

    def test_expiry_and_old_version(self):
        _,pair=self.request('/api/create',{});auth=dict(id=pair['id'],token=pair['token'])
        with server.connect() as db:db.execute('UPDATE sessions SET version=4 WHERE id=?',(pair['id'],))
        self.assertEqual(self.request('/api/status',auth)[0],409);self.assertEqual(self.request('/api/delete',auth)[0],200)
        _,pair=self.request('/api/create',{});auth=dict(id=pair['id'],token=pair['token'])
        with server.connect() as db:db.execute('UPDATE sessions SET created=0 WHERE id=?',(pair['id'],))
        self.assertEqual(self.request('/api/status',auth)[0],404)

    def test_questions_and_health(self):
        self.assertEqual(self.request('/health'),(200,{'ok':True}))
        status,body=self.request('/api/questions');self.assertEqual(status,200)
        self.assertEqual(sum(len(t['questions']) for t in body['topics']),50)
        self.assertEqual({q['type'] for t in body['topics'] for q in t['questions']},{'yesno','number','when','who','text','multi','bipolar','norm'})
