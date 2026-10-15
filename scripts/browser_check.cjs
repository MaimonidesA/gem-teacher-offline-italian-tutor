/* Local browser QA, using an installed Playwright runtime supplied by the caller. */
const fs = require('fs');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1:8765')&&!r.url().startsWith('blob:'))external.push(r.url());});
  await page.goto('http://127.0.0.1:8765');
  await page.getByRole('heading',{name:/on s’y met/}).waitFor();
  fs.mkdirSync('artifacts',{recursive:true});
  await page.screenshot({path:'artifacts/home-desktop.png',fullPage:true});
  for(const name of ['Mon carnet','Mes progrès','Mes préférences','Conversation','Mon parcours']){
    await page.locator('.sidebar').getByRole('button',{name,exact:false}).click();
    await page.waitForTimeout(100);
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Horizontal overflow on '+name);
  }
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'artifacts/home-mobile.png',fullPage:true});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile horizontal overflow');
  console.log(JSON.stringify({errors,external,desktop:'artifacts/home-desktop.png',mobile:'artifacts/home-mobile.png'}));
  await browser.close();if(errors.length||external.length)process.exitCode=1;
})();
