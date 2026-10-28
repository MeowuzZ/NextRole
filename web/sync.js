/* Portable, whitespace-tolerant sync envelopes. Password encryption is optional. */
const SyncCode={
 encode64(bytes){let text='';for(let i=0;i<bytes.length;i+=32768)text+=String.fromCharCode(...bytes.subarray(i,i+32768));return btoa(text).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')},
 decode64(text){if(!/^[A-Za-z0-9_-]+$/.test(text))throw Error('同步码包含无效字符，请完整复制');const bytes=Uint8Array.from(atob(text.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));if(this.encode64(bytes)!==text)throw Error('同步码校验失败，请完整复制');return bytes},
 async zip(bytes,unpack=false){if(typeof CompressionStream==='undefined'||typeof DecompressionStream==='undefined')throw Error('请更新浏览器以使用同步码');const stream=new Blob([bytes]).stream().pipeThrough(unpack?new DecompressionStream('gzip'):new CompressionStream('gzip'));return new Uint8Array(await new Response(stream).arrayBuffer())},
 async key(password,salt){const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveKey']);return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:210000,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt'])},
 async encode(snapshot,password=''){
  const bytes=await this.zip(new TextEncoder().encode(JSON.stringify(snapshot)));
  if(password){const salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12)),key=await this.key(password,salt);const cipher=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},key,bytes));return 'QTE1.'+[salt,iv,cipher].map(v=>this.encode64(v)).join('.')}
  const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',bytes));return 'QTS1.'+this.encode64(digest)+'.'+this.encode64(bytes);
 },
 async decode(input,password=''){
  const code=String(input).replace(/[\s\u200B-\u200D\uFEFF]/g,'');const parts=code.split('.');let bytes;
  try{
   if(parts[0]==='QTS1'&&parts.length===3){bytes=this.decode64(parts[2]);const digest=this.encode64(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)));if(digest!==parts[1])throw Error('同步码校验失败，内容不完整或已被修改')}
   else if(parts[0]==='QTE1'&&parts.length===4){if(!password)throw Error('此同步码已加密，请输入同步密码');const salt=this.decode64(parts[1]),iv=this.decode64(parts[2]);if(salt.length!==16||iv.length!==12)throw Error('同步码格式不正确');const key=await this.key(password,salt);try{bytes=new Uint8Array(await crypto.subtle.decrypt({name:'AES-GCM',iv},key,this.decode64(parts[3])))}catch{throw Error('密码不正确或同步码已损坏')}}
   else throw Error('同步码格式不正确，请完整复制');
   const snapshot=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await this.zip(bytes,true)));
   if(snapshot.schemaVersion!==1||!Number.isSafeInteger(snapshot.modifiedAt)||snapshot.modifiedAt<0||!Array.isArray(snapshot.records))throw Error('同步内容格式不正确');return snapshot;
  }catch(error){if(error.name==='SyntaxError'||error.name==='TypeError')throw Error('同步码损坏或内容不完整');throw error}
 }
};
function syncTime(value){return value?new Date(value).toLocaleString('zh-CN',{hour12:false})+'.'+String(value%1000).padStart(3,'0'):'暂无修改'}
async function exportSyncCode(){try{
 const snapshot=await api('/admin/sync');modal('生成同步码',`<div class="sync-meta">最后修改：${esc(syncTime(snapshot.modifiedAt))} · ${snapshot.records.length} 条记录</div>${field('同步密码（选填，填写后加密）','syncPassword','','password')}<div class="sync-tools"><button type="button" id="generate-sync">生成同步码</button><button type="button" id="copy-sync" disabled>复制</button></div><textarea id="sync-output" class="sync-code" aria-label="同步码" readonly placeholder="正在生成…"></textarea>`,null);$('#cancel-modal').textContent='关闭';
 const output=$('#sync-output'),password=$('#f-syncPassword'),generate=$('#generate-sync'),copy=$('#copy-sync');let generation=0;
 async function generateCode(){const token=++generation;generate.disabled=true;copy.disabled=true;try{const code=await SyncCode.encode(snapshot,password.value);if(token===generation&&output.isConnected){output.value=code;copy.disabled=false}}catch(error){if(output.isConnected)$('#modal-error').textContent=error.message}finally{if(token===generation)generate.disabled=false}}
 password.oninput=()=>{generation++;copy.disabled=true;output.value='';generate.disabled=false;output.placeholder='点击生成同步码'};generate.onclick=generateCode;
 copy.onclick=async()=>{try{await navigator.clipboard.writeText(output.value);toast('同步码已复制')}catch{output.focus();output.select();toast(document.execCommand('copy')?'同步码已复制':'请手动复制已选中的同步码')}};await generateCode();
}catch(error){toast(error.message)}}
function importSyncCode(){
 modal('粘贴同步码',`<div class="field"><label for="sync-input">同步码</label><textarea id="sync-input" class="sync-code" placeholder="在此粘贴完整同步码" spellcheck="false"></textarea></div>${field('同步密码（加密时填写）','syncPassword','','password')}<p class="sync-status" id="sync-status" role="status">仅允许较新的版本覆盖本地资料</p>`,async()=>{
  const snapshot=await SyncCode.decode($('#sync-input').value,$('#f-syncPassword').value);const plan=await api('/admin/sync/validate','POST',{snapshot});
  await api('/admin/sync/import','POST',{snapshot,expectedModifiedAt:plan.currentModifiedAt});await reload();renderPage();toast('同步完成，资料与修改时间已更新');
 },'同步到本机');
 const input=$('#sync-input'),password=$('#f-syncPassword'),status=$('#sync-status'),submit=$('#modal-form button[type=submit]');let timer,revision=0;submit.disabled=true;
 const check=()=>{clearTimeout(timer);const token=++revision;submit.disabled=true;status.className='sync-status';status.textContent=input.value.trim()?'正在检查同步码…':'仅允许较新的版本覆盖本地资料';if(!input.value.trim())return;
  timer=setTimeout(async()=>{try{const snapshot=await SyncCode.decode(input.value,password.value);const plan=await api('/admin/sync/validate','POST',{snapshot});if(token!==revision||!status.isConnected)return;status.textContent=`本机：${syncTime(plan.currentModifiedAt)}\n导入：${syncTime(plan.modifiedAt)} · ${plan.count} 条记录`;status.classList.add('valid');submit.disabled=false}catch(error){if(token===revision&&status.isConnected){status.textContent=error.message;status.classList.add('invalid')}}},350)};
 input.oninput=password.oninput=check;input.focus();
}
