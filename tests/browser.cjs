const {chromium}=require('playwright');
const assert=(condition,message)=>{if(!condition)throw Error(message);};
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const base=process.env.TEST_BASE_URL||'http://127.0.0.1:8000';
  const ca=await browser.newContext(),cb=await browser.newContext();const a=await ca.newPage(),b=await cb.newPage();const errors=[];
  for(const p of [a,b])p.on('pageerror',e=>errors.push(e.message));
  await a.goto(base);await a.screenshot({path:'/tmp/couple-home-desktop.png',fullPage:true});
  const schema=await (await a.request.get(base+'/api/questions')).json();const qs=schema.topics.flatMap(t=>t.questions);
  assert(qs.length===50,'Expected 50 questions');await a.locator('#consent').check();await a.locator('#create').click();
  await a.locator('#invite').waitFor();const invite=await a.locator('#invite').inputValue();await b.goto(invite);
  for(const [i,p] of [[0,a],[1,b]]){
   await p.locator(`input[name="gender"][value="${i?'Он':'Она'}"]`).check();await p.locator('#name').fill(i?'Дима':'Алина');await p.locator('#sign').selectOption(i?'Лев':'Рак');await p.locator('#profile button[type=submit]').click();
   for(let n=0;n<50;n++){
    const q=qs[n],input=p.locator(`[data-n="${n}"]`);
    if(n===0){await p.locator(`input[data-skip="${n}"]`).check();await p.locator(`input[data-skip="${n}"]`).uncheck();}
    if(n===1){await p.locator('#back').click();assert((await p.locator('textarea').inputValue()).includes('Наш тестовый ответ'),'Back lost answer');await p.locator('#questions button[type=submit]').click();}
    if(q.type==='text')await input.fill('<img src=x onerror="window.injected=true"> Наш тестовый ответ.');
    else if(q.type==='number')await input.fill('0');
    else if(q.type==='bipolar')await input.filter({hasNot:p.locator('nonexistent')}).nth(n===20?(i?5:1):3).check();
    else if(q.type==='multi'){
     await input.first().check();
     if(n===10){await input.last().check();assert(!(await input.first().isChecked()),'Exclusive did not clear other choices');await input.first().check();assert(!(await input.last().isChecked()),'Normal choice did not clear exclusive');}
    }else await input.filter({hasNot:p.locator('nonexistent')}).nth(n>=45?(i?1:0):0).check();
    if(i===0&&[0,10,20,30].includes(n)){
     await p.setViewportSize({width:390,height:844});assert(!(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Question mobile overflow');await p.screenshot({path:`/tmp/couple-question-${n+1}.png`,fullPage:true});await p.setViewportSize({width:1280,height:900});
    }
    if(n===49)await p.locator('#submit-consent').check();
    await p.locator('#questions button[type=submit]').click();
   }
   if(i===0){await p.getByText('Ответы сохранены',{exact:true}).waitFor();assert(await p.locator('.private li').count()===5,'Private results should be available before partner submits');}
  }
  for(const p of [a,b])await p.locator('.hero .pill').filter({hasText:'Ваш совместный разбор'}).waitFor({timeout:12000});
  assert(await a.locator('.private li').count()===5,'Own safety missing');assert(await b.locator('.private li').count()===0,'Partner safety leaked');
  assert(await b.locator('.topic .comparison').count()===45,'Shared answer count');
  await b.locator('.topic summary').first().click();assert(await b.locator('img').count()===0&&!await b.evaluate(()=>Boolean(window.injected)),'Unescaped free text');
  await b.getByText('Рак + Лев',{exact:true}).waitFor();await b.getByText('Как вы видите себя в ссоре',{exact:true}).waitFor();
  assert(await b.locator('[data-report-section]').count()===16,'Expected all 16 open report sections');
  assert(await b.locator('.dimension-card').count()===12,'Expected 12 dimension cards');
  assert(await b.locator('.date-grid>.card').count()===5,'Expected 5 complete dates');
  assert(await b.locator('#part-15>.card').count()===6,'Expected 6 complete scenarios');
  assert(await b.locator('.nomination').count()===6,'Expected 6 nominations');
  assert(await b.locator('.risk-metric').count()===4,'Expected four explained risk fractions');
  assert(await b.locator('.pair-answers[data-alignment=same]').count()>0,'Missing match highlighting');
  assert(await b.locator('.pair-answers[data-alignment=different]').count()>0,'Missing difference highlighting');
  await b.getByText('Кто в паре абьюзер?',{exact:true}).waitFor();
  await b.emulateMedia({media:'print'});
  assert(await b.locator('#part-6').evaluate(el=>getComputedStyle(el).display)==='none','Private section should never print');
  await b.pdf({path:'/tmp/couple-full-report.pdf',format:'A4',printBackground:false});
  await b.emulateMedia({media:'screen'});
  assert(await b.locator('#part-6').isVisible(),'Private section not restored after print');
  await b.screenshot({path:'/tmp/couple-report-desktop.png',fullPage:false});
  await b.setViewportSize({width:390,height:844});assert(!(await b.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Report mobile overflow');await b.screenshot({path:'/tmp/couple-report-mobile.png',fullPage:false});
  await b.locator('#part-4').scrollIntoViewIfNeeded();
  await b.screenshot({path:'/tmp/couple-boundaries-mobile.png',fullPage:false});
  assert(!errors.length,errors.join('\n'));
  b.on('dialog',d=>d.accept());await b.locator('#delete').click();await b.locator('#create').waitFor();
  console.log('PASS: 16 full sections; percentages; colored answers; PDF excludes private safety; 100 answers across 8 input types; exclusive choices; back/skip/zero; names/gender; polling; private safety; report; horoscope; escaped text; mobile widths; deletion');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
