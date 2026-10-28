/* Local motion primitives, including native-dialog exit transitions. */
const surfaceAnimations=new WeakMap();
function reducedMotion(){return typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches}
function cancelSurfaceMotion(element){const old=surfaceAnimations.get(element);if(old){surfaceAnimations.delete(element);old.cancel()}}
function animateSurfaceIn(element,kind='modal'){
 const ongoing=surfaceAnimations.has(element)&&typeof getComputedStyle==='function'?getComputedStyle(element):null;const start=ongoing?{opacity:ongoing.opacity,transform:ongoing.transform,filter:ongoing.filter}:null;cancelSurfaceMotion(element);if(reducedMotion()||!element.animate)return;
 const frames={
  modal:[{opacity:0,transform:'translateY(22px) scale(.965)',filter:'blur(3px)'},{opacity:1,transform:'translateY(-2px) scale(1.006)',filter:'blur(0px)',offset:.7},{opacity:1,transform:'translateY(0) scale(1)',filter:'blur(0px)'}],
  drawer:[{opacity:0,transform:'translateX(48px) scale(.985)'},{opacity:1,transform:'translateX(-3px) scale(1)',offset:.76},{opacity:1,transform:'translateX(0) scale(1)'}],
  notice:[{opacity:0,transform:'translate(18px,-15px) scale(.94)',filter:'blur(3px)'},{opacity:1,transform:'translate(-2px,2px) scale(1.012)',filter:'blur(0px)',offset:.7},{opacity:1,transform:'translate(0,0) scale(1)',filter:'blur(0px)'}],
  menu:[{opacity:0,transform:'translateY(-5px) scale(.98)'},{opacity:1,transform:'translateY(0) scale(1)'}],
  toast:[{opacity:0,transform:'translate(-50%,8px) scale(.97)'},{opacity:1,transform:'translate(-50%,0) scale(1)'}]
 };
 const entry=frames[kind]||frames.modal;if(start)entry[0]=start;
 const animation=element.animate(entry,{duration:kind==='notice'?440:kind==='drawer'?440:kind==='menu'?180:360,easing:'cubic-bezier(.22,.8,.26,1)',fill:'both'});surfaceAnimations.set(element,animation);
 animation.finished.then(()=>{if(surfaceAnimations.get(element)===animation){surfaceAnimations.delete(element);animation.cancel()}}).catch(()=>{});
}
function animateSurfaceOut(element,kind='modal',finish=()=>{}){
 const current=typeof getComputedStyle==='function'?getComputedStyle(element):null;const start=current?{opacity:current.opacity,transform:current.transform,filter:current.filter}:null;cancelSurfaceMotion(element);if(reducedMotion()||!element.animate){finish();return}
 const transforms={modal:'translateY(10px) scale(.975)',drawer:'translateX(35px) scale(.99)',notice:'translate(18px,-8px) scale(.96)',menu:'translateY(-4px) scale(.98)',toast:'translate(-50%,7px) scale(.97)'};
 const initial=kind==='toast'?'translate(-50%,0) scale(1)':'translate(0,0) scale(1)';
 const animation=element.animate([start||{opacity:1,transform:initial,filter:'blur(0px)'},{opacity:0,transform:transforms[kind]||transforms.modal,filter:kind==='notice'?'blur(2px)':'blur(0px)'}],{duration:kind==='menu'?130:kind==='drawer'?250:210,easing:'cubic-bezier(.4,0,.8,.35)',fill:'both'});surfaceAnimations.set(element,animation);
 animation.finished.then(()=>{if(surfaceAnimations.get(element)===animation){surfaceAnimations.delete(element);finish();animation.cancel()}}).catch(()=>{});
}
function installDialogMotion(dialog){const nativeShow=dialog.showModal.bind(dialog),nativeClose=dialog.close.bind(dialog);let closing=false;
 dialog.showModal=function(){closing=false;dialog.classList.remove('surface-closing');if(!dialog.open)nativeShow();animateSurfaceIn(dialog,dialog.id==='record-drawer'?'drawer':'modal')};
 dialog.close=function(value){if(!dialog.open||closing)return;closing=true;dialog.classList.add('surface-closing');animateSurfaceOut(dialog,dialog.id==='record-drawer'?'drawer':'modal',()=>{if(!closing)return;nativeClose(value);closing=false;dialog.classList.remove('surface-closing')})};
 if(dialog.id!=='record-drawer')dialog.addEventListener('cancel',event=>{if(!event.defaultPrevented){event.preventDefault();dialog.close()}});
}
document.querySelectorAll('dialog').forEach(installDialogMotion);

/* Animate only newly navigated content, never every keystroke or table row. */
function animateContent(element,delay=0){
 if(!element||reducedMotion()||!element.animate)return;
 const animation=element.animate([{opacity:.35,transform:'translateY(8px)'},{opacity:1,transform:'translateY(0)'}],{duration:240,delay,easing:'cubic-bezier(.2,.75,.25,1)',fill:'backwards'});
 animation.finished.then(()=>animation.cancel()).catch(()=>{});
}
let contentFrame=0;
new MutationObserver(records=>{
 if(!records.some(r=>r.target.id==='content'||[...r.addedNodes].some(n=>n.nodeType===1&&(n.id==='content'||n.querySelector?.('#content')))))return;
 cancelAnimationFrame(contentFrame);contentFrame=requestAnimationFrame(()=>{
  const content=document.querySelector('#content');if(!content)return;
  [...content.children].filter(el=>!el.hidden).slice(0,5).forEach((el,i)=>animateContent(el,i*25));
 });
}).observe(document.querySelector('#app'),{childList:true,subtree:true});
