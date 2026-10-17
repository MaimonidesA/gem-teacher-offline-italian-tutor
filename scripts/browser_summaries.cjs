/* Run after live_summaries.py against the isolated instance on port 8774. */
const fs=require('fs'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const report=JSON.parse(fs.readFileSync('artifacts/summaries-live.json')),base='http://127.0.0.1:8774';
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[],external=[],speech=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('blob:'))external.push(r.url());if(r.url().endsWith('/api/speech'))speech.push(r.postDataJSON());});
  await page.addInitScript(id=>localStorage.setItem('parliamo-profile',id),report.profile_id);
  await page.goto(base);await page.waitForFunction(()=>state.data);
  await page.evaluate(async()=>{await api('/api/settings',{base:'fr',feedback_base:'fr',auto_speak:false});await refresh();});
  await page.evaluate(id=>resumeLesson(id),report.session_id);
  const feedback=page.locator(`[data-message="${report.message_id}"]`),output=page.locator(`#explanation-${report.message_id}`);
  assert.equal(await feedback.locator('[data-explanation]').count(),4);
  assert.equal(await output.getAttribute('lang'),'fr');
  assert.match(await output.innerText(),/^FR · /);
  const before=await page.evaluate(()=>state.data.stats);
  for(const language of ['en','fr']){
   const count=speech.length;
   await feedback.locator(`[data-explanation][data-language="${language}"][data-play="false"]`).click();
   await page.waitForFunction(()=>!state.translating);
   assert.equal(await output.getAttribute('lang'),language);
   assert.equal(speech.length,count,'Reading a translation must not start audio');
   const response=page.waitForResponse(r=>r.url().endsWith('/api/speech')&&r.ok());
   await feedback.locator(`[data-explanation][data-language="${language}"][data-play="true"]`).click();
   await response;await page.waitForFunction(()=>!state.translating);
   assert.equal(speech.at(-1).language,language);
   assert.equal(speech.at(-1).text,report.feedback[language].text);
   await page.evaluate(()=>audioPlayer.stop());
  }
  assert.deepEqual(await page.evaluate(()=>state.data.stats),before);
  await feedback.scrollIntoViewIfNeeded();await page.screenshot({path:'artifacts/feedback-bilingual-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await feedback.locator('.explanation-tools').scrollIntoViewIfNeeded();
  await page.screenshot({path:'artifacts/feedback-bilingual-mobile.png',fullPage:true});
  await page.evaluate(id=>openLessonRecap(id),report.session_id);
  assert(await page.locator('.lesson-recap .teacher-summary').isVisible());
  assert((await page.locator('.lesson-recap .teacher-summary li').count())>=3);
  const replay=page.waitForResponse(r=>r.url().endsWith('/api/speech')&&r.ok());
  await page.locator('[data-summary-speak]').click();await replay;
  assert.equal(speech.at(-1).language,'fr');await page.evaluate(()=>audioPlayer.stop());
  for(const width of [320,390,768,1440]){
   await page.setViewportSize({width,height:900});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   assert.equal(await page.locator('#modal').evaluate(el=>el.scrollWidth>el.clientWidth+1),false);
   if(width===390)await page.screenshot({path:'artifacts/summary-mobile.png',fullPage:true});
   if(width===1440)await page.screenshot({path:'artifacts/summary-desktop.png',fullPage:true});
  }
  await page.locator('.modal-close').click();
  await page.reload();await page.waitForFunction(()=>state.data);
  await page.evaluate(id=>resumeLesson(id),report.session_id);
  assert.equal(await page.locator('.summary-message').count(),1);
  assert.equal(await page.locator(`#explanation-${report.message_id}`).getAttribute('lang'),'fr');
  // Replay real saved completion data through the streaming UI to check autoplay.
  const session=await page.evaluate(()=>structuredClone(state.session));
  const summaryMessage=session.messages.find(m=>m.payload.action==='summary');
  const result=session.messages[session.messages.indexOf(summaryMessage)-1].payload;
  const events=report.completion_events||[{type:'lesson_summary',summary:summaryMessage.payload.lesson_summary,segments:summaryMessage.payload.segments},{type:'done',result,session,just_completed:true,xp:0}];
  await page.route('**/api/turn',route=>route.fulfill({contentType:'application/x-ndjson',body:events.map(e=>JSON.stringify(e)).join('\n')+'\n'}));
  await page.evaluate(()=>{window.played=[];audioPlayer.enqueue=s=>played.push(s);state.data.settings.auto_speak=true;});
  await page.evaluate(()=>sendTurn('reply','Come stai?'));
  assert.equal(await page.evaluate(text=>played.filter(s=>s.text===text).length,summaryMessage.payload.lesson_summary.overview),1);
  await page.unroute('**/api/turn');
  // A real manual finish creates a summary and reads it once if speech is enabled.
  await page.evaluate(async id=>{await api('/api/resume-objectives',{session_id:id});await api('/api/settings',{auto_speak:true});await refresh();await resumeLesson(id);window.played=[];},report.early_id);
  await page.locator('#finish-button').click();
  await page.waitForFunction(()=>!state.busy&&document.querySelector('#modal').open&&state.session.lesson.teacher_summary,{},{timeout:120000});
  await page.waitForFunction(()=>played.length>0);
  assert.equal(await page.evaluate(()=>played.filter(s=>s.text===state.session.lesson.teacher_summary.overview).length),1);
  assert.deepEqual(await page.evaluate(()=>state.data.stats),before);
  await page.locator('.modal-close').click();
  await page.evaluate(()=>setView('settings'));
  assert.equal(await page.locator('[name="feedback_base"]').inputValue(),'fr');
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  fs.writeFileSync('artifacts/summaries-browser.json',JSON.stringify({passed:true,errors,external,readDoesNotPlay:true,languages:['fr','en'],summaryAutoplay:true,manualSummary:true,layouts:[320,390,768,1440]},null,2));
  console.log('PASS bilingual text/audio, saved summaries, automatic and manual summary playback, phone layouts');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
