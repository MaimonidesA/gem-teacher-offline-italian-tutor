/* Live support-language regression, isolated profile on port 8769. */
const fs=require('fs'),assert=require('assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[],external=[],results=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1:8769')&&!r.url().startsWith('blob:'))external.push(r.url());});
 const ready=async()=>{await page.waitForFunction(()=>!state.busy&&state.session?.messages.length,{},{timeout:120000});assert.equal(await page.locator('.error-box').count(),0);};
 const capture=async()=>{const result=await page.evaluate(()=>state.lastResult);results.push(result);console.log(JSON.stringify({base:result.base,segments:result.segments,assessment:result.assessment}));};
 const change=async base=>{await page.locator('#support-language').selectOption(base);await page.waitForFunction(base=>!state.busy&&state.data.settings.base===base&&document.documentElement.lang===base,base);};
 await page.goto('http://127.0.0.1:8769');await page.getByRole('heading',{name:/on s’y met/}).waitFor();
 await page.evaluate(async()=>{await api('/api/settings',{auto_speak:false});await refresh();});
 await page.locator('.topic-card[data-topic="hello"]').click();await page.waitForFunction(()=>state.busy);await ready();
 const sid=await page.evaluate(()=>state.session.id),original=await page.locator('.message.assistant .bubble').first().evaluate(e=>[...e.querySelectorAll('.segment')].map(s=>[...s.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('')).join('|'));
 await page.locator('#chat-input').fill('Mi chiamo Luca.');await change('en');
 assert.equal(await page.locator('#chat-input').inputValue(),'Mi chiamo Luca.');assert.equal(await page.evaluate(()=>state.session.id),sid);assert.equal(await page.evaluate(()=>state.session.base),'en');
 assert.equal(await page.locator('[data-help="english"]').count(),0);assert.equal(await page.locator('[data-help="hint"]').innerText(),'A little hint');
 const after=await page.locator('.message.assistant .bubble').first().evaluate(e=>[...e.querySelectorAll('.segment')].map(s=>[...s.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('')).join('|'));assert.equal(after,original);
 await page.locator('[data-help="hint"]').click();await page.waitForFunction(()=>state.busy);await ready();await capture();assert(results.at(-1).segments.some(s=>s.language==='en'));
 await page.locator('#chat-input').fill('Io sono 30 anni e vivo a Roma.');await page.locator('#chat-input').press('Enter');await page.waitForFunction(()=>state.busy);await ready();await capture();
 assert(results.at(-1).assessment.rating<5);assert(/age|have|use|verb/i.test(results.at(-1).assessment.explanation));assert.equal(results.at(-1).base,'en');
 fs.mkdirSync('artifacts',{recursive:true});await page.waitForFunction(()=>{const m=document.querySelector('#messages');return m.scrollTop>=m.scrollHeight-m.clientHeight-3;});await page.screenshot({path:'artifacts/english-support-desktop.png',fullPage:true,animations:'disabled'});
 await page.setViewportSize({width:360,height:800});await page.screenshot({path:'artifacts/english-support-mobile.png',fullPage:true,animations:'disabled'});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await change('fr');assert.equal(await page.locator('[data-help="hint"]').innerText(),'Un petit indice');assert(await page.locator('[data-help="english"]').isVisible());
 await page.locator('[data-help="english"]').click();await page.waitForFunction(()=>state.busy);await ready();await capture();assert(results.at(-1).segments.some(s=>s.language==='en'));assert.equal(await page.evaluate(()=>state.data.settings.base),'fr');
 await page.locator('[data-help="hint"]').click();await page.waitForFunction(()=>state.busy);await ready();await capture();assert(results.at(-1).segments.some(s=>s.language==='fr'));
 // The original preferences control must also update the existing chat.
 await page.locator('.sidebar [data-view="settings"]:visible').click();await page.locator('#base').selectOption('en');await page.locator('#settings-form button[type="submit"]').click();await page.waitForFunction(()=>state.data.settings.base==='en');
 await page.locator('.sidebar [data-view="conversation"]').click();assert.equal(await page.evaluate(()=>state.session.id),sid);assert.equal(await page.evaluate(()=>state.session.base),'en');assert.equal(await page.locator('[data-help="hint"]').innerText(),'A little hint');
 await page.reload();await page.waitForFunction(()=>state.data?.settings.base==='en');await page.locator('.sidebar [data-view="conversation"]').click();assert.equal(await page.evaluate(()=>state.session.base),'en');assert.equal(await page.locator('[data-help="english"]').count(),0);
 await page.locator('.sidebar [data-view="coffee"]').click();await page.locator('#coffee-subject').fill('The mathematics book I am reading');await page.locator('#coffee-form button[type="submit"]').click();await page.waitForFunction(()=>state.busy);await ready();
 const coffee=await page.evaluate(()=>state.session.id);assert.equal(await page.evaluate(()=>state.session.base),'en');await change('fr');assert.equal(await page.evaluate(()=>state.session.id),coffee);assert.equal(await page.evaluate(()=>state.session.base),'fr');assert(await page.locator('[data-help="english"]').isVisible());
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);fs.writeFileSync('artifacts/support-language-validation.json',JSON.stringify({passed:true,results,errors,external},null,2));console.log(JSON.stringify({passed:true,errors,external}));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
