const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const assert=(value,message)=>{if(!value)throw Error(message);};
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const base=process.env.TEST_BASE_URL||'http://127.0.0.1:8000';
  const ca=await browser.newContext({acceptDownloads:true}),cb=await browser.newContext({acceptDownloads:true});
  const a=await ca.newPage(),b=await cb.newPage();let errors=[];for(const p of [a,b])p.on('pageerror',e=>errors.push(e.message));
  const post=async(path,data)=>{const r=await ca.request.post(base+'/api/'+path,{data});assert(r.ok(),path+': '+r.status());return r.json();};
  const schema=await (await ca.request.get(base+'/api/questions')).json();const qs=schema.topics.flatMap(t=>t.questions);
  const aa=qs.map(q=>q.type==='text'?'Строка 1.\nСтрока 2: «точный текст».':q.type==='number'?0:q.type==='bipolar'?4:q.type==='multi'?[q.options[0]]:q.flag?'Да':q.options[0]);
  aa[10]=['Времени вдвоём','Доверия'];aa[19]='__skip__';const bb=structuredClone(aa);for(let i=45;i<50;i++)bb[i]='Нет';
  const pair=await post('create',{});const authA={id:pair.id,token:pair.token},authB={id:pair.id,token:pair.invite};
  await post('submit',{...authA,answers:aa,profile:{gender:'Она',sign:'',name:'Участница'}});
  await a.goto(base+'/#'+new URLSearchParams(authA));await a.locator('[data-export=mine]').waitFor();
  const download=async(p,selector,path)=>{const pending=p.waitForEvent('download');await p.locator(selector).click();const d=await pending;await d.saveAs(path);return fs.readFile(path,'utf8');};
  const own=await download(a,'[data-export=mine]','/tmp/couple-own-answers.txt');
  assert(own.startsWith('\uFEFF'),'TXT should have UTF-8 BOM');assert((own.match(/Вопрос \d+\./g)||[]).length===50,'Expected all 50 own questions');
  assert(own.includes('Строка 1.\nСтрока 2: «точный текст».'),'Newlines or Unicode lost');assert(own.includes('ЛИЧНЫЙ ВОПРОС'),'Missing own private block');assert(!own.includes('Участник Б'),'Other profile leaked before completion');
  assert(await a.locator('[data-export=shared]').count()===0,'Shared export must not be offered before partner submits');
  await post('submit',{...authB,answers:bb,profile:{gender:'Он',sign:'',name:'Участник Б'}});
  await b.goto(base+'/#'+new URLSearchParams(authB));await b.locator('[data-export=shared][data-format=json]').waitFor();
  const raw=await download(b,'[data-export=shared][data-format=json]','/tmp/couple-shared-answers.json');const json=JSON.parse(raw);
  assert(json.questions.length===45,'Expected 45 shared questions');assert(json.participants.length===2,'Expected both participants');
  assert(json.questions[0].answers.a.value===aa[0],'Raw free text changed');assert(json.questions[18].answers.a.value===0,'Zero lost');
  assert(json.questions[19].answers.a.skipped&&json.questions[19].answers.a.value===null,'Skip lost');
  assert(json.questions[10].answers.a.value.length===2,'Multiple choices lost');
  assert(!json.questions.some(q=>q.private),'Private safety leaked to shared export');
  for(const secret of [pair.id,pair.token,pair.invite])assert(!raw.includes(secret),'Access token leaked');
  const text=await download(b,'[data-export=shared][data-format=txt]','/tmp/couple-shared-answers.txt');
  assert((text.match(/Вопрос \d+\./g)||[]).length===45,'Expected 45 shared questions in TXT');assert(!text.includes('ЛИЧНЫЙ ВОПРОС'),'Private questions in shared TXT');assert(text.includes('Москва'),'Missing readable export timezone');
  const other=await download(b,'[data-export=mine]','/tmp/couple-own-b-answers.txt');assert((other.match(/Вопрос \d+\./g)||[]).length===50,'Missing own B answers');assert(!other.includes('Участница'),'Other participant included in personal export');
  await b.setViewportSize({width:390,height:844});await b.locator('.downloads').scrollIntoViewIfNeeded();assert(!await b.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Mobile overflow');await b.screenshot({path:'/tmp/couple-downloads-mobile.png'});
  assert(!errors.length,errors.join('\n'));await post('delete',authA);
  console.log('PASS: real TXT/JSON downloads; all 50 personal / 45 paired questions; 90 shared answers; exact text, Unicode, newline, zero, multi and skip; no tokens; private isolation; mobile');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
