'use strict';
// Lesson resources are local snapshots. Opening/reviewing them never calls Gemma.
function lessonCopy(fr,en){return state.data.settings.base==='en'?en:fr;}
function lessonStatus(plan){
  return ({active:lessonCopy('Objectifs en cours','Goals in progress'),achieved:lessonCopy('Objectifs atteints !','Goals achieved!'),ended_early:lessonCopy('Séance terminée · objectifs à reprendre','Session ended · goals still to practise'),legacy:lessonCopy('Leçon terminée avant le suivi détaillé','Lesson completed before detailed tracking')})[plan?.status]||'';
}
function objectiveList(plan,evidence=false){
  const current=plan.objectives.find(o=>!o.evidence)?.id;
  return `<ol class="lesson-objectives ${evidence?'with-evidence':''}">${plan.objectives.map((o,i)=>`<li class="${o.evidence?'achieved':o.id===current&&plan.status==='active'?'current':''}"><span class="objective-number">${o.evidence?icon('check'):i+1}</span><div><strong data-verbatim>${esc(o[state.data.settings.base])}</strong>${evidence&&o.evidence?`<blockquote data-verbatim>${esc(o.evidence)}</blockquote>`:''}</div></li>`).join('')}</ol>`;
}
function nextLessonButton(session){
  const topics=state.data.topics, start=topics.findIndex(t=>t.id===session.topic)+1;
  const ordered=[...topics.slice(start),...topics.slice(0,start)];
  const next=ordered.find(t=>t.id!==session.topic&&!state.data.completed_topics.includes(t.id));
  return next?`<button class="button small" data-topic="${next.id}">${lessonCopy('Prochaine leçon','Next lesson')} ${icon('arrow')}</button>`:`<button class="button small" data-action="back-to-path">${lessonCopy('Voir mon parcours','See my learning path')}</button>`;
}
function grammarCard(plan){
  if(!plan.grammar)return '';
  return `<section class="lesson-grammar"><h3>${lessonCopy('La petite pause grammaire','A little grammar break')}</h3><p data-verbatim>${esc(plan.grammar[state.data.settings.base])}</p><p class="grammar-example" data-verbatim>${esc(plan.grammar.example)}</p></section>`;
}
function renderLessonPlan(){
  const root=$('#lesson-plan'), session=state.session, plan=session?.lesson;
  if(!root||!plan)return;
  const achieved=plan.objectives.filter(o=>o.evidence).length;
  root.innerHTML=`<section class="panel lesson-plan"><div class="lesson-plan-heading"><div><span class="eyebrow">${lessonCopy('VOTRE MISSION DU JOUR','TODAY’S MISSION')} · ${session.level}</span><h2 data-verbatim>${lessonStatus(plan)}</h2></div><span class="objective-count">${plan.status==='legacy'?'—':`${achieved} / ${plan.objectives.length}`} ${lessonCopy('objectifs','goals')}</span></div>${objectiveList(plan)}<div class="lesson-plan-actions"><small>${plan.status==='active'?lessonCopy('Chaque coche correspond à une action réussie dans vos réponses.','Each check marks an action demonstrated in your replies.'):lessonCopy('Le bilan et les mots restent disponibles dans votre carnet.','Your recap and words stay available in your notebook.')}</small><button class="button secondary small" id="finish-button" data-action="finish" ${state.busy||(!session.finished&&!session.turns)?'disabled':''}>${session.finished?lessonCopy('Bilan et vocabulaire','Recap & vocabulary'):lessonCopy('Terminer la séance','Finish this session')}</button></div></section>`;
  const resources=$('#lesson-resources');
  if(resources)resources.innerHTML=`${grammarCard(plan)}<button class="text-button" data-lesson-recap="${session.id}">${icon('book')} ${lessonCopy('Voir les mots de cette leçon','View this lesson’s words')}</button><button class="text-button" data-action="choose-topic">${lessonCopy('Choisir un autre sujet','Choose another topic')} ${icon('arrow')}</button>`;
}
function lessonLibrary(){
  const sessions=state.data.sessions.filter(s=>s.lesson&&s.turns>0);
  return `<section class="panel lesson-library"><div class="section-heading"><h2>${lessonCopy('Mes leçons et leur vocabulaire','My lessons & vocabulary')}</h2></div><p>${lessonCopy('Retrouvez chaque mission, ses acquis, sa grammaire et ses mots à pratiquer.','Revisit each mission, its achievements, grammar and words to practise.')}</p>${sessions.length?`<div class="lesson-library-list">${sessions.map(s=>`<button data-lesson-recap="${s.id}"><strong>${esc(state.data.topics.find(t=>t.id===s.topic)?.title)}</strong><small>${s.level} · ${new Date(s.started).toLocaleDateString(state.data.settings.base)} · ${s.lesson.vocabulary_count} ${lessonCopy('expressions','expressions')}</small><span data-verbatim>${lessonStatus(s.lesson)}</span>${icon('arrow')}</button>`).join('')}</div>`:`<p class="subtle">${lessonCopy('Les mots de votre première leçon apparaîtront ici.','Words from your first lesson will appear here.')}</p>`}</section>`;
}
async function openLessonRecap(id){
  if(state.busy||state.translating)return;
  const profileId=state.profileId;
  state.handsfree=false;await stopRecording(false);audioPlayer.stop();if($('#handsfree'))$('#handsfree').checked=false;
  const session=await api('/api/sessions/'+encodeURIComponent(id),undefined,profileId);
  if(state.profileId!==profileId)return;
  state.recapSession=session;
  renderLessonRecap();
}
function vocabularyMeaning(item){
  return state.data.settings.base==='en'?item.english||item.translation:item.base==='fr'?item.translation:item.english||item.translation;
}
function renderLessonRecap(){
  const session=state.recapSession, plan=session.lesson;
  if(!plan)return;
  const topic=state.data.topics.find(t=>t.id===session.topic), notes=plan.recap;
  showModal(`<div class="lesson-recap"><div class="eyebrow">${lessonCopy('BILAN DE LA LEÇON','LESSON RECAP')} · ${session.level}</div><h2>${esc(topic.title)}</h2><p class="recap-status" data-verbatim>${lessonStatus(plan)}</p>${plan.status==='legacy'?`<p>${lessonCopy('Votre ancienne validation est conservée. Les preuves par objectif n’étaient pas encore enregistrées.','Your previous completion is preserved. Evidence for individual goals was not recorded at the time.')}</p>`:objectiveList(plan,true)}
    ${notes?.summary?`<p data-verbatim>${esc(notes.summary)}</p>`:''}${notes?.practice?.length?`<h3>${lessonCopy('À retravailler','Keep practising')}</h3><ul data-verbatim>${notes.practice.map(n=>`<li>${esc(n)}</li>`).join('')}</ul>`:''}${grammarCard(plan)}
    <div class="recap-vocabulary-heading"><h3>${lessonCopy('Les mots de cette leçon','This lesson’s vocabulary')}</h3><button class="button small" data-lesson-practice ${plan.vocabulary.length?'':'disabled'}>${lessonCopy('Pratiquer ces mots','Practise these words')}</button></div><p class="subtle">${lessonCopy('Expressions utiles au sujet et rencontrées pendant la leçon.','Useful expressions for the topic and phrases collected during the lesson.')}</p>
    <div class="lesson-vocabulary">${plan.vocabulary.map((item,i)=>`<article><div><strong data-verbatim>${esc(item.text)}</strong><p data-verbatim>${esc(vocabularyMeaning(item))}</p>${state.data.settings.base==='fr'&&item.base==='fr'&&item.english?`<small data-verbatim>EN · ${esc(item.english)}</small>`:''}${item.reviews?`<small>${lessonCopy('Révisions','Reviews')}: ${item.reviews} · ${item.remembered?lessonCopy('Retenu','Remembered'):lessonCopy('À revoir','Practise again')}</small>`:''}</div><div class="vocabulary-actions"><button class="icon-button" data-lesson-speak="${i}" aria-label="${lessonCopy('Écouter','Listen')}">${icon('volume')}</button><button class="icon-button" data-lesson-save="${i}" aria-label="${lessonCopy('Garder dans mon carnet','Save to my notebook')}">${icon('bookmark')}</button></div></article>`).join('')}</div>
    <div class="recap-actions"><button class="button secondary small" data-resume="${session.id}">${lessonCopy('Continuer à discuter','Keep chatting')}</button>${plan.status==='ended_early'?`<button class="button small" data-resume-objectives="${session.id}">${lessonCopy('Reprendre les objectifs','Resume the goals')}</button>`:plan.status==='active'?'':nextLessonButton(session)}<button class="text-button" data-action="back-to-path">${lessonCopy('Retour au parcours','Back to my path')}</button></div></div>`);
}
function renderLessonPractice(){
  const review=state.lessonReview, session=state.recapSession, item=session.lesson.vocabulary[review.index];
  showModal(`<div class="lesson-recap lesson-practice"><div class="eyebrow">${lessonCopy('LES MOTS DE MA LEÇON','MY LESSON’S WORDS')}</div>${item?`<p>${review.index+1} / ${session.lesson.vocabulary.length}</p><h2 data-verbatim>${esc(item.text)}</h2><button class="icon-button" data-lesson-speak="${review.index}" aria-label="${lessonCopy('Écouter','Listen')}">${icon('volume')}</button><p>${lessonCopy('Retrouvez le sens et essayez une phrase à voix haute.','Recall the meaning and try saying a sentence aloud.')}</p>${review.revealed?`<div class="review-answer" data-verbatim>${esc(vocabularyMeaning(item))}</div><div class="review-actions"><button class="button secondary" data-lesson-grade="again">${lessonCopy('Encore un peu','Practise again')}</button><button class="button" data-lesson-grade="good">${lessonCopy('Je m’en souviens','I remember')}</button></div>`:`<button class="button" data-lesson-reveal>${lessonCopy('Voir le sens','Show the meaning')}</button>`}`:`<h2>${lessonCopy('Révision terminée !','Practice complete!')}</h2><p>${review.index} ${lessonCopy('expressions revues. Votre pratique est sauvegardée.','expressions reviewed. Your practice is saved.')}</p>`}<div class="recap-actions"><button class="text-button" data-lesson-back>${lessonCopy('Retour au bilan','Back to the recap')}</button></div></div>`);
}
async function lessonClick(button){
  if(button.dataset.lessonRecap)return await openLessonRecap(button.dataset.lessonRecap),true;
  if(button.dataset.resumeObjectives){
    if(state.busy||state.translating)return true;
    await api('/api/resume-objectives',{session_id:button.dataset.resumeObjectives});$('#modal').close();
    await refresh();await resumeLesson(button.dataset.resumeObjectives);return true;
  }
  if(button.hasAttribute('data-lesson-practice')){state.lessonReview={index:0,revealed:false};renderLessonPractice();return true;}
  if(button.hasAttribute('data-lesson-reveal')){state.lessonReview.revealed=true;renderLessonPractice();return true;}
  if(button.hasAttribute('data-lesson-back')){audioPlayer.stop();renderLessonRecap();return true;}
  if(button.dataset.lessonGrade){
    button.disabled=true;$$('[data-lesson-grade]').forEach(b=>b.disabled=true);
    const profileId=state.profileId;
    try{
      const session=await api('/api/lesson-review',{session_id:state.recapSession.id,index:state.lessonReview.index,remembered:button.dataset.lessonGrade==='good'},profileId);
      if(state.profileId!==profileId)return true;
      state.recapSession=session;
      if(state.session?.id===state.recapSession.id)state.session=state.recapSession;
      state.lessonReview.index++;state.lessonReview.revealed=false;audioPlayer.stop();renderLessonPractice();
    }catch(error){$$('[data-lesson-grade]').forEach(b=>b.disabled=false);throw error;}
    return true;
  }
  if(button.dataset.lessonSpeak!==undefined){
    const item=state.recapSession.lesson.vocabulary[Number(button.dataset.lessonSpeak)];
    audioPlayer.stop();audioPlayer.enqueue({text:item.text,language:state.recapSession.target});return true;
  }
  if(button.dataset.lessonSave!==undefined){
    const item=state.recapSession.lesson.vocabulary[Number(button.dataset.lessonSave)];
    const topic=state.data.topics.find(t=>t.id===state.recapSession.topic);
    await api('/api/bookmarks',{text:item.text,translation:vocabularyMeaning(item),english:item.english,target:state.recapSession.target,note:topic.title+' · '+state.recapSession.level});
    await refresh();button.disabled=true;toast(lessonCopy('Expression gardée dans votre carnet.','Expression saved to your notebook.'));return true;
  }
  return false;
}
