"""Opt-in live checks; pass a separate server/profile, never your learner profile."""
import argparse,json,time,urllib.request
parser=argparse.ArgumentParser()
parser.add_argument('--url',required=True)
args=parser.parse_args()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def api(path,data=None):
 r=opener.open(urllib.request.Request(args.url+path,json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'}),timeout=180)
 return json.load(r)
s=api('/api/sessions',{'topic':'hello'})
records=[]
def turn(action='reply',text='',audio=None):
 t=time.monotonic(); first=None; done=None
 req=urllib.request.Request(args.url+'/api/turn',json.dumps({'session_id':s['id'],'action':action,'text':text,**({'audio':audio} if audio else {})}).encode(),headers={'Content-Type':'application/json'})
 with opener.open(req,timeout=180) as r:
  for line in r:
   e=json.loads(line)
   if e['type']=='error': raise RuntimeError(e)
   if e['type']=='segment' and first is None: first=round((time.monotonic()-t)*1000)
   if e['type']=='done': done=e
 assert done
 record={'input':text or action,'first_segment_ms':first,'result':done['result'],'phase':done['session']['phase']}
 records.append(record); print(json.dumps(record,ensure_ascii=False),flush=True)
 return done
turn('start')
bad=turn(text='Mi chiamo Luca. Io sono 30 anni e vivo a Roma.')
assert bad['result']['assessment']['rating']<5, 'Age grammar was not corrected'
assert 'ho' in bad['result']['assessment']['corrected'].lower()
good=turn(text='Ho trent’anni e vivo a Roma. Mi piace cucinare.')
assert good['result']['assessment']['rating']==5, 'Correct answer not recognized'
turn(text='Mi piace preparare la pasta con i pomodori. E tu?')
finished=api('/api/finish',{'session_id':s['id']})
turn('continue')
follow=turn(text='Ti ricordi cosa mi piace cucinare?')
assert follow['session']['phase']=='conversation' and follow['session']['turns']==4
mid=follow['message_id']; index=next(i for i,v in enumerate(follow['result']['segments']) if v['language']=='it')
for lang in ['fr','en']: print('translation',api('/api/message-translation',{'session_id':s['id'],'message_id':mid,'segment':index,'language':lang}),flush=True)
from pathlib import Path
Path('artifacts').mkdir(exist_ok=True)
Path('artifacts/continuity-live.json').write_text(json.dumps({'session_id':s['id'],'turns':records,'health':api('/api/health')},ensure_ascii=False,indent=2))
print('PASS',s['id'])
