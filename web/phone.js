'use strict';
(async function refreshAddresses(){
  const output=document.querySelector('#phone-addresses');
  try{
    const response=await fetch('/api/network');if(!response.ok)throw new Error('The local server is unavailable.');
    const network=await response.json();output.textContent='';
    if(!network.enabled)throw new Error('Wi-Fi sharing is disabled. On the computer, stop Gem Teacher, then run ./start_teacher.sh --lan.');
    if(!network.urls.length){
      output.textContent='Sharing is enabled. Connect the computer to Wi-Fi; the address will appear automatically within a few seconds.';
      setTimeout(refreshAddresses,5000);return;
    }
    for(const url of network.urls){
      const link=document.createElement('a');link.className='button';link.href=url;link.textContent=url;output.append(link);
    }
  }catch(error){output.textContent=error.message;}
})();
