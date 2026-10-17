'use strict';
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
  path:'M5 4h6v6H5z M13 14h6v6h-6z M8 10v4a3 3 0 0 0 3 3h2 M11 7h5a3 3 0 0 1 3 3v1',
  chat:'M20 11a8 8 0 0 1-8 8H5l-3 3v-11a9 9 0 0 1 18 0Z M7 10h8 M7 14h5',
  bookmark:'M6 3h12v18l-6-4-6 4V3Z', chart:'M4 20h17 M7 16V9 M12 16V4 M17 16v-6',
  settings:'M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  lock:'M6 10h12v11H6z M8 10V7a4 4 0 0 1 8 0v3 M12 14v3', flame:'M12 2c2 6 6 7 6 13a6 6 0 0 1-12 0c0-3 2-6 4-7 0 3 2 4 2 4s3-4 0-10Z',
  arrow:'M5 12h14 M13 6l6 6-6 6', wave:'M6 13 3 8a1.5 1.5 0 0 1 3-1l3 4-4-7a1.5 1.5 0 0 1 3-1l4 7-2-7a1.5 1.5 0 0 1 3 0l3 9 1-4a2 2 0 0 1 4 1l-1 7a7 7 0 0 1-12 4l-6-6a1.5 1.5 0 0 1 2-2l4 3',
  coffee:'M4 8h12v7a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8Z M16 9h2a3 3 0 0 1 0 6h-2 M7 2v3 M12 2v3 M2 22h18',
  map:'m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2V5Z M9 3v16 M15 5v16', food:'M5 2v7a3 3 0 0 0 6 0V2 M8 2v20 M19 22V2c-5 3-5 11 0 11',
  sun:'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2',
  train:'M6 3h12v14H6z M6 11h12 M10 3v8 M5 22l3-5 M19 22l-3-5 M9 15h.01 M15 15h.01',
  book:'M12 5C8 2 4 3 2 4v16c4-2 7-1 10 1 3-2 6-3 10-1V4c-3-1-6-2-10 1Z M12 5v16',
  check:'m5 12 4 4L19 6', clock:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M12 7v5l3 2',
  globe:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M3 12h18 M12 3c5 6 5 12 0 18-5-6-5-12 0-18',
  spark:'m12 3 2 6 7 3-7 3-2 6-3-6-6-3 6-3 3-6Z', headphones:'M4 13v-2a8 8 0 0 1 16 0v2 M4 12h3v8H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2Z M20 12h-3v8h3a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2Z',
  mic:'M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0V5Z M5 10v2a7 7 0 0 0 14 0v-2 M12 19v3 M8 22h8',
  volume:'M11 4 6 8H2v8h4l5 4V4Z M15 8a6 6 0 0 1 0 8 M18 5a10 10 0 0 1 0 14',
  stop:'M6 6h12v12H6z', send:'m3 3 18 9-18 9 4-9-4-9Z M7 12h14', plus:'M12 5v14 M5 12h14',
  download:'M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5', trash:'M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7',
  flag:'M5 22V3 M5 4c5-4 9 4 15 0v10c-6 4-10-4-15 0', leaf:'M20 3C8 1 1 9 6 16c7 5 15-2 14-13Z M4 21l11-11',
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.spark}"/></svg>`;
const flags = {it:'🇮🇹',fr:'🇫🇷',en:'🇬🇧'};
const names = {it:'italien',fr:'français',en:'anglais'};
const labels = {learn:'MON PARCOURS',conversation:'CONVERSATION',coffee:'LE SALON CAFÉ',notebook:'MON CARNET',progress:'MES PROGRÈS',settings:'MES PRÉFÉRENCES'};
const state = {profileId:localStorage.getItem('parliamo-profile')||'default',data:null,health:null,view:'learn',unit:1,session:null,busy:false,controller:null,review:null,search:'',lastRequest:null,handsfree:false,recorder:null,lastResult:null,translating:false};
let toastTimer;
function toast(text) { $('#toast').textContent = text; $('#toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 4000); }
async function api(path, data, profileId=state.profileId) {
  const response = await fetch(path, {headers:{'Content-Type':'application/json','X-Parliamo-Profile':profileId},...(data===undefined?{}:{method:'POST',body:JSON.stringify(data)})});
  const value = await response.json(); if (!response.ok) throw new Error(value.error || 'Une erreur est survenue.'); return value;
}
function errorText(error) { return error.message === 'Failed to fetch' ? 'Le serveur local ne répond pas. Ouvrez Gem Teacher sur l’ordinateur et gardez-le allumé, sur le même Wi-Fi que votre téléphone.' : error.message; }
async function refresh() { state.data = await api('/api/state'); if(state.session)state.session.base=state.data.settings.base; updateChrome(); }
function updateChrome() {
  const data = state.data; if (!data) return;
  $$('[data-profile-name]').forEach(el=>el.textContent=data.profile.name);
  $$('[data-profile-initial]').forEach(el=>el.textContent=Array.from(data.profile.name)[0].toLocaleUpperCase());
  $('#book-count').textContent = data.bookmarks.length; $('#streak').textContent = data.stats.streak;
  $('#support-language').value = data.settings.base;setSupportLocale(data.settings.base,teacherInfo().name);
  renderTeachers();
  $('#target-language').value = data.settings.target; $('#target-flag').textContent = flags[data.settings.target];
  $('#page-label').textContent = labels[state.view];
  $$('.nav-item').forEach(button => button.classList.toggle('active',button.dataset.view === state.view));
}
async function checkHealth() {
  const profileId=state.profileId;
  try { const health = await api('/api/health'); if(profileId!==state.profileId)return; state.health=health;
    $('#status-dot').classList.toggle('ready',health.online);
    $('#status-text').textContent = health.online ? `Tout reste ici · ${health.model} · ${health.placement}` : 'Professeur indisponible · Consultez les préférences';
  } catch { if(profileId!==state.profileId)return; $('#status-text').textContent = 'Serveur local déconnecté'; $('#status-dot').classList.remove('ready'); }
}
function sessionKey(profileId=state.profileId){return 'parliamo-session:'+profileId;}
function teacherInfo(id=state.data?.settings.teacher){
  return state.data?.teachers?.find(t=>t.id===id)||{id:'sofia',name:'Sofia',initial:'S'};
}
function renderTeachers(){
  const strip=$('#teacher-strip');if(!strip||!state.data?.teachers)return;
  strip.hidden=false;
  strip.innerHTML=`<div class="teacher-strip-heading"><strong>Votre professeur</strong><span>Même conversation, trois voix italiennes.</span></div><div class="teacher-choices">${state.data.teachers.map(t=>`<button class="teacher-choice ${t.id}" data-teacher-select="${t.id}" aria-pressed="${t.id===state.data.settings.teacher}" ${!t.available?'disabled':''}><span class="teacher-avatar" data-verbatim>${t.initial}</span><span><strong data-verbatim>${t.name}</strong><small>${t.available?esc(t.description):'Voix à installer'}</small></span>${t.id===state.data.settings.teacher?icon('check'):''}</button>`).join('')}</div>`;
}
async function switchTeacher(id){
  if(state.busy||state.translating)return toast('Attendez la fin de la réponse pour changer de professeur.');
  if(id===state.data.settings.teacher)return;
  const draft=$('#chat-input')?.value, handsfree=state.handsfree;
  state.busy=true;state.handsfree=false;await stopRecording(false);audioPlayer.stop();
  try{
    await api('/api/settings',{teacher:id});await refresh();render();
    if(draft!==undefined&&$('#chat-input'))$('#chat-input').value=draft;
    toast('Le professeur change, la conversation continue.');
  }catch(error){toast(errorText(error));}
  finally{state.busy=false;state.handsfree=handsfree;if($('#handsfree'))$('#handsfree').checked=handsfree;maybeListen();}
}
function otherVoiceButtons(messageId,index,original='sofia',correction=false){
  return `<span class="voice-comparison-label">Autre voix :</span>${(state.data.teachers||[]).filter(t=>t.id!==original).map(t=>`<button ${correction?'data-correction':'data-segment-play'}="${messageId}" data-index="${index}" data-voice="${t.id}" ${!t.available?'disabled data-unavailable="true"':''} title="Même phrase, autre voix">${icon('volume')} <span data-verbatim>${t.name}</span></button>`).join('')}`;
}
function draftKey(){return 'parliamo-draft:'+state.profileId+':'+state.session?.id;}
async function savedSession(profileId, target){
  const id=localStorage.getItem(sessionKey(profileId));if(!id)return null;
  try{const session=await api('/api/sessions/'+encodeURIComponent(id),undefined,profileId);return session.target===target?session:null;}
  catch{localStorage.removeItem(sessionKey(profileId));return null;}
}
async function switchProfile(profileId){
  if(state.busy||state.translating||profileId===state.profileId)return;
  const draft=$('#chat-input')?.value;
  if(state.session&&draft!==undefined)sessionStorage.setItem(draftKey(),draft);
  state.busy=true;state.handsfree=false;
  await stopRecording(false);audioPlayer.stop();
  try{
    const data=await api('/api/state',undefined,profileId);
    const session=await savedSession(profileId,data.settings.target);
    state.profileId=profileId;localStorage.setItem('parliamo-profile',profileId);
    Object.assign(state,{data,session,health:null,lastResult:null,lastRequest:null,review:null,search:'',unit:1,controller:null,view:session?(session.mode==='coffee'?'coffee':'conversation'):'learn'});
    $('#modal').close();render();
    if(session&&$('#chat-input'))$('#chat-input').value=sessionStorage.getItem(draftKey())||'';
    window.scrollTo({top:0,behavior:'instant'});await checkHealth();
  }finally{state.busy=false;}
}
async function profilesModal(){
  if(state.busy||state.translating)return toast('Attendez la fin de la réponse pour changer de profil.');
  state.handsfree=false;await stopRecording(false);audioPlayer.stop();if($('#handsfree'))$('#handsfree').checked=false;
  const {profiles}=await api('/api/profiles');
  showModal(`<div class="eyebrow">CHACUN SON PARCOURS</div><h2>Qui apprend aujourd’hui ?</h2><p>Chaque profil garde ses conversations, ses progrès, son carnet et ses préférences.</p>
    <div class="learner-list" aria-label="Profils sur cet ordinateur">${profiles.map(p=>`<button class="learner-choice ${p.id===state.profileId?'selected':''}" data-switch-profile="${esc(p.id)}" ${p.id===state.profileId?'disabled aria-current="true"':''}><span class="profile-avatar" data-verbatim>${esc(Array.from(p.name)[0].toLocaleUpperCase())}</span><strong data-verbatim>${esc(p.name)}</strong><span>${p.id===state.profileId?'Profil actuel':icon('arrow')}</span></button>`).join('')}</div>
    <details class="profile-rename"><summary>Renommer mon profil</summary><form id="rename-profile-form"><label for="rename-profile-name">Nom du profil</label><div class="profile-name-row"><input class="input" id="rename-profile-name" value="${esc(state.data.profile.name)}" required maxlength="40" autocomplete="off"><button class="button secondary small" type="submit">Enregistrer</button></div></form></details>
    <form id="add-profile-form" class="add-profile-form"><h3>Ajouter un profil</h3><div class="field-row"><div class="field"><label for="new-profile-name">Prénom ou surnom</label><input class="input" id="new-profile-name" required maxlength="40" placeholder="Votre prénom" autocomplete="off"></div><div class="field"><label for="new-profile-base">Langue d’appui</label><select class="input" id="new-profile-base"><option value="fr" ${state.data.settings.base==='fr'?'selected':''}>Français</option><option value="en" ${state.data.settings.base==='en'?'selected':''}>English</option></select></div></div><button class="button" type="submit">${icon('plus')}Créer et commencer</button><small>Un nouveau parcours, à son rythme. Tout reste sur cet ordinateur.</small></form>`);
  $('#rename-profile-form').onsubmit=async event=>{
    event.preventDefault();const button=event.submitter;button.disabled=true;
    try{state.data.profile=await api('/api/profiles/rename',{name:$('#rename-profile-name').value});updateChrome();await profilesModal();}
    catch(error){toast(errorText(error));button.disabled=false;}
  };
  $('#add-profile-form').onsubmit=async event=>{
    event.preventDefault();const button=event.submitter;button.disabled=true;
    try{const profile=await api('/api/profiles',{name:$('#new-profile-name').value,base:$('#new-profile-base').value});await switchProfile(profile.id);}
    catch(error){toast(errorText(error));button.disabled=false;}
  };
}
function render() { updateChrome(); ({learn:renderLearn,conversation:renderConversation,coffee:renderCoffee,notebook:renderNotebook,progress:renderProgress,settings:renderSettings}[state.view] || renderLearn)(); }
function setView(view) {
  if (state.busy||state.translating) return toast('Attendez la réponse, ou utilisez Arrêter pour changer de page.');
  stopRecording(false); audioPlayer.stop(); state.handsfree = false; state.view = labels[view] ? view : 'learn';
  if (state.view !== 'notebook') state.review = null;
  render(); window.scrollTo({top:0,behavior:'instant'});
}
function topicCard(topic, recommended) {
  const completed = state.data.completed_topics.includes(topic.id);
  return `<button class="topic-card ${recommended ? 'recommended' : ''}" data-topic="${topic.id}">
    <span class="topic-icon">${icon(completed?'check':topic.icon)}</span><span class="topic-info">
    <span class="topic-sub">${completed?'DÉJÀ EXPLORÉ · À REPRATIQUER':recommended?'VOTRE PROCHAINE DÉCOUVERTE':state.data.settings.target==='it'?esc(topic.italian.toUpperCase()):'CONVERSATION GUIDÉE'}</span>
    <h3>${esc(topic.title)}</h3><p>${esc(topic.description)}</p><span class="topic-meta"><i>${topic.level}</i>${topic.minutes} min · Conversation</span>
    </span><span class="topic-arrow">${icon(completed?'check':'arrow')}</span></button>`;
}
function renderLearn() {
  const {settings,stats,topics,bookmarks,sessions} = state.data;
  const next = topics.find(t => !state.data.completed_topics.includes(t.id)) || topics[0];
  const resume = sessions.find(s => s.turns > 0);
  const percent = Math.min(1,stats.today_xp/settings.daily_goal);
  const dayNames = ['D','L','M','M','J','V','S'];
  const word = bookmarks[0];
  const hour = new Date().getHours(); const greeting = settings.target==='it' ? (hour>=17?'Buonasera':'Buongiorno') : settings.target==='fr'?'Bonjour':'Hello';
  $('#app').innerHTML = `<div class="welcome-row"><div><h1>${greeting}, on s’y met ? <span style="color:#a9b47d;font-size:25px">✳</span></h1><p>Un peu d’${settings.target==='it'?'italien':settings.target==='en'?'anglais':'apprentissage'}, beaucoup de découvertes.</p></div><button class="base-badge" data-view="settings">${icon('globe')} Depuis ${settings.base==='fr'?'le français':'l’anglais'}</button></div>
    <div class="dashboard-grid"><section><div class="hero"><div class="hero-copy"><div class="eyebrow">VOTRE RENDEZ-VOUS AVEC L’${settings.target==='it'?'ITALIE':'APPRENTISSAGE'}</div><h2>Un petit pas.<br>Une vraie<br>conversation.</h2><p>Votre professeur s’adapte à vous.<br>Parlez, essayez, et trouvez vos mots.</p>
    <button class="button" ${resume?`data-resume="${resume.id}"`:`data-topic="${next.id}"`}>${resume?'Retrouver Sofia':'C’est parti !'} ${icon('arrow')}</button></div><img class="hero-art" src="/piazza.svg" alt="Une fenêtre ouverte sur l’Italie, un espresso et un petit Ciao !"></div>
    <button class="coffee-invitation" data-view="coffee"><span class="coffee-mark">${icon('coffee')}</span><span><strong>Une pause au salon café ?</strong><small>Un livre, une idée, votre journée… parlons de ce qui vous intéresse.</small></span>${icon('arrow')}</button>
    <div class="section-heading"><div><h2>Votre chemin, à votre rythme</h2><p>De petites conversations pour de grandes envies.</p></div><span class="eyebrow">${settings.level} · ${names[settings.target]}</span></div>
    <div class="unit-tabs" role="group" aria-label="Unités du parcours">${['Les premiers pas','Au quotidien','Un peu plus loin'].map((name,i)=>`<button class="unit-tab ${state.unit===i+1?'active':''}" data-unit="${i+1}">${String(i+1).padStart(2,'0')} &nbsp; ${name}</button>`).join('')}</div>
    <div class="unit-caption">${icon('leaf')} ${['Les bases prennent vie, un échange à la fois.','Des situations que vous aurez envie de revivre.','Des histoires, des opinions, et surtout vos idées.'][state.unit-1]}</div>
    <div class="topic-list">${topics.filter(t=>t.unit===state.unit).map(t=>topicCard(t,t.id===next.id)).join('')}</div>
    <div class="all-topics-note">${icon('spark')} Tous les sujets sont ouverts. Suivez votre curiosité.</div></section>
    <aside class="right-rail"><section class="panel"><div class="panel-title"><h3>Un peu chaque jour</h3>${icon('sun')}</div>
    <div class="goal-ring"><svg viewBox="0 0 120 120" aria-hidden="true"><circle class="track" cx="60" cy="60" r="51"/><circle class="value" cx="60" cy="60" r="51" stroke-dasharray="${percent*320.4} 320.4"/></svg><div class="goal-text"><strong>${stats.today_xp}<span style="font-size:15px;color:#a8b298"> / ${settings.daily_goal}</span></strong><span>XP aujourd’hui</span></div></div><p class="goal-message">${percent>=1?'Objectif atteint. Bravissimo !':'Chaque échange vous fait avancer.'}</p>
    <div class="week-dots">${stats.week.map((day,i)=>`<div class="week-day ${day.xp?'done':''} ${i===6?'today':''}"><i>${day.xp?'✓':'·'}</i>${dayNames[new Date(day.day+'T12:00:00').getDay()]}</div>`).join('')}</div></section>
    <section class="panel notebook-panel"><div class="panel-title"><h3>Les mots qui restent</h3>${icon('bookmark')}</div><div class="notebook-word">${word?esc(word.text):'Un carnet à vous.'}</div><div class="notebook-translation">${word?esc(word.translation):'Vos découvertes méritent une place.'}</div><p>${word?`${bookmarks.length} expression${bookmarks.length>1?'s':''} sauvegardée${bookmarks.length>1?'s':''}. ${stats.due} à revoir aujourd’hui.`:'Gardez un mot, une phrase, une façon de dire. Retrouvez-les quand vous en avez besoin.'}</p><div class="mini-divider"></div><button class="text-button" data-view="notebook">Ouvrir mon carnet ${icon('arrow')}</button></section>
    ${notesPanel(state.data.memory?.notes)}<section class="panel tutor-panel"><div class="avatar">${esc(teacherInfo().initial)}</div><div><h3>Faites connaissance avec Sofia</h3><p>À votre écoute, pour apprendre à votre rythme.</p><div class="online-label"><i></i> Votre professeur personnel</div></div></section>
    <div class="tip-card">${icon('headphones')}<p><strong>Un conseil tout simple</strong>Dites les mots à voix haute, même doucement. Ils deviennent un peu plus les vôtres.</p></div></aside></div>`;
}
function renderNotebook() {
  if (state.review) return renderReview();
  const books = state.data.bookmarks.filter(b => `${b.text} ${b.translation} ${b.note}`.toLowerCase().includes(state.search.toLowerCase()));
  $('#app').innerHTML = `<div class="page-intro"><div class="eyebrow">LES MOTS QUI VOUS ACCOMPAGNENT</div><h1>Mon petit carnet</h1><p>Une expression entendue. Un mot à retrouver. Un souvenir de conversation.</p></div>
    <div class="view-toolbar"><input id="book-search" class="input search" placeholder="Chercher un mot, une expression…" aria-label="Chercher dans le carnet" value="${esc(state.search)}"><div style="display:flex;gap:10px"><button class="button secondary" data-action="add-word">${icon('plus')} Ajouter</button><button class="button" data-action="review" ${state.data.stats.due?'':'disabled'}>Réviser · ${state.data.stats.due}</button></div></div>
    ${books.length?`<div class="book-grid">${books.map(b=>`<article class="word-card"><div class="word-heading"><h3>${esc(b.text)}</h3><button class="icon-button" data-speak-book="${b.id}" aria-label="Écouter cette expression">${icon('volume')}</button></div><p>${esc(b.translation)}</p>${b.english?`<p class="english">EN · ${esc(b.english)}</p>`:''}${b.note?`<p class="word-note">${esc(b.note)}</p>`:''}<div class="word-card-bottom"><span class="due-pill">${b.due<=localDay()?'À revoir':`À revoir le ${new Date(b.due+'T12:00:00').toLocaleDateString('fr-FR',{day:'numeric',month:'short'})}`}</span><div><button class="icon-button" data-edit-book="${b.id}" aria-label="Modifier la note">${icon('book')}</button><button class="icon-button" data-delete-book="${b.id}" aria-label="Supprimer cette expression">${icon('trash')}</button></div></div></article>`).join('')}</div>`:
    `<div class="empty-state">${icon('bookmark')}<h3>${state.search?'Aucun mot ne correspond.':'Vos premiers mots vous attendent.'}</h3><p>En conversation, touchez « Garder » pour retrouver une expression ici. Vous pouvez aussi ajouter vos propres découvertes.</p><button class="button" data-action="add-word">Ajouter une expression ${icon('plus')}</button></div>`}`;
  $('#book-search').addEventListener('input', event => { const position=event.target.selectionStart; state.search=event.target.value; renderNotebook(); $('#book-search').focus(); $('#book-search').setSelectionRange(position,position); });
}
function localDay() { const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function renderReview() {
  const review = state.review, item=review.items[review.index];
  if(!item) { $('#app').innerHTML=`<div class="review-card panel"><div class="completion-icon">✳</div><h1>Les mots reviennent.</h1><p class="muted" style="margin:15px 0">${review.index} expression(s) revue(s). Retrouvez-les à leur prochaine échéance.</p><button class="button" data-action="end-review">Retour au carnet</button></div>`; return; }
  $('#app').innerHTML=`<div class="page-intro"><div class="eyebrow">UN PETIT RENDEZ-VOUS AVEC VOS MOTS</div><h1>Ça vous revient ?</h1><p>Essayez de retrouver le sens avant de retourner la carte.</p></div><section class="review-card panel"><div class="review-counter">${review.index+1} / ${review.items.length} · ${flags[item.target]}</div><h2>${esc(item.text)}</h2><button class="icon-button" data-speak-book="${item.id}" aria-label="Écouter">${icon('volume')}</button>${review.revealed?`<div class="review-answer">${esc(item.translation)}<p class="subtle" style="margin-top:12px">${esc(item.english)}</p></div><div class="review-actions"><button class="button secondary" data-grade="again">Encore un peu</button><button class="button" data-grade="good">Je m’en souviens ${icon('check')}</button></div>`:`<div class="review-actions"><button class="button secondary" data-action="reveal">Voir le sens</button></div>`}</section><button class="text-button" data-action="end-review">Quitter la révision</button>`;
}
function renderProgress() {
  const {stats,settings,sessions,bookmarks}=state.data; const done=sessions.filter(s=>s.finished); const max=Math.max(30,...stats.week.map(d=>d.xp));
  $('#app').innerHTML=`<div class="page-intro"><div class="eyebrow">LES PETITS PAS COMPTENT</div><h1>Regardez le chemin parcouru.</h1><p>Votre pratique en ${names[settings.target]}, conversation après conversation.</p></div><div class="stats-grid">${[['spark',stats.xp,'XP de pratique'],['flame',stats.streak,'jours de suite'],['check',stats.lessons,'leçons terminées'],['bookmark',bookmarks.length,'expressions gardées']].map(([ic,val,label])=>`<div class="stat-card">${icon(ic)}<strong>${val}</strong><span>${label}</span></div>`).join('')}</div>
    <div class="progress-layout"><section class="panel"><div class="panel-title"><h3>Votre semaine en mots</h3><span class="eyebrow">XP / JOUR</span></div><div class="chart">${stats.week.map(d=>`<div class="bar-wrap"><span>${d.xp||'–'}</span><div class="bar" style="height:${Math.max(3,d.xp/max*110)}px"></div><span class="bar-label">${new Date(d.day+'T12:00:00').toLocaleDateString('fr-FR',{weekday:'short'})}</span></div>`).join('')}</div></section><section class="panel"><div class="panel-title"><h3>Votre niveau de travail</h3><span class="level-label">${settings.level}</span></div><div class="level-path">${['A0','A1','A2','B1','B2'].map((level,i)=>`<div class="level-step ${i<=['A0','A1','A2','B1','B2'].indexOf(settings.level)?'on':''}" title="${level}"></div>`).join('')}</div><p class="subtle">Sofia adapte la difficulté à vos réponses. Le niveau choisi est un repère de pratique, pas une certification.</p><button class="text-button" data-view="settings" style="margin-top:20px">Ajuster mon niveau ${icon('arrow')}</button></section>
    ${notesPanel(state.data.memory?.notes)}<section class="panel" style="grid-column:1/-1"><div class="section-heading"><h3>Vos dernières conversations</h3><button class="text-button" data-action="export">${icon('download')} Exporter mes données</button></div>${sessions.length?sessions.slice(0,12).map(s=>`<div class="history-item"><div><strong>${esc(s.mode==='coffee'?'☕ '+(s.subject||'Le salon café'):state.data.topics.find(t=>t.id===s.topic)?.title)}</strong><p>${new Date(s.started).toLocaleDateString('fr-FR',{day:'numeric',month:'long'})} · ${s.turns} réponses · ${s.mode==='coffee'?'Salon café · discussion libre':s.finished?'Leçon validée · conversation ouverte':'Leçon en cours'}</p></div><div style="text-align:right"><span>+${s.xp} XP</span><br><button class="text-button" data-resume="${s.id}">Reprendre ${icon('arrow')}</button></div></div>`).join(''):'<p class="subtle" style="padding:20px 0">Votre première conversation écrira le début de cette histoire.</p>'}</section></div>`;
}
function renderSettings() {
  const s=state.data.settings, h=state.health;
  $('#app').innerHTML=`<div class="page-intro"><div class="eyebrow">À VOTRE FAÇON</div><h1>Un professeur qui vous ressemble.</h1><p>Vos langues, votre rythme, et ce qui vous aide à apprendre.</p></div><div class="settings-grid"><form id="settings-form" class="panel settings-form">
    <div class="field-row"><div class="field"><label for="base">Ma langue d’appui</label><select class="input" id="base" name="base"><option value="fr" ${s.base==='fr'?'selected':''}>Français d’abord</option><option value="en" ${s.base==='en'?'selected':''}>English first</option></select><small>Ce choix s’applique aussi aux conversations en cours. En français, Help in English reste disponible.</small></div><div class="field"><label for="level">Mon niveau de travail</label><select class="input" id="level" name="level">${[['A0','Je commence'],['A1','Quelques bases'],['A2','Je me débrouille'],['B1','Je converse'],['B2','J’approfondis']].map(([l,n])=>`<option ${s.level===l?'selected':''} value="${l}">${l} · ${n}</option>`).join('')}</select></div></div>
    <label class="toggle-row"><span>Adapter les leçons à mes réponses<small>Simplifier quand je bloque, avancer quand je suis à l’aise.</small></span><input type="checkbox" name="auto_adapt" ${s.auto_adapt?'checked':''}></label>
    <div class="field"><label for="instructions">Ce que Sofia devrait retenir</label><textarea class="input" name="instructions" id="instructions" maxlength="1500" placeholder="J’aime voyager et cuisiner. Corrige doucement mes articles. Reviens sur le passé composé…">${esc(s.instructions)}</textarea><small>Ces consignes accompagnent chaque leçon. Vos retours sur les réponses restent aussi dans votre export.</small></div>
    <div class="field-row"><div class="field"><label for="daily_goal">Mon objectif quotidien</label><select class="input" id="daily_goal" name="daily_goal">${[10,20,30,50,100].map(n=>`<option value="${n}" ${s.daily_goal===n?'selected':''}>${n} XP · ${n/10} échanges</option>`).join('')}</select></div><div class="field"><label for="speech_rate">Débit de la voix</label><select class="input" id="speech_rate" name="speech_rate">${[[1.3,'Tout doucement'],[1.1,'Un peu plus lent'],[1,'Naturel'],[.85,'Plus rapide']].map(([v,n])=>`<option value="${v}" ${s.speech_rate===v?'selected':''}>${n}</option>`).join('')}</select></div></div>
    <label class="toggle-row"><span>Écouter les réponses de Sofia<small>Dialogue et explications utiles, avec les voix locales.</small></span><input type="checkbox" name="auto_speak" ${s.auto_speak?'checked':''}></label>
    <label class="toggle-row"><span>Lire aussi les traductions automatiquement<small>Désactivé : touchez Écouter FR ou Listen EN sous une phrase. Les consignes du professeur restent parlées.</small></span><input type="checkbox" name="auto_translate" ${s.auto_translate?'checked':''}></label>
    <label class="toggle-row"><span>Une touche d’humour<small>Quelques sourires dans la conversation, toujours bienveillants.</small></span><input type="checkbox" name="humor" ${s.humor?'checked':''}></label>
    <div class="field-row"><div class="field"><label for="audio_mode">Écoute du microphone</label><select class="input" id="audio_mode" name="audio_mode"><option value="native" ${s.audio_mode==='native'?'selected':''}>Gemma · audio direct</option><option value="whisper" ${s.audio_mode==='whisper'?'selected':''}>Whisper puis Gemma</option></select><small>Audio direct : un seul appel au professeur.</small></div><div class="field"><label for="pause_ms">Pause avant de répondre</label><select class="input" id="pause_ms" name="pause_ms">${[[450,'Rapide · 0,45 s'],[650,'Naturelle · 0,65 s'],[1000,'Prendre mon temps · 1 s'],[1500,'Réfléchir · 1,5 s']].map(([v,n])=>`<option value="${v}" ${s.pause_ms===v?'selected':''}>${n}</option>`).join('')}</select><small>En mode voix ouverte uniquement.</small></div></div>
    <div class="field"><label for="mic_device">Microphone</label><select id="mic_device" name="mic_device" class="input"><option value="${esc(s.mic_device)}">${s.mic_device?'Microphone sélectionné':'Microphone système par défaut'}</option></select><button class="text-button" type="button" data-action="microphones">Afficher les microphones</button></div>
    <div class="field"><label for="model">Le modèle local de Sofia</label><select class="input" id="model" name="model">${(h?.models?.length?h.models:[{name:s.model}]).map(m=>`<option value="${esc(m.name)}" ${m.name===s.model?'selected':''}>${esc(m.name)} ${m.parameters?`· ${esc(m.parameters)}`:''}</option>`).join('')}</select><small>Les modèles cloud sont exclus. Aucune installation automatique.</small></div>
    <button class="button" type="submit">Enregistrer mes préférences ${icon('check')}</button></form>
    <aside><section class="panel"><div class="panel-title"><h3>Tout se passe ici.</h3>${icon('lock')}</div><dl class="system-list"><div><dt>Professeur</dt><dd>${h?.online?'Disponible':'À vérifier'}</dd></div><div><dt>Calcul du modèle</dt><dd>${esc(h?.placement||'En attente')}</dd></div><div><dt>Mémoire GPU du modèle</dt><dd>${h?.vram_mb?`${h.vram_mb} Mo`:'Non chargé'}</dd></div><div><dt>Audio natif</dt><dd>${h?.audio?'Pris en charge':'Indisponible'}</dd></div><div><dt>Voix Piper</dt><dd>CPU · local</dd></div><div><dt>Whisper</dt><dd>${h?.whisper?'Installé · CPU':'Non installé'}</dd></div><div><dt>Stockage</dt><dd>SQLite · cet ordinateur</dd></div></dl><div class="privacy-note"><strong>Vos mots vous appartiennent.</strong>Conversations, progrès et carnet sont enregistrés ici. Les enregistrements du micro sont traités en mémoire ; ils ne sont pas conservés. Aucun service de reconnaissance vocale du navigateur n’est utilisé.</div><div class="settings-actions"><button class="button secondary small" data-action="diagnostic">Vérifier</button><button class="button secondary small" data-action="warmup">Préparer Sofia</button></div></section><section class="panel" style="margin-top:20px"><h3>La suite de votre apprentissage</h3><p class="subtle" style="margin:12px 0">Exportez vos conversations, corrections, consignes et retours pour une sauvegarde ou pour préparer de meilleures leçons avec un futur modèle.</p><button class="text-button" data-action="export">${icon('download')} Exporter toutes mes données</button></section></aside></div>`;
  $('#settings-form').addEventListener('submit',saveSettings);
  const panel=document.createElement('section');panel.className='panel phone-panel';
  $('.settings-grid>aside').prepend(panel);
  renderPhonePanel(panel,state.data.network);
  updatePhonePanel(panel);
  const note=document.createElement('section');note.className='panel teacher-note';
  note.innerHTML='<h3>À propos des voix</h3><p>Trois voix italiennes distinctes. Leur région n’est pas certifiée : elles ne sont pas étiquetées romaine ou sicilienne. Les voix françaises et anglaises restent les mêmes.</p><p>Les boutons « Autre voix » relisent exactement la même phrase sans changer votre professeur ni vos progrès.</p>';
  $('.settings-grid>aside').append(note);
}
function renderPhonePanel(panel,network){
  const snapshot=JSON.stringify(network);
  if(panel.dataset.network===snapshot)return;
  panel.dataset.network=snapshot;
  panel.innerHTML=`<h3>Sur mon téléphone</h3><p>Même Wi-Fi, même professeur, mêmes profils.</p>${network?.enabled&&network.urls.length?`<p>Installez une fois le certificat local sur le téléphone pour parler avec Sofia.</p>${network.setup_urls.map(url=>`<a class="phone-link" href="${esc(url)}" target="_blank" rel="noreferrer" data-verbatim>${esc(url)}</a>`).join('')}<small>Adresse pour les conversations avec le microphone :</small>${network.urls.map(url=>`<a class="phone-link" href="${esc(url)}" target="_blank" rel="noreferrer" data-verbatim>${esc(url)}</a>`).join('')}<p>Un seul modèle est partagé. Les appareils de ce Wi-Fi peuvent accéder aux profils.</p>`:network?.enabled?'<p>Partage activé. Connectez l’ordinateur au Wi-Fi : l’adresse apparaîtra automatiquement en quelques secondes.</p>':'<p>Sur l’ordinateur, arrêtez le service puis lancez <code>./start_teacher.sh --lan</code> pour activer le partage Wi-Fi.</p>'}`;
}
async function updatePhonePanel(panel){
  if(!panel.isConnected)return;
  if(!document.hidden){
    try{
      const network=await api('/api/network');
      if(!panel.isConnected)return;
      state.data.network=network;renderPhonePanel(panel,network);
    }catch{/* Keep the last known address during a brief disconnection. */}
  }
  setTimeout(()=>updatePhonePanel(panel),5000);
}
async function saveSettings(event) {
  event.preventDefault(); const form=event.target, raw=new FormData(form), data=Object.fromEntries(raw);
  for(const key of ['daily_goal','speech_rate','pause_ms']) data[key]=Number(data[key]);
  for(const key of ['auto_adapt','auto_speak','auto_translate','humor']) data[key]=form.elements[key].checked;
  try { await api('/api/settings',data); await refresh(); await checkHealth(); renderSettings(); toast('Vos préférences sont enregistrées.'); }
  catch(error) { toast(errorText(error)); }
}
function showModal(html) { $('#modal-content').innerHTML=html; $('#modal').showModal(); }
function wordModal(book={}) {
  showModal(`<h2>${book.id?'Votre expression':'Une nouvelle découverte'}</h2><p>Gardez ce que vous avez envie de retrouver.</p><form id="word-form"><div class="field"><label for="word-text">Mot ou expression</label><input required class="input" id="word-text" name="text" maxlength="1600" value="${esc(book.text||'')}"></div><div class="field"><label for="word-translation">Sens en ${names[state.data.settings.base]}</label><input class="input" id="word-translation" name="translation" maxlength="2000" value="${esc(book.translation||'')}"></div><div class="field"><label for="word-english">English, if it helps</label><input class="input" id="word-english" name="english" maxlength="2000" value="${esc(book.english||'')}"></div><div class="field"><label for="word-note">Un contexte, une astuce, un souvenir</label><textarea class="input" id="word-note" name="note" maxlength="2000">${esc(book.note||'')}</textarea></div><button class="button" type="submit">Garder dans mon carnet ${icon('bookmark')}</button></form>`);
  if(book.id) $('#word-text').readOnly=true;
  const translateButton=document.createElement('button');translateButton.type='button';translateButton.className='text-button';translateButton.style.marginTop='10px';translateButton.textContent='Traduire cette expression avec Sofia';$('#word-text').after(translateButton);
  translateButton.onclick=async()=>{translateButton.disabled=true;translateButton.textContent='Sofia traduit…';try{const value=await api('/api/translate',{text:$('#word-text').value,source:book.target||state.data.settings.target,base:state.session?.base||state.data.settings.base});$('#word-translation').value=value.translation;$('#word-english').value=value.english;}catch(error){toast(errorText(error));}finally{translateButton.disabled=false;translateButton.textContent='Traduire cette expression avec Sofia';}};
  $('#word-form').addEventListener('submit',async event=>{event.preventDefault();try{await api('/api/bookmarks',{...Object.fromEntries(new FormData(event.target)),target:book.target||state.data.settings.target});$('#modal').close();await refresh();if(state.view==='notebook')renderNotebook();toast('Une expression de plus dans votre carnet.');}catch(error){toast(errorText(error));}});
}
async function exportData() { const data=await api('/api/export');const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`parliamo-${data.profile.id}-${localDay()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000); }

const coffeeIdeas=[
  {icon:'book',title:'Le livre du moment',subject:'Le livre que je lis en ce moment',description:'Une idée, un personnage, une page qui vous reste.'},
  {icon:'spark',title:'Maths & découvertes',subject:'Les idées dans mes livres de mathématiques',description:'Une démonstration, une intuition, une question.'},
  {icon:'chat',title:'Cinéma & culture',subject:'Les films et les artistes qui m’intéressent',description:'Un film, un artiste, une œuvre qui vous parle.'},
  {icon:'sun',title:'La vie, tout simplement',subject:'Les petits événements de ma journée',description:'Ce qui vous amuse, vous étonne ou vous occupe.'}
];
function renderCoffee() {
  if(state.session?.mode==='coffee')return renderConversation();
  const recent=state.data.sessions.filter(s=>s.mode==='coffee').slice(0,4);
  $('#app').innerHTML=`<div class="coffee-welcome"><div><div class="eyebrow">UN CAFÉ, UNE IDÉE, UNE CONVERSATION</div><h1>Installez-vous.<br>De quoi a-t-on envie de parler ?</h1><p>Votre livre de maths, un film, une pensée du jour.<br>Sofia suit vos idées et vous aide à trouver vos mots en ${esc(names[state.data.settings.target])}.</p></div><div class="coffee-emblem" aria-hidden="true">${icon('coffee')}<span>un caffè con Sofia</span></div></div>
    <div class="coffee-grid"><section><form id="coffee-form" class="panel coffee-form"><label for="coffee-subject">Qu’avez-vous en tête ?</label><textarea class="input" id="coffee-subject" maxlength="400" rows="3" placeholder="Je lis un livre sur la théorie des groupes. J’aimerais parler de ce qui me fascine…"></textarea><small>Vous pouvez présenter le sujet en français, en anglais ou en italien.</small><div class="coffee-form-actions"><button type="submit" class="button">Retrouver Sofia ${icon('arrow')}</button><button type="button" class="text-button" data-action="coffee-open">Commençons simplement</button></div></form>
    <div class="section-heading"><h2>Une petite étincelle ?</h2><span class="eyebrow">SUIVEZ VOTRE CURIOSITÉ</span></div><div class="coffee-ideas">${coffeeIdeas.map((idea,i)=>`<button class="coffee-idea" data-coffee-idea="${i}"><span>${icon(idea.icon)}</span><strong>${esc(idea.title)}</strong><p>${esc(idea.description)}</p>${icon('arrow')}</button>`).join('')}</div></section>
    <aside class="right-rail"><section class="panel coffee-note"><div class="panel-title"><h3>La discussion vous appartient.</h3>${icon('leaf')}</div><p>Changez de sujet quand vous voulez. Sofia échange avec vous, pose des questions et rebondit sur vos idées.</p><p>Vos corrections, vos mots à garder et l’aide en français ou en anglais restent à portée de main.</p><div class="memory-next">${icon('bookmark')}<span>Les conversations et leurs notes sont sauvegardées pour la prochaine fois.</span></div></section>${recent.length?`<section class="panel coffee-history"><div class="panel-title"><h3>Nos dernières pauses</h3>${icon('clock')}</div>${recent.map(session=>`<button class="coffee-resume" data-resume="${session.id}"><strong>${esc(session.subject||'Une conversation avec Sofia')}</strong><small>${session.turns} échanges · ${new Date(session.started).toLocaleDateString('fr-FR',{day:'numeric',month:'short'})}</small><span>Reprendre ${icon('arrow')}</span></button>`).join('')}</section>`:''}</aside></div>`;
  $('#coffee-form').onsubmit=event=>{event.preventDefault();startCoffee($('#coffee-subject').value).catch(error=>toast(errorText(error)));};
}
async function startCoffee(subject='') {
  if(state.busy||state.translating)return;
  state.busy=true;
  try {
    await stopRecording(false);audioPlayer.stop();state.handsfree=false;
    state.session=await api('/api/sessions',{mode:'coffee',subject});
    localStorage.setItem(sessionKey(),state.session.id);state.view='coffee';render();
  } finally {state.busy=false;}
  await sendTurn('start');
}
function coffeeTopicModal() {
  if(state.busy||state.translating)return;
  state.handsfree=false;stopRecording(false);audioPlayer.stop();if($('#handsfree'))$('#handsfree').checked=false;
  showModal(`<h2>Suivons une autre idée.</h2><p>La même conversation, un nouveau sujet.</p><form id="coffee-topic-form"><div class="field"><label for="coffee-next-subject">De quoi voulez-vous parler ?</label><textarea class="input" id="coffee-next-subject" required maxlength="400" rows="3" placeholder="Un autre livre, un souvenir, une question…"></textarea></div><button class="button" type="submit">Parlons-en ${icon('arrow')}</button></form>`);
  $('#coffee-topic-form').onsubmit=event=>{event.preventDefault();const subject=$('#coffee-next-subject').value.trim();if(!subject)return;$('#modal').close();sendTurn('topic',subject);};
}
function coffeeSidebar(session) {
  return `<section class="panel coffee-note"><div class="panel-title"><h3>À notre table</h3>${icon('coffee')}</div><p class="coffee-subject" id="coffee-current-subject">${esc(session.subject||'Au fil de vos envies')}</p><p class="subtle">Suivez vos idées. Une question, une anecdote, un changement de sujet : Sofia reste avec vous.</p><p class="coffee-count" id="coffee-count">${session.turns} échanges · vos mots font leur chemin</p><button class="button secondary small" data-action="coffee-topic">Changer de sujet ${icon('spark')}</button><button class="text-button" data-action="coffee-lobby" style="margin-top:17px">Les autres tables ${icon('arrow')}</button></section>`;
}

function renderConversation() {
  const session=state.view==='conversation'&&state.session?.mode==='coffee'?null:state.session;
  if(!session) { $('#app').innerHTML=`<div class="page-intro"><div class="eyebrow">UN SUJET, MILLE FAÇONS DE LE DIRE</div><h1>De quoi parle-t-on ?</h1><p>Choisissez une situation. Sofia vous y retrouve, à votre niveau.</p></div><div class="book-grid">${state.data.topics.map(t=>topicCard(t,false)).join('')}</div>`;return; }
  const coffee=session.mode==='coffee';
  const topic=state.data.topics.find(t=>t.id===session.topic);
  const last=[...session.messages].reverse().find(m=>m.role==='assistant');state.lastResult=last?.payload||null;
  $('#app').innerHTML=`<div class="conversation-layout"><section class="chat-panel ${coffee?'coffee-chat':''}"><header class="chat-header"><div class="avatar">${esc(teacherInfo().initial)}</div><div><h3>Sofia · ${coffee?'le salon café':esc(topic.title)}</h3><p id="chat-language-caption">${flags[session.target]} ${esc(names[session.target])} · appui en ${esc(names[session.base])}</p></div><div class="chat-header-actions"><span class="level-label">${session.level}</span><button class="icon-button" data-action="stop-audio" aria-label="Arrêter la voix et la réponse" title="Arrêter la voix et la réponse">${icon('stop')}</button></div></header>
    <div id="messages" class="messages" role="log" aria-live="polite" aria-label="Conversation avec Sofia">${chatIntro(session)}${session.messages.map(renderMessage).join('')}<div id="live-response"></div></div>
    <div id="lesson-milestone" class="lesson-milestone" role="status"></div><div class="composer-wrap"><div class="help-row"><button class="help-chip" data-help="hint">Un petit indice</button><button class="help-chip" data-help="simplify">Plus simple, s’il vous plaît</button>${session.base==='fr'?'<button class="help-chip" data-help="english">Help in English</button>':''}</div><div class="voice-indicator" id="voice-indicator"></div><form id="composer" class="composer"><button class="mic-button" type="button" id="mic-button" aria-label="Commencer un enregistrement" title="Cliquez pour parler, recliquez pour envoyer">${icon('mic')}</button><textarea id="chat-input" aria-label="Votre réponse" placeholder="Écrivez… ou osez le dire à voix haute." maxlength="2500" rows="1"></textarea><button class="button send-button" type="submit" aria-label="Envoyer">${icon('send')}</button></form><div class="composer-meta"><label class="voice-toggle"><input type="checkbox" id="handsfree" ${state.handsfree?'checked':''}> Voix ouverte</label><span id="turn-status">Votre micro reste sur cet ordinateur</span></div></div></section>
    <aside class="lesson-side">${coffee?coffeeSidebar(session):`<section class="panel"><div class="panel-title"><h3>Votre petite mission</h3>${icon(topic.icon)}</div><p class="lesson-goal">${esc(topic.description)}</p><div class="lesson-counter" id="lesson-counter">${[0,1,2].map(i=>`<span class="${session.turns>i?'filled':''}"></span>`).join('')}</div><p class="subtle" id="turn-count">${session.turns} échange${session.turns>1?'s':''} · 3 réponses minimum · validation selon vos acquis</p><button class="button secondary small" id="finish-button" data-action="finish" ${session.turns<3||session.finished?'disabled':''}>${icon('check')} Valider et continuer</button><button class="text-button" data-action="choose-topic" style="margin-top:17px">Choisir un autre sujet ${icon('arrow')}</button></section>`}

    <div id="level-suggestion"></div><div id="teacher-notes"></div><section class="panel notebook-panel" id="phrase-panel"></section><section class="panel" id="correction-panel"></section><div class="metrics" id="metrics">Audio ${state.data.settings.audio_mode==='native'?'direct vers Gemma':'via Whisper'} · réponse progressive<br>La difficulté suit votre compréhension.</div></aside></div>`;
  renderLessonDetails();
  { $('#composer').addEventListener('submit',event=>{event.preventDefault();const input=$('#chat-input');const text=input.value.trim();if(text&&!state.busy){input.value='';sendTurn('reply',text);}});$('#chat-input').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();$('#composer').requestSubmit();}});$('#handsfree').addEventListener('change',event=>{state.handsfree=event.target.checked;if(state.handsfree)maybeListen();else stopRecording(false);}); }
  scrollChat();
}
function chatIntro(session) {
  return `<div class="chat-date">Un espace pour essayer. Les erreurs sont les bienvenues.${session.older_messages?`<br>${session.older_messages} messages plus anciens conservés dans votre export. Sofia garde le fil avec ses notes.`:''}</div>`;
}
function notesPanel(notes) {
  if(!notes?.summary)return '';
  return `<section class="panel memory-panel"><div class="panel-title"><h3>Le fil avec Sofia</h3>${icon('book')}</div><p>${esc(notes.summary)}</p>${notes.strengths?.length?`<div class="memory-label">CE QUI PROGRESSE</div><p>${notes.strengths.map(esc).join(' · ')}</p>`:''}${notes.practice?.length?`<div class="memory-label">À REPRENDRE ENSEMBLE</div><p>${notes.practice.map(esc).join(' · ')}</p>`:''}${notes.next_step?`<div class="memory-next">${icon('arrow')} <span>${esc(notes.next_step)}</span></div>`:''}<small>Notes mises à jour au fil des échanges.</small></section>`;
}
function assessmentHtml(assessment, id, teacher='sofia') {
  if(!assessment)return '';
  const verdicts={correct:'Très bien !',almost:'Presque !',needs_work:'Une piste pour progresser',unclear:'Reprenons doucement',unrated:'Un conseil de Sofia'};
  const clarity={clear:'Sens clair',partly_clear:'Sens partiellement clair',unclear:'À clarifier'};
  return `<div class="phrase-feedback ${assessment.verdict}" aria-label="Retour sur votre phrase"><div class="feedback-heading"><strong>${verdicts[assessment.verdict]||'Votre phrase'}</strong>${Number.isInteger(assessment.rating)?`<span class="phrase-score" title="Estimation du professeur pour cette phrase">${assessment.rating}<small>/5</small></span>`:''}</div>${assessment.praise?`<p>${esc(assessment.praise)}</p>`:''}${assessment.corrected?`<div class="corrected-phrase"><span>À DIRE</span><strong>${esc(assessment.corrected)}</strong><button class="icon-button" data-correction="${id}" aria-label="Écouter la phrase corrigée">${icon('volume')}</button>${state.session?.target==='it'?`<button class="slow-correction" data-correction="${id}" data-slow="true" title="Écouter lentement en italien">IT lent</button>`:''}</div>${state.session?.target==='it'?`<div class="segment-tools voice-comparison">${otherVoiceButtons(id,0,teacher,true)}</div>`:''}`:''}${assessment.explanation?`<p>${esc(assessment.explanation)}</p>`:''}${assessment.explanation||assessment.praise?`<div class="segment-tools"><button data-explanation="${id}">${icon('volume')} Explication EN</button></div><div class="requested-translation" id="explanation-${id}" aria-live="polite"></div>`:''}<small>${clarity[assessment.clarity]||''}${Number.isInteger(assessment.rating)?' · appréciation du professeur':''}</small></div>`;
}
function renderMessage(message) {
  const user=message.role==='user', result=message.payload;
  return `<article class="message ${user?'user':'assistant'}" data-message="${message.id}"><div class="message-label">${user?(result.action==='topic'?'NOUVEAU SUJET':'VOUS'):`<span data-verbatim>${esc(teacherInfo(result.teacher||'sofia').name.toUpperCase())}</span>`}${!user?' · votre professeur':''}</div><div class="bubble">${user?esc(message.content):result.segments?.map((segment,i)=>segmentHtml(segment,i,message)).join('')||esc(message.content)}</div>${user?assessmentHtml(result.assessment,message.id,result.teacher||'sofia'):`<div class="message-actions"><button data-replay="${message.id}">${icon('volume')} Réécouter</button><button data-save-message="${message.id}">${icon('bookmark')} Garder</button><button data-feedback="${message.id}">${icon('flag')} Une remarque</button></div>`}</article>`;
}
function segmentKind(segment,action='reply') {
  if(['dialogue','instruction','translation'].includes(segment.kind))return segment.kind;
  return segment.language===state.session?.target?'dialogue':['hint','simplify','english'].includes(action)?'instruction':'translation';
}
function shouldSpeak(segment,action) {
  return segmentKind(segment,action)!=='translation'||state.data.settings.auto_translate;
}
function segmentHtml(segment,index=0,message=null) {
  const kind=segmentKind(segment,message?.payload.action), target=segment.language===state.session?.target;
  return `<div class="segment ${kind==='translation'?'translation':''}"><span class="segment-language">${esc(segment.language.toUpperCase())}${kind==='instruction'?' · CONSEIL':kind==='translation'?' · TRADUCTION':''}</span>${esc(segment.text)}${message?`<div class="segment-tools"><button data-segment-play="${message.id}" data-index="${index}" title="Écouter cette phrase">${icon('volume')} ${segment.language.toUpperCase()}</button>${segment.language==='it'?`<button data-segment-play="${message.id}" data-index="${index}" data-slow="true" title="Écouter lentement en italien">${icon('clock')} IT lent</button>`:''}${target?['fr','en'].filter(l=>l!==segment.language).map(lang=>`<button data-translation="${message.id}" data-index="${index}" data-language="${lang}">${lang==='fr'?'Écouter FR':'Listen EN'}</button>`).join(''):''}</div>${segment.language==='it'?`<div class="segment-tools voice-comparison">${otherVoiceButtons(message.id,index,message.payload.teacher||'sofia')}</div>`:''}<div class="requested-translation" id="translation-${message.id}-${index}" aria-live="polite"></div>`:''}</div>`;
}
function phraseForBase(result) {
  const phrase={...result.phrase};
  if(state.data.settings.base==='en')phrase.translation=phrase.english||phrase.translation;
  else if(result.base==='en')phrase.translation='';
  return phrase;
}
function renderLessonDetails() {
  const result=state.lastResult, session=state.session;
  if(!$('#phrase-panel'))return;
  $('#phrase-panel').innerHTML=`<div class="panel-title"><h3>À glisser dans votre carnet</h3>${icon('bookmark')}</div>${result?.phrase?.text?`<p class="phrase-highlight">${esc(result.phrase.text)}</p><p class="subtle">${esc(phraseForBase(result).translation)}</p><button class="text-button" data-action="save-phrase" style="margin-top:14px">Garder cette expression ${icon('plus')}</button>`:'<p class="subtle" style="margin-top:15px">Une expression à retenir apparaîtra au fil de votre conversation.</p>'}`;
  $('#correction-panel').innerHTML=`<h3>Un petit coup de pouce</h3>${result?.correction?`<p class="correction">${esc(result.correction)}</p>`:'<p class="subtle" style="margin-top:12px">Cherchez vos mots tranquillement. Sofia vous aide, une idée à la fois.</p>'}${result?.focus?`<div class="eyebrow" style="margin-top:15px;font-size:8px;color:#a1ad8c">${esc(result.focus)}</div>`:''}`;
  if($('#coffee-current-subject'))$('#coffee-current-subject').textContent=session.subject||'Au fil de vos envies';
  if($('#coffee-count'))$('#coffee-count').textContent=`${session.turns} échanges · vos mots font leur chemin`;
  if($('#turn-count'))$('#turn-count').textContent=session.finished?`${session.turns} échanges · la conversation continue`:`${session.turns} échanges · 3 réponses minimum, puis validation selon vos acquis`;
  if($('#lesson-milestone')){$('#lesson-milestone').hidden=session.mode==='coffee'||!session.finished;$('#lesson-milestone').innerHTML=session.finished?`${icon('check')} <div><strong>Leçon validée · bravissimo !</strong><span>Continuez avec Sofia, ou choisissez un autre sujet quand vous le souhaitez.</span></div>`:'';}
  if($('#level-suggestion')){
    const scores=session.messages.filter(m=>m.role==='assistant'&&m.payload.action==='reply'&&m.payload.assessment?.rating!=null).slice(-8).map(m=>m.payload.score);
    const mean=scores.reduce((a,b)=>a+b,0)/Math.max(1,scores.length),levels=['A0','A1','A2','B1','B2'],current=levels.indexOf(session.level);
    const suggested=session.finished&&scores.length>=5?(mean>=2.8?levels[Math.min(4,current+1)]:mean<1.6?levels[Math.max(0,current-1)]:session.level):session.level;
    $('#level-suggestion').innerHTML=suggested!==session.level&&suggested!==state.data.settings.level?`<section class="panel"><h3>Pour la prochaine leçon</h3><p class="subtle" style="margin:12px 0">Vos derniers échanges suggèrent d’essayer ${suggested}. À vous de choisir votre rythme.</p><button class="button secondary small" data-suggest-level="${suggested}">Essayer ${suggested}</button></section>`:'';
  }
  if($('#teacher-notes'))$('#teacher-notes').innerHTML=notesPanel(session.notes?.summary?session.notes:state.data.memory?.notes);
  if($('#finish-button'))$('#finish-button').innerHTML=session.finished?`${icon('check')} Objectif validé`:`${icon('check')} Valider et continuer`;
  if($('#lesson-counter'))$('#lesson-counter').innerHTML=[0,1,2].map(i=>`<span class="${session.turns>i?'filled':''}"></span>`).join('');
  if($('#finish-button'))$('#finish-button').disabled=session.turns<3||!!session.finished||state.busy;
  const m=result?.metrics;if(m&&$('#metrics'))$('#metrics').innerHTML=`Premier token · ${(m.first_token_ms/1000).toFixed(1)} s<br>Réponse complète · ${(m.total_ms/1000).toFixed(1)} s<br>${m.tokens_per_second} tokens/s · ${esc(m.input==='native_audio'?'Audio direct':m.input==='whisper'?'Whisper + Gemma':'Texte')}${m.transcription_ms?`<br>Transcription · ${(m.transcription_ms/1000).toFixed(1)} s`:''}`;
}
function scrollChat() { const messages=$('#messages');if(messages)messages.scrollTop=messages.scrollHeight; }
function busyUI(busy) { state.busy=busy;$$('[data-help],#composer button,#chat-input,[data-translation],[data-segment-play],[data-replay],[data-correction],[data-explanation]').forEach(e=>e.disabled=busy||e.dataset.unavailable==='true');if($('#finish-button'))$('#finish-button').disabled=busy||state.session.turns<3||!!state.session.finished;$('#target-language').disabled=busy;$('#support-language').disabled=busy; }
async function startLesson(topic) {
  if(state.busy||state.translating)return;
  stopRecording(false);audioPlayer.stop();state.handsfree=false;
  state.session=await api('/api/sessions',{topic});localStorage.setItem(sessionKey(),state.session.id);state.view='conversation';render();await sendTurn('start');
}
async function resumeLesson(id) {
  if(state.busy||state.translating)return;
  stopRecording(false);audioPlayer.stop();state.handsfree=false;
  state.session=await api('/api/sessions/'+encodeURIComponent(id));localStorage.setItem(sessionKey(),id);state.view=state.session.mode==='coffee'?'coffee':'conversation';render();if(!state.session.messages.length&&!state.session.finished)await sendTurn('start');
}
async function sendTurn(action,text='',audio=null) {
  if(state.busy||state.translating||!state.session)return;
  await stopRecording(false);audioPlayer.stop();busyUI(true);
  state.lastRequest={action,text,audio};const controller=new AbortController();state.controller=controller;
  const live=$('#live-response');let segments=[],userNode=null,done=false;
  if(!['start','continue'].includes(action)){userNode=document.createElement('div');userNode.innerHTML=`<article class="message user"><div class="message-label">${action==='topic'?'NOUVEAU SUJET':'VOUS'}</div><div class="bubble">${esc(audio?'Message vocal…':text||({english:'Help in English',simplify:'Plus simple, s’il vous plaît',hint:'Un petit indice'}[action]))}</div></article>`;live.before(userNode);}
  live.innerHTML=`<div class="chat-loading"><span class="typing-dots"><i></i><i></i><i></i></span><span id="thinking-status">Sofia prépare sa réponse…</span></div>`;scrollChat();
  try {
    const response=await fetch('/api/turn',{method:'POST',headers:{'Content-Type':'application/json','X-Parliamo-Profile':state.profileId},body:JSON.stringify({session_id:state.session.id,action,text,...(audio?{audio}:{})}),signal:controller.signal});
    if(!response.ok){const value=await response.json();throw new Error(value.error);}
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    async function handle(event){
      if(event.type==='error')throw new Error(event.error);
      if(event.type==='status'&&$('#thinking-status'))$('#thinking-status').textContent=event.text;
      if(event.type==='transcript'&&userNode)$('.bubble',userNode).textContent=event.text;
      if(event.type==='segment'){
        segments.push(event.segment);live.innerHTML=`<article class="message assistant"><div class="message-label">SOFIA · votre professeur</div><div class="bubble">${segments.map(segment=>segmentHtml(segment)).join('')}</div></article>`;
        if(state.data.settings.auto_speak&&shouldSpeak(event.segment,action))audioPlayer.enqueue(event.segment);scrollChat();
      }
      if(event.type==='done'){
        done=true;state.session=event.session;state.lastResult=event.result;
        const messages=$('#messages');messages.innerHTML=`${chatIntro(state.session)}${state.session.messages.map(renderMessage).join('')}<div id="live-response"></div>`;
        renderLessonDetails();scrollChat();await refresh();if(event.just_completed)toast('Leçon validée ! La conversation continue.');else if(event.xp)toast(`+${event.xp} XP · Un pas de plus !`);
      }
    }
    while(true){const chunk=await reader.read();if(chunk.done)break;buffer+=decoder.decode(chunk.value,{stream:true});let index;while((index=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,index);buffer=buffer.slice(index+1);if(line.trim())await handle(JSON.parse(line));}}
    buffer+=decoder.decode();if(buffer.trim())await handle(JSON.parse(buffer));
    if(!done)throw new Error('La connexion a été interrompue avant la fin de la réponse.');
  } catch(error) {
    audioPlayer.stop();state.handsfree=false;if($('#handsfree'))$('#handsfree').checked=false;
    const message=error.name==='AbortError'?'Réponse arrêtée. Les échanges incomplets ne rapportent pas de XP.':errorText(error);
    const current=$('#live-response');if(current)current.innerHTML=`<div class="error-box">${esc(message)}<br><button class="button secondary small" data-action="retry">Réessayer</button></div>`;
    if(userNode)userNode.remove();scrollChat();
  } finally {state.controller=null;busyUI(false);renderLessonDetails();checkHealth();if(!audioPlayer.active)maybeListen();}
}
async function finishLesson() {
  if(state.busy)return;
  busyUI(true);
  await stopRecording(false);audioPlayer.stop();
  try {state.session=await api('/api/finish',{session_id:state.session.id});await refresh();renderLessonDetails();}
  finally {busyUI(false);}
  toast('Leçon validée. On garde le fil avec Sofia !');
  maybeListen();
}
async function playTranslation(button) {
  if(state.busy||state.translating)return toast('Un instant, Sofia termine sa réponse.');
  state.translating=true;busyUI(true);await stopRecording(false);audioPlayer.stop();
  const generation=audioPlayer.generation;
  const label=button.textContent;button.disabled=true;button.textContent='Traduction…';
  try {
    const value=await api('/api/message-translation',{session_id:state.session.id,message_id:button.dataset.translation,segment:Number(button.dataset.index),language:button.dataset.language});
    const output=$(`#translation-${button.dataset.translation}-${button.dataset.index}`);
    if(output){output.textContent=`${value.language.toUpperCase()} · ${value.text}`;output.classList.add('visible');}
    if(audioPlayer.generation===generation)audioPlayer.enqueue(value);
  } finally {state.translating=false;busyUI(false);button.textContent=label;if(!audioPlayer.active)maybeListen();}
}

async function playExplanation(button) {
  if(state.busy||state.translating)return;
  state.translating=true;busyUI(true);await stopRecording(false);audioPlayer.stop();
  const generation=audioPlayer.generation,label=button.innerHTML;
  button.textContent='Préparation…';
  try{
    const value=await api('/api/assessment-explanation',{session_id:state.session.id,message_id:button.dataset.explanation});
    const output=$('#explanation-'+button.dataset.explanation);
    if(output){output.textContent='EN · '+value.text;output.classList.add('visible');}
    if(audioPlayer.generation===generation)audioPlayer.enqueue(value);
  }finally{state.translating=false;busyUI(false);button.innerHTML=label;if(!audioPlayer.active)maybeListen();}
}

class AudioPlayer {
  constructor(){this.queue=[];this.active=false;this.generation=0;this.audio=null;this.element=new Audio();this.finish=null;this.resume=null;}
  enqueue(segment){const generation=this.generation;const pending=api('/api/speech',{...segment,teacher:segment.teacher||state.data.settings.teacher}).then(value=>({value}),error=>({error}));this.queue.push({pending,generation});if(!this.active)this.pump();}
  async pump(){
    const generation=this.generation;this.active=true;
    while(this.queue.length&&generation===this.generation){
      const {pending}=this.queue.shift();const {value,error}=await pending;if(generation!==this.generation)return;
      if(error){toast('Voix indisponible : '+errorText(error));continue;}
      const audio=this.element;audio.src=value.url;this.audio=audio;
      try{await new Promise((resolve,reject)=>{
        this.finish=resolve;audio.onended=resolve;audio.onerror=()=>reject(new Error('Lecture audio impossible.'));
        this.resume=()=>audio.play().then(()=>{$('#audio-permission').hidden=true;}).catch(error=>{
          if(generation!==this.generation)return;
          if(error.name==='NotAllowedError')$('#audio-permission').hidden=false;else reject(error);
        });
        this.resume();
      });}
      catch(error){toast(errorText(error));}
      $('#audio-permission').hidden=true;
      if(generation!==this.generation)return;
    }
    this.active=false;this.audio=null;this.finish=null;this.resume=null;maybeListen();
  }
  stop(){this.generation++;this.queue=[];$('#audio-permission').hidden=true;if(this.audio){this.audio.onended=null;this.audio.onerror=null;this.audio.pause();this.audio.removeAttribute('src');this.audio.load();}if(this.finish)this.finish();this.audio=null;this.finish=null;this.resume=null;this.active=false;}
}
const audioPlayer=new AudioPlayer();
function voiceStatus(text){if($('#voice-indicator'))$('#voice-indicator').textContent=text;}
function maybeListen(){if(state.handsfree&&!state.busy&&!audioPlayer.active&&!state.recorder&&['conversation','coffee'].includes(state.view)&&!state.translating&&state.session)startRecording(true);}
async function startRecording(automatic=false){
  if(state.busy||state.translating||state.recorder)return;
  audioPlayer.stop();
  const rec={frames:[],preroll:[],rate:48000,started:performance.now(),lastSpeech:0,voiced:0,noise:.002,automatic,active:false,stream:null,context:null,node:null};state.recorder=rec;
  try{
    if(!navigator.mediaDevices?.getUserMedia)throw new Error('Pour le micro sur téléphone, ouvrez l’adresse HTTPS après la configuration du certificat dans Préférences.');
    voiceStatus('Autorisez le microphone pour commencer.');
    const constraints={echoCancellation:true,noiseSuppression:true,autoGainControl:true};
    let stream;
    try{stream=await navigator.mediaDevices.getUserMedia({audio:{...constraints,...(state.data.settings.mic_device?{deviceId:{exact:state.data.settings.mic_device}}:{})}});}
    catch(error){if(!state.data.settings.mic_device||!['OverconstrainedError','NotFoundError'].includes(error.name))throw error;stream=await navigator.mediaDevices.getUserMedia({audio:constraints});}
    if(state.recorder!==rec){stream.getTracks().forEach(t=>t.stop());return;}
    rec.stream=stream;const context=new AudioContext();rec.context=context;rec.rate=context.sampleRate;
    await context.audioWorklet.addModule('/capture.js');await context.resume();
    if(state.recorder!==rec){stream.getTracks().forEach(t=>t.stop());await context.close();return;}
    const source=context.createMediaStreamSource(stream),node=new AudioWorkletNode(context,'pcm-recorder');rec.node=node;
    const mute=context.createGain();mute.gain.value=0;source.connect(node);node.connect(mute);mute.connect(context.destination);
    rec.started=performance.now();
    $('#mic-button')?.classList.add('recording');$('#mic-button')?.setAttribute('aria-label','Terminer et envoyer l’enregistrement');
    voiceStatus(automatic?'Je vous écoute… parlez, puis faites une petite pause.':'À vous ! Recliquez sur le micro pour envoyer.');
    node.port.onmessage=event=>{
      if(state.recorder!==rec)return;
      const samples=event.data,now=performance.now(),duration=samples.length/rec.rate;
      let square=0;for(const value of samples)square+=value*value;const rms=Math.sqrt(square/samples.length);
      const voiced=rms>Math.max(.007,rec.noise*3);
      if(voiced){rec.voiced+=duration;rec.lastSpeech=now;if(!rec.active){rec.active=true;rec.frames.push(...rec.preroll);rec.preroll=[];}}
      else if(!rec.active)rec.noise=rec.noise*.98+Math.min(rms,.015)*.02;
      if(rec.active||!automatic)rec.frames.push(samples);else{rec.preroll.push(samples);if(rec.preroll.length>Math.ceil(.3*rec.rate/samples.length))rec.preroll.shift();}
      const elapsed=rec.frames.reduce((sum,f)=>sum+f.length,0)/rec.rate;
      if(elapsed>=28||(automatic&&rec.voiced>.25&&now-rec.lastSpeech>state.data.settings.pause_ms))stopRecording(true);
      else if(automatic&&!rec.active&&now-rec.started>15000){state.handsfree=false;if($('#handsfree'))$('#handsfree').checked=false;stopRecording(false);voiceStatus('Micro en pause. Réactivez la voix ouverte quand vous êtes prêt.');}
    };
  }catch(error){await stopRecording(false);state.handsfree=false;if($('#handsfree'))$('#handsfree').checked=false;toast(error.name==='NotAllowedError'?'Autorisez le microphone dans votre navigateur pour parler.':errorText(error));voiceStatus('Vous pouvez continuer en écrivant.');}
}
async function stopRecording(send=false){
  const rec=state.recorder;if(!rec)return;state.recorder=null;
  if(rec.node){rec.node.port.onmessage=null;rec.node.disconnect();}
  rec.stream?.getTracks().forEach(t=>t.stop());if(rec.context&&rec.context.state!=='closed')await rec.context.close();
  $('#mic-button')?.classList.remove('recording');$('#mic-button')?.setAttribute('aria-label','Commencer un enregistrement');voiceStatus('');
  if(send){if(rec.voiced<.2){toast('Aucune parole détectée. Approchez-vous du micro et réessayez.');state.handsfree=false;if($('#handsfree'))$('#handsfree').checked=false;return;}
    const length=rec.frames.reduce((sum,frame)=>sum+frame.length,0),samples=new Float32Array(length);let offset=0;for(const frame of rec.frames){samples.set(frame,offset);offset+=frame.length;}
    const encoded=encodeWav(samples,rec.rate);await sendTurn('reply','',encoded);
  }
}
function encodeWav(samples,rate){
  const ratio=rate/16000,length=Math.min(29*16000,Math.floor(samples.length/ratio)),buffer=new ArrayBuffer(44+length*2),view=new DataView(buffer);
  function str(offset,text){for(let i=0;i<text.length;i++)view.setUint8(offset+i,text.charCodeAt(i));}
  str(0,'RIFF');view.setUint32(4,36+length*2,true);str(8,'WAVE');str(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,length*2,true);
  for(let i=0;i<length;i++){const start=Math.floor(i*ratio),end=Math.max(start+1,Math.floor((i+1)*ratio));let sum=0;for(let j=start;j<end&&j<samples.length;j++)sum+=samples[j];const value=Math.max(-1,Math.min(1,sum/(end-start)));view.setInt16(44+i*2,value<0?value*32768:value*32767,true);}
  const bytes=new Uint8Array(buffer);let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(binary);
}

document.addEventListener('click',async event=>{
  const button=event.target.closest('button,a');if(!button)return;
  try{
    if(button.matches('.modal-close'))return $('#modal').close();
    if(button.dataset.switchProfile)return await switchProfile(button.dataset.switchProfile);
    if(button.dataset.teacherSelect)return await switchTeacher(button.dataset.teacherSelect);
    if(button.dataset.view){event.preventDefault();return setView(button.dataset.view);}
    if(button.matches('.brand')){event.preventDefault();return setView('learn');}
    if(button.dataset.coffeeIdea!==undefined)return await startCoffee(coffeeIdeas[Number(button.dataset.coffeeIdea)].subject);
    if(button.dataset.topic)return await startLesson(button.dataset.topic);
    if(button.dataset.resume)return await resumeLesson(button.dataset.resume);
    if(button.dataset.unit){state.unit=Number(button.dataset.unit);return renderLearn();}
    if(button.dataset.help)return await sendTurn(button.dataset.help);
    if(button.id==='mic-button'){if(state.recorder)return await stopRecording(true);return await startRecording(false);}
    if(button.dataset.translation)return await playTranslation(button);
    if(button.dataset.explanation)return await playExplanation(button);
    if(button.dataset.segmentPlay){if(state.busy||state.translating)return;const m=state.session.messages.find(m=>m.id===button.dataset.segmentPlay);await stopRecording(false);audioPlayer.stop();audioPlayer.enqueue({...m.payload.segments[Number(button.dataset.index)],teacher:button.dataset.voice||m.payload.teacher||'sofia',slow:button.dataset.slow==='true'});return;}
    if(button.dataset.correction){if(state.busy||state.translating)return;const m=state.session.messages.find(m=>m.id===button.dataset.correction);await stopRecording(false);audioPlayer.stop();audioPlayer.enqueue({language:state.session.target,text:m.payload.assessment.corrected,teacher:button.dataset.voice||m.payload.teacher||'sofia',slow:button.dataset.slow==='true'});return;}
    if(button.dataset.replay){if(state.busy||state.translating)return;const m=state.session.messages.find(m=>m.id===button.dataset.replay);await stopRecording(false);audioPlayer.stop();for(const s of m.payload.segments)if(shouldSpeak(s,m.payload.action))audioPlayer.enqueue({...s,teacher:m.payload.teacher||'sofia'});return;}
    if(button.dataset.saveMessage){const m=state.session.messages.find(m=>m.id===button.dataset.saveMessage);return wordModal({...phraseForBase(m.payload),target:state.session.target});}
    if(button.dataset.feedback){showModal(`<h2>Une idée pour mieux apprendre ?</h2><p>Ce retour sera conservé avec la conversation pour améliorer vos futures leçons.</p><form id="feedback-form"><div class="field"><label for="feedback-note">Votre remarque</label><textarea class="input" id="feedback-note" required maxlength="2000" placeholder="L’explication était trop longue. J’aimerais un autre exemple…"></textarea></div><button class="button" type="submit">Garder ce retour</button></form>`);const mid=button.dataset.feedback;$('#feedback-form').onsubmit=async e=>{e.preventDefault();try{await api('/api/feedback',{session_id:state.session.id,message_id:mid,note:$('#feedback-note').value});$('#modal').close();toast('Votre retour est sauvegardé.');}catch(error){toast(errorText(error));}};return;}
    if(button.dataset.speakBook){const b=state.data.bookmarks.find(b=>b.id===button.dataset.speakBook);audioPlayer.stop();audioPlayer.enqueue({text:b.text,language:b.target});return;}
    if(button.dataset.editBook)return wordModal(state.data.bookmarks.find(b=>b.id===button.dataset.editBook));
    if(button.dataset.deleteBook){const bid=button.dataset.deleteBook;showModal(`<h2>Retirer cette expression ?</h2><p>Elle sera retirée de votre carnet et de vos révisions.</p><button class="button danger" id="confirm-delete">Retirer de mon carnet</button>`);$('#confirm-delete').onclick=async()=>{try{await api('/api/bookmarks/delete',{id:bid});$('#modal').close();await refresh();renderNotebook();}catch(error){toast(errorText(error));}};return;}
    if(button.dataset.grade){const review=state.review,item=review.items[review.index];button.disabled=true;await api('/api/review',{id:item.id,remembered:button.dataset.grade==='good'});review.index++;review.revealed=false;await refresh();return renderReview();}
    if(button.dataset.suggestLevel){await api('/api/settings',{level:button.dataset.suggestLevel});await refresh();renderLessonDetails();toast('Niveau enregistré pour la prochaine leçon.');return;}
    if(button.dataset.setLevel){await api('/api/settings',{level:button.dataset.setLevel});await refresh();$('#modal').close();setView('learn');toast('Votre nouveau niveau de travail est enregistré.');return;}
    switch(button.dataset.action){
      case 'resume-audio':return audioPlayer.resume?.();
      case 'profiles':return await profilesModal();
      case 'add-word':return wordModal();
      case 'review':state.review={items:state.data.bookmarks.filter(b=>b.due<=localDay()),index:0,revealed:false};return renderReview();
      case 'reveal':state.review.revealed=true;return renderReview();
      case 'end-review':state.review=null;return renderNotebook();
      case 'export':return await exportData();
      case 'diagnostic':await checkHealth();renderSettings();return toast('Diagnostic actualisé.');
      case 'warmup':button.disabled=true;button.textContent='Préparation…';await api('/api/warmup',{});await checkHealth();renderSettings();return toast('Sofia est prête.');
      case 'microphones':{const stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(t=>t.stop());const devices=await navigator.mediaDevices.enumerateDevices();$('#mic_device').innerHTML='<option value="">Microphone système par défaut</option>'+devices.filter(d=>d.kind==='audioinput').map(d=>`<option value="${esc(d.deviceId)}" ${d.deviceId===state.data.settings.mic_device?'selected':''}>${esc(d.label||'Microphone')}</option>`).join('');return;}
      case 'save-phrase':return wordModal({...phraseForBase(state.lastResult),target:state.session.target});
      case 'coffee-open':return await startCoffee();
      case 'coffee-topic':return coffeeTopicModal();
      case 'coffee-lobby':if(state.busy||state.translating)return;state.handsfree=false;await stopRecording(false);audioPlayer.stop();state.session=null;await refresh();return renderCoffee();
      case 'finish':return await finishLesson();
      case 'choose-topic':if(state.busy)return toast('Attendez la réponse ou arrêtez-la.');state.handsfree=false;await stopRecording(false);audioPlayer.stop();state.session=null;return renderConversation();
      case 'stop-audio':state.handsfree=false;if($('#handsfree'))$('#handsfree').checked=false;await stopRecording(false);audioPlayer.stop();state.controller?.abort();return;
      case 'retry':{const r=state.lastRequest;if(r)return await sendTurn(r.action,r.text,r.audio);return;}
      case 'back-to-path':$('#modal').close();return setView('learn');
    }
  }catch(error){toast(errorText(error));button.disabled=false;}
});
$('#support-language').addEventListener('change',async event=>{
  const base=event.target.value;
  if(state.busy||state.translating){updateChrome();return;}
  const draft=$('#chat-input')?.value,wasHandsfree=state.handsfree;
  state.busy=true;$('#support-language').disabled=true;$('#target-language').disabled=true;
  state.handsfree=false;await stopRecording(false);audioPlayer.stop();
  try {
    await api('/api/settings',{base});await refresh();
    if(state.session)state.session=await api('/api/sessions/'+encodeURIComponent(state.session.id));
    state.handsfree=wasHandsfree;render();
    if(draft!==undefined&&$('#chat-input'))$('#chat-input').value=draft;
    toast(base==='en'?'English support is on from the next reply.':'L’appui en français reprend dès la prochaine réponse.');
  } catch(error){toast(errorText(error));updateChrome();}
  finally {state.busy=false;$('#support-language').disabled=false;$('#target-language').disabled=false;if(state.handsfree)maybeListen();}
});
$('#target-language').addEventListener('change',async event=>{try{state.handsfree=false;await stopRecording(false);audioPlayer.stop();await api('/api/settings',{target:event.target.value});state.session=null;state.lastResult=null;state.review=null;state.search='';await refresh();render();toast(`Votre parcours en ${names[event.target.value]} est prêt.`);}catch(error){toast(errorText(error));updateChrome();}});
$('#modal').addEventListener('click',event=>{if(event.target===$('#modal'))$('#modal').close();});
window.addEventListener('pagehide',()=>{state.handsfree=false;stopRecording(false);audioPlayer.stop();state.controller?.abort();});
document.addEventListener('visibilitychange',()=>{if(document.hidden){state.handsfree=false;stopRecording(false);if($('#handsfree'))$('#handsfree').checked=false;}});
async function init(){
  $$('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));
  try{
    const {profiles}=await api('/api/profiles');
    if(!profiles.some(p=>p.id===state.profileId))state.profileId='default';
    localStorage.setItem('parliamo-profile',state.profileId);
    const legacy=localStorage.getItem('parliamo-session');
    if(legacy&&!localStorage.getItem(sessionKey('default')))localStorage.setItem(sessionKey('default'),legacy);
    localStorage.removeItem('parliamo-session');
    await refresh();state.session=await savedSession(state.profileId,state.data.settings.target);render();await checkHealth();
  }
  catch(error){$('#app').innerHTML=`<div class="empty-state"><h1>Votre espace se repose.</h1><p>${esc(errorText(error))}</p><p>Ouvrez Gem Teacher sur l’ordinateur, puis actualisez cette page.</p></div>`;}
}
init();
