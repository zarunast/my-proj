const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const {randomBytes}=require('node:crypto');
const {mkdtemp,rm}=require('node:fs/promises');
const os=require('node:os');const path=require('node:path');
(async()=>{
 const password=randomBytes(24).toString('hex'),dir=await mkdtemp(path.join(os.tmpdir(),'couple-access-'));
 const port=process.env.TEST_ACCESS_PORT||'8123',base='http://127.0.0.1:'+port;
 const child=spawn('python3',['server.py'],{env:{...process.env,PORT:port,SITE_PASSWORD:password,DATA_DIR:dir},stdio:['ignore','ignore','ignore']});
 let browser;
 try{
  for(let i=0;i<60;i++){try{if((await fetch(base+'/health')).ok)break;}catch{}if(i===59)throw Error('Temporary server failed to start');await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
  const outsider=await browser.newContext();
  if((await outsider.request.get(base+'/')).status()!==401)throw Error('Anonymous homepage is accessible');
  if((await outsider.request.post(base+'/api/create',{data:{}})).status()!==401)throw Error('Anonymous API is accessible');
  const ca=await browser.newContext({httpCredentials:{username:'para',password}}),cb=await browser.newContext({httpCredentials:{username:'para',password}});
  const a=await ca.newPage(),b=await cb.newPage();
  await a.goto(base);await a.locator('#consent').check();await a.locator('#create').click();await a.locator('#invite').waitFor();
  const invitation=await a.locator('#invite').inputValue();await b.goto(invitation);
  await b.locator('#profile').waitFor();
  if(invitation.includes(password)||invitation.includes('para@'))throw Error('Site credential leaked in invitation');
  await b.locator('input[name=gender][value="Он"]').check();await b.locator('#profile button[type=submit]').click();await b.locator('#questions').waitFor();
  console.log('PASS: anonymous access blocked; two authenticated browsers; protected fetch/create/invitation flow; no password in invitation');
 }finally{if(browser)await browser.close();child.kill('SIGTERM');await new Promise(r=>child.exitCode!==null?r():child.once('exit',r));await rm(dir,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exit(1);});
