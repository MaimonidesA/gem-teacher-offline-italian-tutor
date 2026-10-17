/* Run against an isolated test instance on 8772, with a seeded conversation. */
const fs=require('fs'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const base='http://127.0.0.1:8772';
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('blob:'))external.push(r.url());});
  await page.goto(base);await page.waitForFunction(()=>state.data);
  assert.equal(await page.locator('[data-teacher-select]').count(),3);
  assert.equal(await page.locator('[data-teacher-select]:disabled').count(),0);
  await page.evaluate(async()=>{await api('/api/settings',{teacher:'sofia',base:'en',auto_speak:false});await refresh();await resumeLesson(state.data.sessions[0].id);});
  const before=await page.evaluate(()=>({id:state.session.id,xp:state.data.stats.xp,messages:state.session.messages.length,notes:state.session.notes}));
  const text=await page.evaluate(()=>state.session.messages.find(m=>m.role==='assistant').payload.segments[0].text);
  const play=async(selector,teacher)=>{
   const request=page.waitForResponse(r=>r.url().endsWith('/api/speech'));
   await page.locator(selector).first().click();const response=await request;
   assert.equal(response.status(),200);const body=response.request().postDataJSON();
   assert.equal(body.teacher,teacher);
   await page.waitForFunction(()=>audioPlayer.audio&&!audioPlayer.audio.paused&&audioPlayer.audio.duration>0,null,{timeout:30000});
   await page.evaluate(()=>audioPlayer.stop());return body;
  };
  for(const teacher of ['aurora','leonardo']){
   const body=await play(`[data-segment-play][data-voice="${teacher}"]`,teacher);
   assert.equal(body.text,text);assert.equal(body.language,'it');
  }
  await play('[data-segment-play][data-slow]','sofia');
  await play('[data-correction][data-voice="aurora"]','aurora');
  assert.deepEqual(await page.evaluate(()=>({id:state.session.id,xp:state.data.stats.xp,messages:state.session.messages.length,notes:state.session.notes})),before);
  assert.equal(await page.evaluate(()=>state.data.settings.teacher),'sofia');
  await page.locator('#chat-input').fill('Un pensiero da conservare.');
  for(const teacher of ['aurora','leonardo']){
   await page.locator(`[data-teacher-select="${teacher}"]`).click();
   await page.waitForFunction(t=>!state.busy&&state.data.settings.teacher===t,teacher);
   assert.equal(await page.locator('#chat-input').inputValue(),'Un pensiero da conservare.');
   assert.equal(await page.evaluate(()=>state.session.id),before.id);
   assert.equal((await page.locator('.message.assistant .message-label').first().textContent()).replace(/\s+/g,' ').trim(),'SOFIA · your teacher');
   assert((await page.locator('.chat-header h3').innerText()).startsWith(teacher[0].toUpperCase()+teacher.slice(1)));
  }
  await page.reload();await page.waitForFunction(()=>state.data);
  assert.equal(await page.evaluate(()=>state.data.settings.teacher),'leonardo');
  await page.evaluate(()=>resumeLesson(state.session.id));
  await page.locator('#chat-input').fill('Come ti chiami?');await page.locator('#chat-input').press('Enter');
  await page.waitForFunction(()=>state.busy);
  await page.waitForFunction(()=>!state.busy,null,{timeout:120000});
  assert.equal(await page.locator('.error-box').count(),0);
  const reply=await page.evaluate(()=>state.session.messages.at(-1).payload);
  assert.equal(reply.teacher,'leonardo');
  assert(reply.segments.some(s=>/Leonardo/i.test(s.text)),'Teacher should use the selected identity');
  assert.equal((await page.locator('.message.assistant .message-label').last().textContent()).replace(/\s+/g,' ').trim(),'LEONARDO · your teacher');
  const other=await page.evaluate(async()=>{const p=await api('/api/profiles',{name:'Teacher isolation',base:'fr'});return (await api('/api/state',undefined,p.id)).settings.teacher;});
  assert.equal(other,'sofia');
  const layouts=[];
  for(const width of [320,360,390,430,768,1440]){
   await page.setViewportSize({width,height:width>=768?1050:844});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`Overflow at ${width}`);layouts.push(width);
  }
  fs.mkdirSync('artifacts',{recursive:true});
  await page.screenshot({path:'artifacts/teachers-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.locator('.voice-comparison').last().scrollIntoViewIfNeeded();
  await page.screenshot({path:'artifacts/teachers-mobile.png',fullPage:true});
  await page.locator('[data-view="settings"]:visible').first().click();
  assert(await page.getByText('About the voices',{exact:true}).isVisible());
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const report={passed:true,teachers:3,exactReplay:true,progressPreserved:true,draftPreserved:true,historyKeepsSpeaker:true,profileIsolation:true,modelIdentity:reply.segments.map(s=>s.text).join(' '),layouts,errors,external};
  fs.writeFileSync('artifacts/teachers-validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
