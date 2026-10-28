/* Share one accessible picker across mobile controls and resume dictionaries. */
(()=>{
 let active=null;
 const eligible=s=>s instanceof HTMLSelectElement&&!s.multiple&&!s.disabled&&(matchMedia('(max-width:900px)').matches||!!s.closest('.reference-editor'));
 function open(select){
  if(active||!eligible(select))return;
  const picker=document.createElement('dialog');picker.className='choice-picker';
  const label=select.labels?.[0]?.textContent.replace(/\*/g,'').trim()||select.getAttribute('aria-label')||'选择选项';
  const heading=document.createElement('h2');heading.id='choice-picker-title';heading.textContent=label;picker.setAttribute('aria-labelledby',heading.id);
  const head=document.createElement('header');head.append(heading);
  const close=document.createElement('button');close.type='button';close.className='choice-close';close.textContent='✕';close.setAttribute('aria-label','关闭选择');head.append(close);picker.append(head);
  const source=Array.from(select.options);let search=null;
  if(source.length>8){search=document.createElement('input');search.type='search';search.placeholder='搜索选项';search.setAttribute('aria-label','搜索'+label);search.className='choice-search';picker.append(search)}
  const list=document.createElement('div');list.className='choice-list';list.setAttribute('role','listbox');list.setAttribute('aria-label',label);picker.append(list);
  let closing=false;function finish(){if(active!==picker||closing)return;closing=true;picker.close()}
  picker.addEventListener('close',()=>{if(active===picker)active=null;picker.remove();if(select.isConnected)select.focus({preventScroll:true})},{once:true});
  function draw(){list.replaceChildren();const query=(search?.value||'').trim().toLocaleLowerCase();
   source.forEach((option,index)=>{if(option.hidden||!option.textContent.toLocaleLowerCase().includes(query))return;
    const b=document.createElement('button');b.type='button';b.className='choice-option';b.setAttribute('role','option');b.setAttribute('aria-selected',String(index===select.selectedIndex));b.disabled=option.disabled||option.parentElement.disabled===true;
    const text=document.createElement('span');text.textContent=option.textContent;const check=document.createElement('span');check.textContent=index===select.selectedIndex?'✓':'';check.setAttribute('aria-hidden','true');b.append(text,check);
    b.onclick=()=>{const changed=select.selectedIndex!==index;finish();if(changed&&select.isConnected){select.selectedIndex=index;select.dispatchEvent(new Event('input',{bubbles:true}));select.dispatchEvent(new Event('change',{bubbles:true}))}};list.append(b);
   });if(!list.children.length){const empty=document.createElement('p');empty.className='choice-empty';empty.textContent='无匹配选项';list.append(empty)}
  }
  close.onclick=finish;picker.addEventListener('cancel',e=>{e.preventDefault();finish()});picker.addEventListener('click',e=>{if(e.target===picker){const r=picker.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)finish()}});
  list.onkeydown=e=>{if(!['ArrowDown','ArrowUp','Home','End'].includes(e.key))return;e.preventDefault();const items=[...list.querySelectorAll('button:not(:disabled)')];let i=items.indexOf(document.activeElement);i=e.key==='Home'?0:e.key==='End'?items.length-1:Math.max(0,Math.min(items.length-1,i+(e.key==='ArrowDown'?1:-1)));items[i]?.focus()};
  if(search)search.oninput=draw;active=picker;document.body.append(picker);draw();if(typeof installDialogMotion==='function')installDialogMotion(picker);picker.showModal();
  const chosen=list.querySelector('[aria-selected=true]');chosen?.scrollIntoView({block:'nearest'});if(search)close.focus();else(chosen||list.querySelector('button')||close).focus();

 }
 document.addEventListener('pointerdown',e=>{if(eligible(e.target))e.preventDefault()},true);
 document.addEventListener('click',e=>{if(eligible(e.target)){e.preventDefault();open(e.target)}},true);
 document.addEventListener('keydown',e=>{if(eligible(e.target)&&['Enter',' ','ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();open(e.target)}});
})();
