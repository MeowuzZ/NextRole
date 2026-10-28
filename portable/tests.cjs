const assert=require('assert'),fs=require('fs'),vm=require('vm');const {webcrypto}=require('crypto');
const ctx={crypto:webcrypto,TextEncoder,TextDecoder,console,Date};vm.createContext(ctx);vm.runInContext(fs.readFileSync('web/resume-schema.js','utf8')+'\nglobalThis.RESUME_SECTIONS=RESUME_SECTIONS;globalThis.RESUME_OPTIONS=RESUME_OPTIONS;',ctx);vm.runInContext(fs.readFileSync('portable/local-service.js','utf8'),ctx);
function memory(){let snap={revision:0,data:{records:[]}};return {read:async()=>JSON.parse(JSON.stringify(snap)),write:async(expected,data)=>{assert.equal(snap.revision,expected);snap={revision:expected+1,data:JSON.parse(JSON.stringify(data))}},snapshot:()=>snap}}
(async()=>{const storage=memory(),api=ctx.QituLocalFactory.createService(storage).request;
assert.equal((await api('/auth/session')).user.account,'本地工作台');
const resume=await api('/resumes','POST',{name:'演示简历',content:{skills:['JavaScript']}});
let row=await api('/workspace-records','POST',{companyName:'演示公司',jobTitle:'工程师',city:'杭州',stageGroup:'TEST',stageDetail:'',resumeId:resume.id,resumeVersion:resume.version,notes:'原始备注',assessments:[{title:'技术测评',deadline:'2026-11-01T18:00'}]});
async function update(fields){row=await api('/workspace-records/'+row.recordId,'PATCH',{...fields,applicationVersion:row.applicationVersion,jobVersion:row.jobVersion});return row}
await update({stageGroup:'INTERVIEW',stageDetail:'SECOND'});const historyIndex=row.history.length-1;assert.equal(row.history[historyIndex].fromStageGroup,'TEST');
row=await api('/workspace-records/'+row.recordId+'/progress-experience','POST',{historyIndex,summary:'演示复盘',applicationVersion:row.applicationVersion,jobVersion:row.jobVersion});
row=await api('/workspace-records/'+row.recordId+'/undo-progress','POST',{historyIndex,applicationVersion:row.applicationVersion,jobVersion:row.jobVersion});assert.equal(row.stageGroup,'TEST');assert.equal(row.notes,'原始备注');assert.equal(row.assessments.length,1);assert(row.history[historyIndex].undoneAt);assert.equal(row.history[historyIndex].experience.summary,'演示复盘');
await assert.rejects(()=>api('/workspace-records/'+row.recordId,'PATCH',{stageGroup:'TERMINATED',stageDetail:'',applicationVersion:1,jobVersion:row.jobVersion}));
await assert.rejects(()=>update({assessments:[{title:'',deadline:''}]}));
let interview=await api('/applications/'+row.applicationId+'/interviews','POST',{title:'技术面试',round:1,durationMinutes:60,startAt:'2026-11-02T14:00:00+08:00',format:'VIDEO'});assert.equal((await api('/reminders')).length,2);interview=await api('/interviews/'+interview.id+'/review','PUT',{version:1,review:{summary:'面试总结'}});assert.equal(interview.review.summary,'面试总结');
const preview=await api('/job-imports','POST',{type:'CSV',text:'公司,岗位,岗位城市\n示例B,数据分析,上海\n示例B,数据分析,上海\n,错误,北京'});assert.equal(preview.rows.map(r=>r.status).join(','),'VALID,DUPLICATE,INVALID');assert.equal((await api('/job-imports/confirm','POST',{rows:preview.rows.filter(x=>x.status==='VALID').map(x=>x.normalizedPreview)})).created,1);
const count=(await api('/workspace-records')).length,backup=await api('/admin/backups','POST',{});assert.equal((await api('/admin/restores/validate','POST',{backup})).count,storage.snapshot().data.records.length);const invalid=JSON.parse(JSON.stringify(backup));invalid.checksum='bad';await assert.rejects(()=>api('/admin/restores/validate','POST',{backup:invalid}));
await api('/workspace-records/'+row.recordId,'DELETE',{applicationVersion:row.applicationVersion,jobVersion:row.jobVersion});assert.equal((await api('/workspace-records')).length,count-1);await api('/admin/restores','POST',{backup,confirmation:'恢复本机数据'});assert.equal((await api('/workspace-records')).length,count);
const resumed=ctx.QituLocalFactory.createService(storage);assert.equal((await resumed.request('/workspace-records')).length,count);
// Shared required-field schema applies equally offline.
await assert.rejects(()=>api('/resumes/'+resume.id+'/content','PUT',{version:1,content:{editorSchema:'honor-reference-v2',basics:{name:'缺项'}}}));
const restored=(await api('/workspace-records')).find(x=>x.recordId===row.recordId);assert.equal(restored.history[historyIndex].experience.summary,'演示复盘');
// A separate browser workspace can restore an original server-format backup.
if(process.env.QITU_TEST_BACKUP){const original=JSON.parse(fs.readFileSync(process.env.QITU_TEST_BACKUP,'utf8')),other=ctx.QituLocalFactory.createService(memory());await other.request('/admin/restores/validate','POST',{backup:original});await other.request('/admin/restores','POST',{backup:original,confirmation:'恢复本机数据'});assert.equal((await other.request('/resumes')).length,1)}
// Stage ownership and structured notes survive reload; group interviews omit hidden counts.
for(const [group,detail,experience] of [
 ['TEST','',{notes:'测评经验'}],
 ['INTERVIEW','FIRST',{interviewType:'SOLO',candidateCount:20,interviewer:'业务负责人',questions:'1. **项目**',other:'复盘'}],
 ['INTERVIEW','GROUP',{interviewType:'GROUP',candidateCount:10,questions:'1. 分工讨论'}],
 ['OFFER_CALL','PENDING',{initialOffer:'1. 月薪',negotiatedOffer:'1. 签字费'}]
]){
 let r=await api('/workspace-records','POST',{companyName:'经验测试'+group+detail,jobTitle:'岗位',stageGroup:group,stageDetail:detail});
 r=await api('/workspace-records/'+r.recordId,'PATCH',{stageGroup:'TERMINATED',stageDetail:'',applicationVersion:r.applicationVersion,jobVersion:r.jobVersion});
 const args={historyIndex:r.history.length-1,applicationVersion:r.applicationVersion,jobVersion:r.jobVersion};
 if(group==='INTERVIEW'&&detail==='FIRST')await assert.rejects(()=>api('/workspace-records/'+r.recordId+'/progress-experience','POST',{...args,experience:{...experience,candidateCount:21}}));
 r=await api('/workspace-records/'+r.recordId+'/progress-experience','POST',{...args,experience:{...experience,kind:'TEST'}});
 const saved=r.history.at(-1).experience;assert.equal(saved.kind,group);assert.equal(saved.schemaVersion,2);
 if(detail==='GROUP')assert(!('candidateCount' in saved));
 const reopened=(await api('/workspace-records')).find(x=>x.recordId===r.recordId);assert.deepEqual(reopened.history.at(-1).experience,saved);
}
console.log('离线存储：新建/阶段/撤销/经验/面试/测评/导入/备份校验/恢复/重开/必填检查通过');
})().catch(e=>{console.error(e);process.exitCode=1});
