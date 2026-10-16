/* Isolated real-model/TTS test: HTTP 8771, local HTTPS 9444; synthetic microphone WAV. */
const fs=require('fs'),assert=require('assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const network=await (await fetch('http://127.0.0.1:8771/api/network')).json(),url=network.urls[0];assert(url);
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-audio-capture=/tmp/parliamo-phone-microphone.wav']});
 const context=await browser.newContext({ignoreHTTPSErrors:true,permissions:['microphone'],viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 const page=await context.newPage(),errors=[],external=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(url)&&!r.url().startsWith('blob:'))external.push(r.url());});
 const ready=async()=>{await page.waitForFunction(()=>!state.busy&&state.session?.messages.length,{},{timeout:120000});assert.equal(await page.locator('.error-box').count(),0);};
 await page.goto(url);await page.waitForFunction(()=>state.data);assert(await page.evaluate(()=>isSecureContext&&!!navigator.mediaDevices?.getUserMedia));
 // Always use a fresh local learner so repeated validation never modifies a real profile.
 await page.evaluate(async()=>{const p=await api('/api/profiles',{name:'Phone validation',base:'fr'});await switchProfile(p.id);await api('/api/settings',{auto_speak:false,mic_device:'desktop-device-unavailable'});await refresh();});
 await page.locator('.topic-card[data-topic="hello"]').click();await ready();
 const slowResponse=page.waitForResponse(r=>r.url().endsWith('/api/speech')&&r.request().postDataJSON()?.slow===true);
 await page.locator('[data-segment-play][data-slow]').first().click();assert.equal((await slowResponse).status(),200);
 await page.waitForFunction(()=>audioPlayer.audio&&!audioPlayer.audio.paused&&audioPlayer.audio.duration>0,{},{timeout:30000});await page.evaluate(()=>audioPlayer.stop());
 await page.locator('#chat-input').fill('Io sono trenta anni.');await page.locator('#chat-input').press('Enter');await page.waitForFunction(()=>state.busy);await ready();
 assert((await page.evaluate(()=>state.lastResult.assessment.rating))<5);
 const xp=await page.evaluate(()=>state.data.stats.xp);
 const explanation=page.waitForResponse(r=>r.url().endsWith('/api/assessment-explanation'));
 await page.locator('[data-explanation]').last().click();const feedback=await (await explanation).json();assert.equal(feedback.language,'en');assert(/age|have|avere/i.test(feedback.text));
 await page.waitForFunction(()=>!state.busy&&audioPlayer.audio&&!audioPlayer.audio.paused,{},{timeout:60000});assert.equal(await page.evaluate(()=>state.data.stats.xp),xp);await page.evaluate(()=>audioPlayer.stop());
 // Simulate Safari's user-gesture requirement and recover using the visible play button.
 await page.evaluate(()=>{const play=HTMLMediaElement.prototype.play;let first=true;HTMLMediaElement.prototype.play=function(){if(first){first=false;return Promise.reject(new DOMException('Gesture required','NotAllowedError'));}return play.call(this);};});
 await page.locator('[data-correction][data-slow]').first().click();await page.locator('#audio-permission').waitFor({state:'visible'});await page.locator('[data-action="resume-audio"]').click();await page.locator('#audio-permission').waitFor({state:'hidden'});
 await page.waitForFunction(()=>audioPlayer.audio&&!audioPlayer.audio.paused);await page.evaluate(()=>audioPlayer.stop());
 // Hands-free HTTPS microphone, including fallback from a desktop-only device ID.
 await page.locator('#handsfree').check();await page.waitForFunction(()=>state.recorder?.node,{},{timeout:15000});await page.waitForFunction(()=>state.busy,{},{timeout:30000});await page.locator('#handsfree').uncheck();await ready();
 const spoken=await page.evaluate(()=>state.lastResult);assert(spoken.heard.trim());assert.equal(spoken.metrics.input,'native_audio');assert(spoken.assessment);
 fs.mkdirSync('artifacts',{recursive:true});const layouts=[];
 for(const width of [320,360,390,430,768,1440]){
   await page.setViewportSize({width,height:width>=768?1000:844});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert(!overflow,`Horizontal overflow at ${width}`);layouts.push(width);
 }
 await page.setViewportSize({width:390,height:844});await page.locator('[data-explanation]').first().scrollIntoViewIfNeeded();await page.screenshot({path:'artifacts/phone-conversation.png',fullPage:true,animations:'disabled'});
 await page.locator('.sidebar [data-view="settings"]:visible').click();assert(await page.locator('.phone-panel .phone-link').first().isVisible());await page.screenshot({path:'artifacts/phone-preferences.png',fullPage:true,animations:'disabled'});
 await page.goto(url+'/phone.html');await page.locator('#phone-addresses a').waitFor();assert.equal(await page.locator('#phone-addresses a').first().getAttribute('href'),url);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:'artifacts/phone-setup.png',fullPage:true,animations:'disabled'});
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);const report={passed:true,secureMicrophone:true,nativeAudioTranscript:spoken.heard,englishExplanation:feedback.text,slowReplay:true,autoplayRecovery:true,layouts,errors,external};
 fs.writeFileSync('artifacts/phone-validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
