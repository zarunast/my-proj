import unittest
import server
from test_server import answers, profiles


class FullReportTest(unittest.TestCase):
    def report(self,a=None,b=None,role='a'):
        return server.analyze(answers() if a is None else a,answers() if b is None else b,role,profiles())['full']

    def test_every_extended_section_has_content_and_traceable_sources(self):
        report=self.report()
        self.assertEqual(len(report['dimensions']),12)
        self.assertEqual(len(report['axes']),10)
        self.assertEqual(len(report['boundaries']['items']),10)
        self.assertEqual(len(report['dates']),5)
        self.assertEqual(len(report['scenarios']),6)
        self.assertEqual(len(report['nominations']),6)
        for date in report['dates']:
            for key in ('together','remote','question','check','basis'):
                self.assertTrue(date[key])
        for scenario in report['scenarios']:
            self.assertTrue(scenario['step']);self.assertTrue(scenario['prompt'])
            self.assertTrue(all(1<=v['source']<=45 for v in scenario['evidence']))
        self.assertTrue(all(1<=v['source']<=45 for d in report['dimensions'] for v in d['evidence']))

    def test_percentages_are_observed_fractions_not_predictions(self):
        a,b=answers(),answers();a[20]=1;b[20]=7
        a[30]='Мне ок';b[30]='Мне не ок';a[31]='Зависит от ситуации';a[40]='Нет'
        report=self.report(a,b)
        metrics=report['risk_indicators']
        self.assertEqual((metrics[1]['count'],metrics[1]['total'],metrics[1]['percent']),(1,10,10))
        self.assertEqual((metrics[2]['count'],metrics[2]['total'],metrics[2]['percent']),(1,9,11))
        self.assertEqual((metrics[3]['count'],metrics[3]['total'],metrics[3]['percent']),(1,10,10))
        for metric in metrics:
            self.assertEqual(metric['percent'],round(metric['count']/metric['total']*100))
        self.assertNotIn('breakup_probability',report)

    def test_all_skips_remain_unknown_not_zero_risk_or_fake_strength(self):
        report=self.report([server.SKIP]*50,[server.SKIP]*50)
        self.assertTrue(all(v['percent'] is None and v['total']==0 for v in report['risk_indicators']))
        self.assertEqual(report['boundaries']['total'],0)
        self.assertEqual(report['strengths'],[]);self.assertEqual(report['weaknesses'],[])
        self.assertTrue(all(v['winner'] is None for v in report['nominations']))
        self.assertTrue(all(v['total']==0 for v in report['dimensions']))
        self.assertIn('не хватает',report['portrait']['description'])

    def test_private_answers_do_not_change_any_public_section(self):
        a,b=answers(),answers();baseline=self.report(a,b)
        a[-5:]=['Да']*5;b[-5:]=['Не хочу отвечать']*5
        self.assertEqual(self.report(a,b),baseline)
        self.assertEqual(self.report(a,b,'b'),baseline)
        self.assertEqual(len(server.analyze(a,b,'a',profiles())['private_safety']['flags']),5)
        self.assertEqual(server.analyze(a,b,'b',profiles())['private_safety']['flags'],[])

    def test_public_concerns_are_attributed_to_the_right_person(self):
        a,b=answers(),answers()
        a[16]=['Повышает голос'];b[15]=['Повышает голос'];a[15]=['Предлагает поговорить'];b[16]=['Предлагает поговорить']
        a[34]='Мне ок';b[34]='Мне не ок'
        report=self.report(a,b)
        self.assertEqual(len(report['flagometer']['a']['concerns']),2)
        self.assertEqual(report['flagometer']['b']['concerns'],[])
        self.assertIn('обоими',report['flagometer']['a']['concerns'][0]['basis'])
        self.assertIn('не доказывает',report['flagometer']['a']['concerns'][1]['basis'])
        for nomination in report['nominations']:
            self.assertEqual(nomination['winner'],'both')

    def test_priority_does_not_ignore_refusal_or_major_life_choice(self):
        a,b=answers(),answers();a[21]=1;b[21]=7
        self.assertEqual(self.report(a,b)['conversation']['title'],'Ваши взгляды на детей')
        a[40]='Нет'
        self.assertEqual(self.report(a,b)['conversation']['title'],'Уважение отказа и возможность быть собой')
        a=[server.SKIP]*50;b=[server.SKIP]*50
        self.assertEqual(self.report(a,b)['conversation']['title'],'Чего вам хочется больше')
