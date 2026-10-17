/* Run after live_lessons.py against the isolated server on port 8773. */
const fs=require('fs'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const report=JSON.parse(fs.readFileSync('artifacts/lessons-live.json'));
 const base='http://127.0.0.1:8773';
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[],external=[],speech=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('blob:'))external.push(r.url());if(r.url().endsWith('/api/speech'))speech.push(r.postDataJSON());});
  await page.addInitScript(id=>localStorage.setItem('parliamo-profile',id),report.profile_id);
  await page.goto(base);await page.waitForFunction(()=>state.data);
  await page.evaluate(async()=>{await api('/api/settings',{base:'en'});await refresh();});
  await page.evaluate(id=>resumeLesson(id),report.session_id);
  await page.waitForFunction(()=>!state.busy);
  assert.equal(await page.locator('#lesson-plan li.achieved').count(),3);
  assert.match(await page.locator('#lesson-plan').innerText(),/Goals achieved/);
  assert(await page.locator('#lesson-milestone').isVisible());
  assert(await page.locator('#chat-input').isEnabled());
  assert(await page.locator('#lesson-milestone [data-topic="city"]').isVisible());
  assert.match(await page.locator('#lesson-resources').innerText(),/plural/);
  const before=await page.evaluate(()=>({xp:state.data.stats.xp,turns:state.session.turns,finished:state.session.finished}));
  await page.screenshot({path:'artifacts/lessons-desktop.png',fullPage:true});
  await page.locator('#finish-button').click();await page.locator('.lesson-recap').waitFor();
  assert.equal(await page.locator('.lesson-recap blockquote').count(),3);
  const wordCount=await page.locator('.lesson-vocabulary article').count();assert(wordCount>=3&&wordCount<=12);
  const spoken=page.waitForResponse(r=>r.url().endsWith('/api/speech')&&r.ok());
  await page.locator('[data-lesson-speak="0"]').click();await spoken;
  assert.equal(speech.at(-1).language,'it');await page.evaluate(()=>audioPlayer.stop());
  await page.locator('[data-lesson-practice]').click();
  for(let i=0;i<wordCount;i++){
   assert.equal(await page.locator('.review-answer').count(),0);
   await page.locator('[data-lesson-reveal]').click();assert(await page.locator('.review-answer').isVisible());
   await page.locator(`[data-lesson-grade="${i===0?'again':'good'}"]`).click();
   if(i+1<wordCount)await page.locator('[data-lesson-reveal]').waitFor();
  }
  await page.getByRole('heading',{name:'Practice complete!'}).waitFor();
  await page.locator('[data-lesson-back]').click();assert.match(await page.locator('.lesson-vocabulary').innerText(),/Reviews: 1/);
  await page.locator('[data-lesson-save="0"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-lesson-save="0"]').disabled);
  const after=await page.evaluate(()=>({xp:state.data.stats.xp,turns:state.session.turns,finished:state.session.finished}));
  assert.deepEqual(after,before);
  await page.screenshot({path:'artifacts/lessons-recap-desktop.png',fullPage:true});
  for(const width of [320,390,768,1440]){
   await page.setViewportSize({width,height:900});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   assert.equal(await page.locator('#modal').evaluate(el=>el.scrollWidth>el.clientWidth+1),false);
   if(width===390)await page.screenshot({path:'artifacts/lessons-recap-mobile.png',fullPage:true});
  }
  await page.locator('.modal-close').click();
  await page.selectOption('#support-language','fr');await page.waitForFunction(()=>!state.busy&&state.data.settings.base==='fr');
  assert.match(await page.locator('#lesson-plan').innerText(),/Objectifs atteints/);
  assert.match(await page.locator('#lesson-resources').innerText(),/pluriel/);
  for(const width of [320,390,768,1440]){
   await page.setViewportSize({width,height:900});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   if(width===390)await page.screenshot({path:'artifacts/lessons-mobile.png',fullPage:true});
  }
  await page.evaluate(()=>setView('notebook'));
  assert(await page.locator('.lesson-library').isVisible());
  await page.locator(`[data-lesson-recap="${report.early_id}"]`).click();
  await page.waitForFunction(id=>state.recapSession?.id===id&&document.querySelector('#modal').open,report.early_id);
  assert.match(await page.locator('.recap-status').innerText(),/objectifs à reprendre/);
  await page.locator('[data-resume-objectives]').click();
  await page.waitForFunction(()=>state.session?.lesson?.status==='active');
  assert.equal(await page.locator('#lesson-plan li.achieved').count(),1);
  await page.locator('#finish-button').click();await page.locator('.lesson-recap').waitFor();
  assert.match(await page.locator('.recap-status').innerText(),/objectifs à reprendre/);
  assert.equal(await page.evaluate(()=>state.data.stats.lessons),1);
  await page.locator('.modal-close').click();
  await page.reload();await page.waitForFunction(()=>state.data);
  await page.evaluate(id=>openLessonRecap(id),report.session_id);
  assert.match(await page.locator('.lesson-vocabulary').innerText(),/Révisions: 1/);
  await page.locator('.recap-actions [data-topic="city"]').click();
  await page.waitForFunction(()=>!state.busy&&state.session?.topic==='city'&&state.session.messages.length,{},{timeout:120000});
  assert.equal(await page.locator('#modal').evaluate(el=>el.open),false);
  assert.equal(await page.locator('#lesson-plan li.achieved').count(),0);
  // Exercise the UI's automatic completion/audio path without changing saved progress.
  await page.evaluate(()=>{window.played=[];audioPlayer.enqueue=s=>played.push(s);state.data.settings.auto_speak=true;state.handsfree=true;});
  const session=await page.evaluate(()=>structuredClone(state.session));
  const announcement={language:'it',kind:'instruction',text:'Abbiamo raggiunto tutti gli obiettivi della lezione!'};
  const result={segments:[{language:'it',kind:'dialogue',text:'Va bene!'},announcement],action:'reply',phrase:{},memory:session.notes};
  const updated={...session,finished:new Date().toISOString(),lesson:{...session.lesson,status:'achieved',objectives:session.lesson.objectives.map(o=>({...o,evidence:'Test learner evidence'}))},messages:[...session.messages,{id:'completion-ui',role:'assistant',payload:result}]};
  await page.route('**/api/turn',route=>route.fulfill({contentType:'application/x-ndjson',body:[...result.segments.map(segment=>({type:'segment',segment})),{type:'done',result,session:updated,just_completed:true,xp:10}].map(v=>JSON.stringify(v)).join('\n')+'\n'}));
  await page.evaluate(()=>sendTurn('reply','Va bene.'));
  assert.equal(await page.evaluate(()=>state.handsfree),false);
  assert.equal(await page.evaluate(()=>played.filter(s=>s.text.includes('obiettivi')).length),1);
  assert(await page.locator('#lesson-milestone').isVisible());assert(await page.locator('#chat-input').isEnabled());
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  fs.writeFileSync('artifacts/lessons-browser.json',JSON.stringify({passed:true,wordCount,layouts:[320,390,768,1440],errors,external,progressPreserved:true,completionSpoken:true},null,2));
  console.log('PASS lesson objectives, recap, speech, vocabulary practice, early finish, restart, next lesson, phone layouts');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
