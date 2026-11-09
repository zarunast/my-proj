"""Full report built only from the 45 shared answers; no external services."""


def build_report(a, b, questions, comparisons, summary):
    assert len(a) == len(b) == len(questions) == len(comparisons) == 45
    skip = '__skip__'

    def values(index):
        return dict(question=questions[index]['text'], a=a[index], b=b[index], source=index+1)

    def chosen(answers, index):
        return answers[index] if isinstance(answers[index], list) else []

    def scale(index):
        item = comparisons[index]
        filled = type(a[index]) is int and type(b[index]) is int
        return dict(**values(index), left=questions[index]['left'], right=questions[index]['right'], gap=abs(a[index]-b[index]) if filled else None,
                    note=item['note'])

    # Portrait titles are playful summaries of explicit choices, not personality diagnoses.
    rest = [v for v in (a[22], b[22]) if type(v) is int]
    if len(rest) < 2:
        portrait_title = 'Ваша история ещё пишется'
        portrait = 'Для игрового портрета не хватает двух ответов о любимом отдыхе. Открытые ответы ниже расскажут о вас больше любого ярлыка.'
    elif max(rest) <= 3:
        portrait_title = 'Команда уютных вечеров'
        portrait = 'В вопросе об отдыхе вы оба ближе к спокойному варианту. Это общая предпочтительная атмосфера, а не описание всего вашего характера.'
    elif min(rest) >= 5:
        portrait_title = 'Искатели новых впечатлений'
        portrait = 'Вы оба ближе к активному отдыху. Можно использовать это совпадение, выбирая новое занятие вдвоём.'
    else:
        portrait_title = 'Два ритма — один маршрут'
        portrait = 'Ваши ответы об отдыхе не попали в одну из двух крайних групп. Уточните, сколько уюта и приключений хочется каждому.'

    strengths = [dict(title=x, reason='Оба отметили этот пункт в списке того, что уже получается.', sources=[12]) for x in summary['common_strengths']]
    strengths += [dict(title=q['green'], reason='Оба ответили «Да» на вопрос «'+q['text']+'».', sources=[i+1]) for i,q in enumerate(questions) if 'green' in q and a[i] == b[i] == 'Да']
    weaknesses = [dict(title=q, reason='Хотя бы один участник ответил «Нет». Это область потребности, а не обвинение.', sources=[i+1]) for i,q in enumerate([item['text'] for item in questions]) if i >= 40 and 'Нет' in (a[i],b[i])]
    weaknesses += [dict(title=c['question'], reason='Разница по шкале: '+str(c['gap'])+' из 6 возможных шагов. Обсудите важность этого различия.', sources=[i+1]) for i,c in enumerate(comparisons) if c['type']=='bipolar' and c.get('gap',0)>=3]
    selected_disputes = [v for v in questions[12]['options'] if v != 'Почти не спорим' and (v in chosen(a,12) or v in chosen(b,12))]
    shared_disputes = [v for v in selected_disputes if v in chosen(a,12) and v in chosen(b,12)]

    axes = [scale(i) for i in range(20,30)]
    dimensions = []
    definitions = [
        ('Темп жизни',[20,23]), ('Планы и дети',[21,28]), ('Деньги и общий быт',[24,38,39]),
        ('Личное время',[25,32]), ('Разговоры о близости',[27]), ('Границы и приватность',[30,31,34,35]),
        ('Поддержка',[26,41]), ('Примирение',[17,29,42]), ('Время и внимание',[18,19,44]),
        ('Свобода самовыражения',[33,37,43]), ('Согласие и уважение',[36,40]), ('Общий отдых',[22]),
    ]
    for label, indexes in definitions:
        evidence = [dict(**values(i), note=comparisons[i]['note'], alignment=comparisons[i]['alignment']) for i in indexes]
        known = [c for c in evidence if c['alignment'] is not None]
        dimensions.append(dict(title=label, aligned=sum(c['alignment'] for c in known), total=len(known), evidence=evidence))

    boundaries = [dict(**values(i), note=comparisons[i]['note'], alignment=comparisons[i]['alignment']) for i in range(30,40)]
    known_boundaries = [c for c in boundaries if c['alignment'] is not None]
    boundary_report = dict(aligned=sum(c['alignment'] for c in known_boundaries), total=len(known_boundaries), uncertain=len(boundaries)-len(known_boundaries), items=boundaries)

    # Public flagometer never receives safety answers. A concern is a reported behavior/attitude, not a diagnosis.
    flagometer = {}
    for target, partner in [('a', b), ('b', a)]:
        own = a if target == 'a' else b
        good = [dict(title=q['green'], source=i+1, basis='Отмечено партнёром в ответе о вашем взаимодействии.') for i,q in enumerate(questions) if 'green' in q and partner[i]=='Да']
        concerns = []
        for behavior in ('Повышает голос','Долго доказывает свою правоту'):
            self_report = behavior in chosen(own,16)
            partner_report = behavior in chosen(partner,15)
            if self_report or partner_report:
                concerns.append(dict(title=behavior, source=17 if self_report else 16, basis='Отмечено обоими: в самоотчёте и описании партнёра.' if self_report and partner_report else 'Отмечено только в самоотчёте.' if self_report else 'Отмечено только партнёром; это его или её восприятие.'))
        if own[34]=='Мне ок':
            concerns.append(dict(title='Допускает просмотр телефона без разрешения', source=35, basis='Собственный ответ о допустимости. Он не доказывает, что человек так поступал. Просмотр без согласия нарушает приватность.'))
        flagometer[target] = dict(green=good, concerns=concerns)

    nominations = []
    for label,index,direction in [('Хранитель уютных вечеров',22,'low'),('Разведчик новых впечатлений',20,'high'),('Режиссёр планов',23,'high'),('Защитник заначки',24,'low'),('Хранитель личного времени',25,'high'),('Давайте поговорим сейчас',29,'low')]:
        x,y=a[index],b[index]
        winner = None
        if type(x) is int and type(y) is int:
            winner = 'both' if x==y else 'a' if (x<y if direction=='low' else x>y) else 'b'
        nominations.append(dict(title=label, winner=winner, **scale(index)))

    # Most important discussion is selected transparently, without forecasting a breakup.
    if any('Нет' in (a[i],b[i]) for i in (40,43)):
        focus_indexes=[i for i in (40,43) if 'Нет' in (a[i],b[i])]
        focus_title='Уважение отказа и возможность быть собой'
        prompt='Что нужно изменить, чтобы можно было спокойно говорить «нет» и оставаться собой?'
    elif type(a[21]) is int and type(b[21]) is int and abs(a[21]-b[21])>=3:
        focus_indexes=[21];focus_title='Ваши взгляды на детей';prompt='Как каждый видит своё будущее и есть ли здесь решение, на которое оба согласны без давления?'
    elif summary['differences']:
        focus_indexes=[i for i in range(20,30) if type(a[i]) is int and type(b[i]) is int and abs(a[i]-b[i])>=3]
        focus_indexes=sorted(focus_indexes,key=lambda i:abs(a[i]-b[i]),reverse=True)[:1]
        focus_title=questions[focus_indexes[0]]['text'];prompt='Что для тебя важно в этом выборе и что ты готов(а) обсуждать, а что для тебя принципиально?'
    elif summary['needs']:
        focus_indexes=[i for i in range(40,45) if 'Нет' in (a[i],b[i])][:1]
        focus_title=questions[focus_indexes[0]]['text'];prompt='Вспомни один недавний пример. Чего не хватило и о каком конкретном действии хочется попросить?'
    elif selected_disputes:
        focus_indexes=[12];focus_title='Ваши повторяющиеся споры';prompt='Какую одну спорную тему можно обсудить без требования решить все проблемы сразу?'
    else:
        focus_indexes=[10];focus_title='Чего вам хочется больше';prompt='Что сделало бы ближайшую неделю приятнее для каждого из вас?'
    conversation=dict(title=focus_title,prompt=prompt,evidence=[values(i) for i in focus_indexes],
        steps=['Выберите время, когда никто не спешит. Спросите, готов ли второй к разговору.',
               'По пять минут каждому: один пример, свои чувства и одна просьба. Второй пересказывает услышанное.',
               'Запишите одну добровольную договорённость: что вы делаете, когда и как поймёте, что стало лучше.',
               'Через неделю проверьте результат. Если разговор превращается в давление — остановитесь; при страхе нужна личная поддержка, а не упражнение вдвоём.'],
        tonight='За 20 минут назовите по одной вещи, которую цените, и одной просьбе на неделю. Не спорьте с чувствами друг друга; согласуйте только один небольшой шаг.')

    def shared(index):
        return [v for v in chosen(a,index) if v in chosen(b,index)]
    def basis_for(item, fallback):
        return 'Оба отметили: «'+item+'».' if item in shared(10) else fallback

    dates=[
        dict(title='Вечер без параллельных дел',duration='30 минут',basis=basis_for('Времени вдвоём','Общий вариант для спокойного общения; это предложение, а не вывод о нехватке внимания.'),
             together='Уберите уведомления. По очереди расскажите про один хороший и один трудный момент недели.',remote='Созвонитесь с чаем или ужином. На эти полчаса закройте другие вкладки.',question='В какой момент этого вечера ты почувствовал(а), что тебя слушают?',check='Каждый смог договорить; никто не обязан раскрывать то, чем не готов делиться.'),
        dict(title='Свидание по очереди',duration='45–60 минут',basis=basis_for('Свиданий и романтики','Способ попробовать предпочтения друг друга, не требуя одинаковых вкусов.'),
             together='Один выбирает прогулку или недорогое занятие в заранее согласованном бюджете. В следующий раз меняетесь.',remote='Один выбирает виртуальную прогулку, игру или фильм. Обсудите выбор до начала.',question='Что из моего выбора тебе понравилось, а что хотелось бы иначе?',check='Идея и бюджет подходят обоим; от неподходящего занятия можно отказаться.'),
        dict(title='Два слушателя',duration='20 минут',basis=basis_for('Спокойных разговоров','Подходит для прояснения разных ответов. Используйте только если обоим безопасно разговаривать.'),
             together='По пять минут расскажите о небольшой потребности. Второй сначала пересказывает, потом уточняет.',remote='То же по аудио или видео. Если связь мешает, обменяйтесь короткими голосовыми.',question='Я правильно понял(а), что тебе сейчас важно…?',check='Каждый подтверждает, что его поняли, без обязанности согласиться со всем.'),
        dict(title='Небольшое совместное приключение',duration='40 минут',basis=basis_for('Веселья и новых впечатлений','Можно выбрать новый опыт без больших расходов и обязательств.'),
             together='Приготовьте новое блюдо или сходите по незнакомому маршруту. Каждый может предложить более спокойный вариант.',remote='Готовьте одно блюдо по видеосвязи или сыграйте в совместную игру.',question='Что мы хотели бы попробовать ещё раз?',check='Оба выбрали занятие добровольно; развлечение не превращается в соревнование.'),
        dict(title='Забота без угадывания',duration='25 минут',basis=basis_for('Помощи и благодарности','Проясняет способы заботы. Ответы о поддержке можно сопоставить в зелёных флагах.'),
             together='Каждый называет одну приятную форму заботы. Объятия — только если оба хотят, разговор или помощь тоже подходят.',remote='Спросите про одну посильную помощь на расстоянии: выслушать, напомнить, вместе составить план.',question='Что помогло бы тебе почувствовать поддержку на этой неделе?',check='Выбрано одно посильное действие, а не обещание исправить все чувства другого.'),
    ]

    scenarios=[]
    definitions=[
      ('Выходные наедине','Вы остаётесь вдвоём на два дня без привычных дел.',[22,25], 'Как разделить совместные занятия и время на себя?', 'По очереди выберите по одному общему занятию и отдельному часу. Личное время не требует оправдания.'),
      ('Неожиданный расход','Появилась общая трата, на которую вы не рассчитывали.',[24,38], 'Какую сумму нужно обсуждать заранее и кто за что отвечает?', 'Назовите доступный бюджет и обязательные расходы. Договоритесь без финансового давления.'),
      ('Поездка пошла не по плану','Отменили транспорт или закрыли место, куда вы собирались.',[20,23], 'Кому нужен план Б, а кому проще импровизировать?', 'Сначала решите практическую задачу. Потом обсудите эмоции без поиска виноватого.'),
      ('Вечер с друзьями','Один идёт к друзьям, другой остаётся дома.',[30,35], 'О чём договориться для спокойствия, сохраняя право на личную жизнь?', 'Согласуйте удобный способ связи. Геолокация и пароли не должны становиться обязательным доказательством любви.'),
      ('Месяц на расстоянии','Вы не сможете встретиться ближайший месяц.',[18,25,44], 'Какой ритм звонков реалистичен для обоих?', 'Согласуйте несколько окон для связи и право предупредить о занятости без наказания молчанием.'),
      ('Ссора поздно вечером','Один хочет разобраться сейчас, другой устал и хочет спать.',[29,36], 'Как обозначить паузу так, чтобы это не выглядело исчезновением?', 'Договоритесь о времени возвращения к разговору. Не лишайте друг друга сна ради обязательного примирения.'),
    ]
    for title,scene,indexes,prompt,step in definitions:
        scenarios.append(dict(title=title,scene=scene,prompt=prompt,step=step,evidence=[values(i) for i in indexes],verdict='Сценарий для обсуждения, не прогноз. Разные ответы требуют договорённости; по ним нельзя предсказать, как вы поведёте себя.'))

    chemistry=dict(openness=scale(27),wishes=dict(a=chosen(a,10),b=chosen(b,10)),
       conversation='Выберите спокойный момент и спросите, как каждому удобнее говорить о желаниях. Одинаковая оценка не означает одинаковых желаний или согласия на контакт.',
       fidelity='В этом тесте нет прямого вопроса о ваших договорённостях о верности. Оценить верность, вероятность измены или частоту желаемого секса по этим ответам нельзя. Спросите друг друга, что вы считаете нарушением договорённостей, и обозначьте свои границы без давления.')

    def ratio(title, count, total, basis):
        return dict(title=title, count=count, total=total, percent=round(count/total*100) if total else None, basis=basis)

    known = [c for c in comparisons if c['alignment'] is not None]
    known_axes = [c for c in axes if c['gap'] is not None]
    defined_green = [v for row in (a,b) for v in row[40:45] if v in ('Да','Нет')]
    risk_indicators = [
        ratio('Различия в сопоставимых ответах', sum(not c['alignment'] for c in known), len(known), 'Доля разных закрытых ответов. На шкалах разница больше 1 считается различием.'),
        ratio('Заметные различия в ожиданиях', sum(c['gap']>=3 for c in known_axes), len(known_axes), 'Доля заполненных обоими шкал с разницей от 3 шагов из 6 возможных.'),
        ratio('Различия во взглядах на границы', sum(not c['alignment'] for c in known_boundaries), len(known_boundaries), 'Доля разных определённых ответов в десяти ситуациях о границах.'),
        ratio('Ответы о нехватке важного', sum(v=='Нет' for v in defined_green), len(defined_green), 'Доля ответов «Нет» среди ответов «Да/Нет» в пяти вопросах о зелёных флагах у обоих участников.'),
    ]
    return dict(portrait=dict(title=portrait_title,description=portrait,evidence=scale(22)),
       title='Экипаж вашего собственного маршрута',risk_indicators=risk_indicators,dimensions=dimensions,boundaries=boundary_report,flagometer=flagometer,nominations=nominations,
       axes=axes,conversation=conversation,strengths=strengths[:3],weaknesses=weaknesses[:3],disputes=dict(shared=shared_disputes,all=selected_disputes,evidence=values(12)),
       annoyances=[values(5),values(6)],requests=[values(7),values(8)],love=[values(i) for i in (0,1,3,4)],chemistry=chemistry,dates=dates,scenarios=scenarios,
       finale=dict(film=values(9),message='У ваших отношений нет финала, который тест может предсказать. Сохраните то, что оба цените, выберите один разговор и один посильный шаг. Решение о будущем принадлежит вам, а не отчёту.',
                   meme='Мы: «Не будем читать мысли». Тоже мы: открываем 50 вопросов, чтобы наконец спросить словами.'),
       scope='Самостоятельный открытый отчёт по вашим ответам. Скрытые тексты другого сервиса не извлекались и не восстанавливались. Вероятности расставания, диагнозы, сила любви и верность не рассчитываются.')
