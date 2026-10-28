const assert=require('assert'),fs=require('fs'),vm=require('vm'),{webcrypto}=require('crypto');
const ctx={crypto:webcrypto,TextEncoder,TextDecoder,Blob,Response,CompressionStream,DecompressionStream,btoa,atob,Date,console};vm.createContext(ctx);vm.runInContext(fs.readFileSync('portable/local-service.js','utf8'),ctx);vm.runInContext(fs.readFileSync('web/sync.js','utf8')+'\nglobalThis.codec=SyncCode;',ctx);
function memory(){let state={revision:0,data:{records:[]}};return {read:async()=>structuredClone(state),write:async(expected,data)=>{assert.equal(state.revision,expected);state={revision:expected+1,data:structuredClone(data)}}}}
(async()=>{
 const api=ctx.QituLocalFactory.createService(memory()).request,other=ctx.QituLocalFactory.createService(memory()).request;
 assert.equal((await api('/admin/storage')).lastModifiedAt,0);
 let job=await api('/jobs','POST',{companyName:'中文 🌟',jobTitle:'工程师',notes:'多行\n含 *Markdown*'});const stamp=(await api('/admin/storage')).lastModifiedAt;
 for(let i=0;i<3;i++){await api('/jobs');await api('/admin/sync');await api('/admin/backups','POST',{})}assert.equal((await api('/admin/storage')).lastModifiedAt,stamp);
 job=await api('/jobs/'+job.id,'PATCH',{version:job.version,companyName:'中文 🌟'});assert.equal((await api('/admin/storage')).lastModifiedAt,stamp);
 const snapshot=await api('/admin/sync'),code=await ctx.codec.encode(snapshot);assert.equal(code,await ctx.codec.encode(snapshot));assert.deepEqual(JSON.parse(JSON.stringify(await ctx.codec.decode(code))),JSON.parse(JSON.stringify(snapshot)));
 const wrapped=code.match(/.{1,40}/g).join('\n \t');assert.equal((await ctx.codec.decode(wrapped)).modifiedAt,stamp);
 await assert.rejects(()=>ctx.codec.decode(code.slice(0,-5)));await assert.rejects(()=>ctx.codec.decode(code.replace(/.$/,code.endsWith('A')?'B':'A')));
 const encrypted=await ctx.codec.encode(snapshot,'我的同步密码');await assert.rejects(()=>ctx.codec.decode(encrypted));await assert.rejects(()=>ctx.codec.decode(encrypted,'错误'));assert.equal((await ctx.codec.decode(encrypted,'我的同步密码')).records.length,1);
 await assert.rejects(()=>api('/admin/sync/validate','POST',{snapshot}),/相同/);
 const plan=await other('/admin/sync/validate','POST',{snapshot});assert.equal((await other('/admin/storage')).lastModifiedAt,0);
 await other('/admin/sync/import','POST',{snapshot,expectedModifiedAt:plan.currentModifiedAt});assert.equal((await other('/admin/storage')).lastModifiedAt,stamp);
 assert.equal((await other('/jobs'))[0].companyName,'中文 🌟');assert.equal((await other('/admin/sync/previous')).payload.records.length,0);
 await api('/jobs/'+job.id,'DELETE',{version:job.version});const newer=await api('/admin/sync');assert(newer.modifiedAt>stamp);await other('/admin/sync/import','POST',{snapshot:newer,expectedModifiedAt:stamp});assert.equal((await other('/jobs?deleted=1')).length,1);
 await assert.rejects(()=>other('/admin/sync/import','POST',{snapshot,expectedModifiedAt:newer.modifiedAt}),/早于/);
 console.log('同步码：压缩、加密、中文与换行、损坏检测、只读/无修改保存、新旧时间、删除同步与回滚备份通过');
})().catch(e=>{console.error(e);process.exitCode=1});
