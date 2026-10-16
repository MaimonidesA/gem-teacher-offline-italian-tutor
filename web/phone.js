'use strict';
(async()=>{
  const output=document.querySelector('#phone-addresses');
  try{
    const response=await fetch('/api/network');if(!response.ok)throw new Error('The local server is unavailable.');
    const network=await response.json();output.textContent='';
    if(!network.enabled||!network.urls.length)throw new Error('Wi-Fi sharing is not ready. On the computer, connect to Wi-Fi and restart Gem Teacher with ./start_teacher.sh --lan.');
    for(const url of network.urls){
      const link=document.createElement('a');link.className='button';link.href=url;link.textContent=url;output.append(link);
    }
  }catch(error){output.textContent=error.message;}
})();
