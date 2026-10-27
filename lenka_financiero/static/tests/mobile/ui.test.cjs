const { chromium } = require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES ? process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES + '/playwright' : 'playwright');
const fs=require('fs'), path=require('path'), http=require('http'), assert=require('assert/strict');
const root=process.cwd();
const server=http.createServer((req,res)=>{
 const p=req.url.split('?')[0];
 let file,content;
 if(p==='/lenka/app'){content=fs.readFileSync(path.join(root,'lenka_financiero/views/mobile_app.xml'),'utf8').match(/<html[\s\S]*?<\/html>/)[0];res.setHeader('Content-Type','text/html');}
 else {file=path.join(root,p);if(!file.startsWith(root)||!fs.existsSync(file)){res.writeHead(404);return res.end();}content=fs.readFileSync(file);res.setHeader('Content-Type',p.endsWith('.mjs')?'text/javascript':p.endsWith('.css')?'text/css':p.endsWith('.png')?'image/png':'application/json');}
 res.end(content);
});
const operations=[{id:3,name:'LENKA-OP-000003',type:'loan',state:'active',currency:'HNL',principal_amount:70000,financed_amount:70000,outstanding_capital:70000,interest_rate:2,rate_period:'monthly',term_months:12,next_payment:{sequence:1,date:'2026-11-14',amount_due:6500,state:'pending'}},{id:4,name:'LENKA-OP-000004',type:'loan',state:'active',currency:'USD',principal_amount:100,outstanding_capital:100,next_payment:false}];
const investments=[{id:1,name:'LENKA-INV-000001',state:'active',currency:'HNL',principal_amount:50000,outstanding_principal:50000,accrued_interest:500,passive_rate:1,rate_period:'monthly',maturity_date:'2027-01-01'}];
const statements=[{id:1,name:'Estado de cuenta · Octubre 2026',date_from:'2026-10-01',date_to:'2026-10-31',currency:'HNL',opening_balance:70000,closing_balance:70000,period_capital:0,period_interest:0,period_late_fees:0,period_fees:0}];
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const origin=`http://127.0.0.1:${server.address().port}`;
 const launch = { headless: true }; if (process.env.LENKA_CHROMIUM_EXECUTABLE) launch.executablePath = process.env.LENKA_CHROMIUM_EXECUTABLE; const browser=await chromium.launch(launch);const page=await browser.newPage({viewport:{width:390,height:844}});let mode='ok';const logs=[];page.on('pageerror',e=>logs.push(e.message));
 await page.route('**/lenka/mobile/v1/**',async route=>{
  const url=new URL(route.request().url());let result;
  if(mode==='session')return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({error:{data:{name:'odoo.http.SessionExpiredException'}}})});
  if(mode==='error')return route.fulfill({status:500,body:'SERVER TRACE SECRET'});
  if(url.pathname.endsWith('dashboard'))result={partner:{name:'Cliente de prueba',email:'test@example.invalid'}};
  else if(url.pathname.endsWith('operations/3'))result={...operations[0],schedule:[{sequence:1,date:'2026-11-14',capital:5100,interest:1400,late_fee_due:0,amount_due:6500,payment_state:'pending'}],payments:[{id:1,name:'LENKA-COB-PRUEBA',date:'2026-10-27',gross_amount:1000,net_amount:1000,card_fee:0,capital:600,interest:400,late_fee:0}]};
  else if(url.pathname.endsWith('investments/1'))result={...investments[0],interest_history:[{date:'2026-10-01',amount:500}],withdrawals:[]};
  else if(url.pathname.endsWith('operations'))result=mode==='empty'?[]:operations;
  else if(url.pathname.endsWith('investments'))result=mode==='empty'?[]:investments;
  else if(url.pathname.endsWith('statements'))result=mode==='empty'?[]:statements;
  return route.fulfill({contentType:'application/json',body:JSON.stringify({result})});
 });
 await page.goto(origin+'/lenka/app');await page.getByRole('heading',{name:'Cliente de prueba'}).waitFor();
 for(const width of [360,390,768,1280]){await page.setViewportSize({width,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),`overflow ${width}`);}
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'/tmp/lenka-mobile-home.png',fullPage:true});
 assert.match(await page.locator('main').innerText(),/70,000/);assert.match(await page.locator('main').innerText(),/100/);
 await page.getByRole('button',{name:'Préstamos',exact:true}).click();await page.getByRole('button',{name:'Ver préstamo y pagos'}).first().click();await page.getByRole('heading',{name:'Plan de pagos'}).waitFor();assert.match(await page.locator('main').innerText(),/14/);assert.match(await page.locator('main').innerText(),/LENKA-COB-PRUEBA/);await page.screenshot({path:'/tmp/lenka-mobile-detail.png',fullPage:true});
 await page.getByRole('button',{name:'Inversiones',exact:true}).click();await page.getByRole('button',{name:'Ver inversión',exact:true}).click();await page.getByRole('heading',{name:'Retiros aplicados'}).waitFor();
 await page.getByRole('button',{name:'Estados',exact:true}).click();await page.getByRole('heading',{name:'Estados de cuenta',exact:true}).waitFor();assert.match(await page.locator('main').innerText(),/Octubre 2026/);
 mode='error';await page.getByRole('button',{name:'Actualizar información'}).click();await page.getByRole('alert').waitFor();assert(!((await page.locator('main').innerText()).includes('SECRET')));
 mode='ok';await page.getByRole('button',{name:'Intentar de nuevo'}).click();await page.getByRole('heading',{name:'Estados de cuenta',exact:true}).waitFor();
 mode='session';await page.getByRole('button',{name:'Actualizar información'}).click();await page.getByRole('link',{name:'Iniciar sesión'}).waitFor();
 mode='empty';await page.reload();await page.getByRole('heading',{name:'Estados de cuenta',exact:true}).count();await page.getByRole('heading',{name:'Cliente de prueba'}).waitFor();await page.getByRole('button',{name:'Préstamos',exact:true}).click();assert.match(await page.locator('main').innerText(),/Todavía no tenés préstamos/);
 await page.context().setOffline(true);await page.getByRole('alert').waitFor();assert.match(await page.locator('main').innerText(),/No hay conexión/);await page.context().setOffline(false);await page.getByRole('heading',{name:'Mis préstamos'}).waitFor();
 assert.equal(await page.evaluate(()=>localStorage.length),0);assert.equal(logs.length,0,logs.join('\n'));
 console.log('PASS: responsive 360/390/768/1280; préstamos/detalle/pagos; inversiones/retiros; estados; errores sin traceback; sesión vencida; vacíos; offline/reconexión; sin localStorage; sin errores JS. Datos ficticios.');
 await browser.close();server.close();
})().catch(e=>{console.error(e);server.close();process.exit(1)});
