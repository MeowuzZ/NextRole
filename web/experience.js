/* Local Markdown subset: lists, headings, emphasis, quotes, links and code. Raw HTML is text. */
function experienceMarkdown(source){
 function plain(s){return esc(s).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/\*(.+?)\*/g,'<em>$1</em>').replace(/~~(.+?)~~/g,'<del>$1</del>')}
 function inline(s){return s.split(/(`[^`]+`|\[[^\]]+\]\((?:https?:\/\/|mailto:)[^)\s]+\))/g).map(t=>{if(t.startsWith('`')&&t.endsWith('`'))return '<code>'+esc(t.slice(1,-1))+'</code>';const m=t.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+|mailto:[^)\s]+)\)$/);return m?`<a href="${esc(m[2])}" target="_blank" rel="noopener noreferrer">${plain(m[1])}</a>`:plain(t)}).join('')}
 const lines=String(source||'').replace(/\r\n?/g,'\n').split('\n');let out='',list='',code=null;
 const close=()=>{if(list){out+='</'+list+'>';list=''}};
 for(const line of lines){if(/^\s*```/.test(line)){close();if(code===null)code=[];else{out+='<pre><code>'+esc(code.join('\n'))+'</code></pre>';code=null}continue}if(code!==null){code.push(line);continue}
  const item=line.match(/^\s*(?:(\d+)\.\s+|([-+*])\s+)(.*)$/);if(item){const kind=item[1]?'ol':'ul';if(list!==kind){close();list=kind;out+='<'+kind+(item[1]?' start="'+Number(item[1])+'"':'')+'>'}out+='<li>'+inline(item[3])+'</li>';continue}close();if(!line.trim())continue;
  const h=line.match(/^(#{1,6})\s+(.+)$/);if(h){out+=`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`;continue}if(/^>\s?/.test(line)){out+='<blockquote>'+inline(line.replace(/^>\s?/,''))+'</blockquote>';continue}out+='<p>'+inline(line)+'</p>';
 }close();if(code!==null)out+='<pre><code>'+esc(code.join('\n'))+'</code></pre>';return out;
}
/* Edit rendered blocks directly, serialize Markdown only when synchronizing the form. */
function experienceToMarkdown(root){
 function inline(node){if(node.nodeType===3)return node.textContent.replace(/\u00a0/g,' ');if(node.nodeType!==1)return '';const tag=node.tagName.toLowerCase(),body=[...node.childNodes].map(inline).join('');
  if(tag==='br')return '\n';if(tag==='b'||tag==='strong')return '**'+body+'**';if(tag==='i'||tag==='em')return '*'+body+'*';if(tag==='s'||tag==='strike'||tag==='del')return '~~'+body+'~~';if(tag==='code')return '`'+body+'`';if(tag==='a'){const href=node.getAttribute('href')||'';return /^(https?:\/\/|mailto:)/i.test(href)?'['+body+']('+href+')':body}return body;
 }
 function block(node,depth=0){if(node.nodeType!==1)return inline(node);const tag=node.tagName.toLowerCase();
  if(tag==='ul'||tag==='ol'){let i=Number(node.getAttribute('start'))||1;return [...node.children].filter(n=>n.tagName==='LI').map(li=>{const content=[...li.childNodes].filter(n=>!['UL','OL'].includes(n.tagName)).map(inline).join('').trim();const nested=[...li.children].filter(n=>['UL','OL'].includes(n.tagName)).map(n=>block(n,depth+1)).join('');return '  '.repeat(depth)+(tag==='ol'?(i++)+'. ':'- ')+content+'\n'+nested}).join('')+'\n'}
  if(tag==='pre')return '```\n'+node.textContent.replace(/\n$/,'')+'\n```\n\n';
  if(tag==='blockquote')return node.textContent.split('\n').filter(Boolean).map(line=>'> '+line).join('\n')+'\n\n';
  if(/^h[1-6]$/.test(tag))return '#'.repeat(Number(tag[1]))+' '+inline(node)+'\n\n';
  if([...node.children].some(n=>['DIV','P','UL','OL','PRE','BLOCKQUOTE'].includes(n.tagName)))return [...node.childNodes].map(n=>block(n,depth)).join('');
  return inline(node)+(['p','div','li'].includes(tag)?'\n\n':'');
 }
 return [...root.childNodes].map(n=>block(n)).join('').replace(/\n{3,}/g,'\n\n').trim();
}
function markdownExperienceField(label,name,value=''){
 return `<section class="field full markdown-field"><label id="label-${name}" for="editor-${name}">${label}</label><div class="rich-writing-box"><div class="rich-toolbar" role="toolbar" aria-label="${label}格式">${[['bold','加粗','B'],['italic','斜体','I'],['insertOrderedList','编号列表','1.'],['insertUnorderedList','项目列表','•'],['heading','小标题','H'],['undo','撤销','↶'],['redo','重做','↷']].map(([command,title,text])=>`<button type="button" data-rich-command="${command}" title="${title}" aria-label="${title}">${text}</button>`).join('')}</div><div class="markdown-preview rich-editor" id="editor-${name}" data-rich-editor="${name}" contenteditable="true" role="textbox" aria-multiline="true" aria-labelledby="label-${name}" spellcheck="false" data-placeholder="点击开始记录"></div><textarea id="f-${name}" name="${name}" data-markdown hidden>${esc(value)}</textarea></div></section>`;
}
function experienceBlockShortcut(text){
 const m=text.match(/^(#{1,6}|\d+\.|[-*+]|>)[ \u00a0]+/);if(!m)return null;
 return {length:m[0].length,command:m[1][0]==='#'?'heading':m[1]==='>'?'quote':/^\d/.test(m[1])?'ordered':'unordered',level:m[1][0]==='#'?m[1].length:0,start:/^\d/.test(m[1])?Number(m[1].slice(0,-1)):1};
}
function bindExperienceMarkdown(root){root.querySelectorAll('[data-rich-editor]').forEach(editor=>{
 const area=root.querySelector('#f-'+editor.dataset.richEditor),toolbar=editor.previousElementSibling;
 editor.innerHTML=experienceMarkdown(area.value);let composing=false,converting=false;
 const sync=()=>{area.value=experienceToMarkdown(editor);editor.setAttribute('aria-invalid',String(area.value.length>20000));area.dispatchEvent(new Event('input',{bubbles:true}))};
 function caretEnd(node){const range=document.createRange();range.selectNodeContents(node);range.collapse(false);const selection=getSelection();selection.removeAllRanges();selection.addRange(range)}
 function startList(){if(!editor.textContent.trim()&&!editor.querySelector('li')){editor.innerHTML='<ol><li><br></li></ol>';caretEnd(editor.querySelector('li'));sync()}}
 function currentBlock(){const selection=getSelection();if(!selection?.isCollapsed||!editor.contains(selection.anchorNode))return null;let node=selection.anchorNode.nodeType===1?selection.anchorNode:selection.anchorNode.parentElement;const block=node.closest('p,div,h1,h2,h3,h4,h5,h6,li,blockquote,pre');return block&&editor.contains(block)?block:null}
 function selectPrefix(block,length){const walker=document.createTreeWalker(block,NodeFilter.SHOW_TEXT);let node,remaining=length;const range=document.createRange();range.selectNodeContents(block);range.collapse(true);while((node=walker.nextNode())){if(remaining<=node.length){range.setEnd(node,remaining);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);return true}remaining-=node.length}return false}
 function convertTypedMarkdown(){
  if(converting||composing)return;const selection=getSelection();let block=currentBlock();if(!block||block.closest('pre,code'))return;
  const rule=experienceBlockShortcut(block.textContent);
  if(rule){converting=true;try{
   // Root text and the auto-created numbered item both accept block shortcuts.
   if(block===editor){document.execCommand('formatBlock',false,'p');block=currentBlock();if(!block||block===editor)return}
   const caret=document.createRange();caret.selectNodeContents(block);caret.setEnd(selection.anchorNode,selection.anchorOffset);const cursor=Math.max(0,caret.toString().length-rule.length);
   const listItem=block.closest('li'),list=listItem?.parentElement;
   if(!selectPrefix(block,rule.length))return;document.execCommand('delete',false,null);
   if(rule.command==='heading'||rule.command==='quote'){
    if(list&&editor.contains(list))document.execCommand(list.tagName==='OL'?'insertOrderedList':'insertUnorderedList',false,null);
    document.execCommand('formatBlock',false,rule.command==='heading'?'h'+rule.level:'blockquote');
   }else{
    const wanted=rule.command==='ordered'?'OL':'UL';if(list?.tagName!==wanted)document.execCommand(rule.command==='ordered'?'insertOrderedList':'insertUnorderedList',false,null);
    if(rule.command==='ordered'&&rule.start!==1){const active=currentBlock()?.closest('ol');if(active)active.setAttribute('start',String(rule.start))}
   }
   if(cursor>0){const active=currentBlock();if(active){const walker=document.createTreeWalker(active,NodeFilter.SHOW_TEXT);let node,left=cursor;while((node=walker.nextNode())){if(left<=node.length){const r=document.createRange();r.setStart(node,left);r.collapse(true);selection.removeAllRanges();selection.addRange(r);break}left-=node.length}}}
  }finally{converting=false}return}
  // Inline delimiters turn into formatted text as soon as the closing marker is typed.
  if(!selection?.isCollapsed||selection.anchorNode?.nodeType!==3)return;
  const node=selection.anchorNode,offset=selection.anchorOffset,before=node.textContent.slice(0,offset);
  const match=before.match(/(\*\*[^*\n]+\*\*|~~[^~\n]+~~|`[^`\n]+`|\*[^*\n]+\*|\[[^\]\n]+\]\((?:https?:\/\/|mailto:)[^)\s]+\))$/);if(!match)return;
  converting=true;try{const range=document.createRange();range.setStart(node,offset-match[0].length);range.setEnd(node,offset);selection.removeAllRanges();selection.addRange(range);const fragment=document.createElement('div');fragment.innerHTML=experienceMarkdown(match[0]);document.execCommand('insertHTML',false,fragment.firstElementChild?.innerHTML||esc(match[0]))}finally{converting=false}
 }
 editor.addEventListener('focus',startList);
 editor.addEventListener('input',event=>{if(!composing&&!converting){if(!['historyUndo','historyRedo'].includes(event.inputType))convertTypedMarkdown();sync()}});
 editor.addEventListener('compositionstart',()=>composing=true);editor.addEventListener('compositionend',()=>{composing=false;convertTypedMarkdown();sync()});
 toolbar.querySelectorAll('button').forEach(button=>{button.addEventListener('pointerdown',event=>event.preventDefault());button.onclick=()=>{editor.focus();const command=button.dataset.richCommand;if(command==='heading')document.execCommand('formatBlock',false,'h3');else document.execCommand(command,false,null);sync()}});
 editor.addEventListener('paste',event=>{event.preventDefault();const text=event.clipboardData?.getData('text/plain')||'';if(!text)return;const rendered=/\n|^(?:#{1,6} |\d+\. |[-*] )/.test(text)||/\*\*.+?\*\*/.test(text)?experienceMarkdown(text):esc(text);document.execCommand('insertHTML',false,rendered);sync()});
 editor.addEventListener('drop',event=>event.preventDefault());editor.addEventListener('click',event=>{if(event.target.closest('a'))event.preventDefault()});
 // FormData still receives Markdown, keeping existing storage and exports compatible.
 area.form?.addEventListener('submit',sync,true);
 })}
function experienceDetails(experience){if(!experience)return '';if(experience.schemaVersion!==2)return `<p class="progress-experience-text">${esc(experience.summary||'')}</p>`;
 const e=experience;let html='';const item=(label,text,markdown=false)=>text?`<div class="experience-detail"><strong>${esc(label)}</strong><div class="${markdown?'markdown-preview':'experience-plain'}">${markdown?experienceMarkdown(text):esc(text)}</div></div>`:'';
 if(e.kind==='TEST')html=item('笔试／测评记录',e.notes);
 if(e.kind==='INTERVIEW')html=`<div class="experience-facts"><span>${e.interviewType==='GROUP'?'群面':'Solo面'}</span>${e.interviewType==='SOLO'?`<span>候选人 ${esc(e.candidateCount)} 人</span>`:''}</div>`+item('面试官身份',e.interviewer)+item('面试问题记录',e.questions,true)+item('其他记录',e.other);
 if(e.kind==='OFFER_CALL')html=item('初次谈薪待遇',e.initialOffer,true)+item('谈判增加待遇',e.negotiatedOffer,true);
 return `<div class="progress-experience-content">${html}</div>`;
}
function candidateWheelValue(index){return ((Math.round(index)%20)+20)%20+1}
function interviewCountWheel(value){return `<div class="field full" id="candidate-count-field"><label id="candidate-count-label">面试候选人人数</label><div class="candidate-picker"><div class="candidate-wheel-selection" aria-hidden="true"></div><div class="candidate-wheel" role="spinbutton" tabindex="0" aria-valuemin="1" aria-valuemax="20" aria-valuenow="${value}" aria-labelledby="candidate-count-label">${Array.from({length:140},(_,i)=>`<button type="button" tabindex="-1" aria-hidden="true" data-count-index="${i}" data-count="${i%20+1}">${i%20+1}</button>`).join('')}</div></div><input type="hidden" name="candidateCount" value="${value}"></div>`}
function bindInterviewWheel(root){const wheel=root.querySelector('.candidate-wheel'),input=root.querySelector('[name=candidateCount]'),field=root.querySelector('#candidate-count-field');if(!wheel)return;
 const rowHeight=44,center=60;let frame=0;
 function paint(index){const n=candidateWheelValue(index);input.value=n;wheel.setAttribute('aria-valuenow',n);wheel.setAttribute('aria-valuetext',n+' 人');wheel.querySelectorAll('[data-count-index]').forEach(button=>button.classList.toggle('is-centered',+button.dataset.countIndex===Math.round(index)))}
 function recenter(){const raw=wheel.scrollTop/rowHeight;if(raw>=20&&raw<120)return;const cycles=Math.floor(raw/20)-3;wheel.scrollTop-=cycles*20*rowHeight}
 function move(index){if(field.hidden)return;recenter();wheel.scrollTo({top:index*rowHeight,behavior:reducedMotion()?'auto':'smooth'})}
 wheel.querySelectorAll('[data-count-index]').forEach(button=>button.onclick=()=>{const target=+button.dataset.countIndex,current=Math.round(wheel.scrollTop/rowHeight);const delta=target-current;recenter();move(Math.round(wheel.scrollTop/rowHeight)+delta)});
 wheel.addEventListener('scroll',()=>{if(field.hidden)return;cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{recenter();paint(wheel.scrollTop/rowHeight)})},{passive:true});
 wheel.onkeydown=event=>{if(!['ArrowUp','ArrowDown','Home','End'].includes(event.key))return;event.preventDefault();recenter();const index=Math.round(wheel.scrollTop/rowHeight),value=candidateWheelValue(index);const delta=event.key==='Home'?1-value:event.key==='End'?20-value:event.key==='ArrowDown'?1:-1;move(index+delta)};
 wheel.addEventListener('scrollend',()=>{if(!field.hidden){recenter();paint(wheel.scrollTop/rowHeight)}});
 root.querySelector('form')?.addEventListener('submit',()=>{if(!field.hidden)paint(wheel.scrollTop/rowHeight)},true);
 const update=()=>{cancelAnimationFrame(frame);field.hidden=root.querySelector('[name=interviewType]:checked')?.value==='GROUP';if(!field.hidden)requestAnimationFrame(()=>{if(field.hidden||!wheel.isConnected)return;const index=center+Math.max(0,Math.min(19,(+input.value||1)-1));wheel.scrollTop=index*rowHeight;paint(index)})};root.querySelectorAll('[name=interviewType]').forEach(el=>el.addEventListener('change',update));update();
}
