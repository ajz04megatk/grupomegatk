import test from 'node:test';
import assert from 'node:assert/strict';
import { date, totalsByCurrency, upcoming, rpc, SessionExpired } from '../../src/mobile/core.mjs';

test('separa saldos de distintas monedas', () => {
    assert.deepEqual(totalsByCurrency([{currency:'HNL', balance:25000},{currency:'USD',balance:100},{currency:'HNL',balance:45000}], 'balance'), {HNL:70000, USD:100});
});
test('las fechas del contrato no cambian de día en Honduras', () => {
    assert.match(date('2026-11-14'), /14/);
    assert.equal(date(false), 'Sin fecha');
});
test('la próxima cuota solo considera operaciones activas y ordena por fecha', () => {
    const ops = [{id:1,state:'contracted',next_payment:{date:'2026-01-01'}},{id:2,state:'active',next_payment:{date:'2026-12-01'}},{id:3,state:'active',next_payment:{date:'2026-11-01'}},{id:4,state:'active',next_payment:false}];
    assert.deepEqual(upcoming(ops).map(x=>x.id), [3,2]);
});
test('consulta JSON-RPC con sesión, sin caché ni credenciales en el cuerpo', async () => {
    const result = await rpc('/lenka/mobile/v1/operations', async (path, options) => {
        assert.equal(path, '/lenka/mobile/v1/operations');
        assert.equal(options.credentials, 'same-origin');
        assert.equal(options.cache, 'no-store');
        assert.deepEqual(JSON.parse(options.body).params, {});
        assert.equal(options.headers.Authorization, undefined);
        return {ok:true, json:async()=>({result:[{id:3}]})};
    });
    assert.deepEqual(result, [{id:3}]);
});
test('rechaza destinos ajenos a la API Lenka', async () => {
    let called = false;
    await assert.rejects(rpc('https://elsewhere.invalid', async()=>{called=true;}), /Ruta no permitida/);
    assert.equal(called, false);
});
test('sesión vencida exige volver a iniciar sesión', async () => {
    await assert.rejects(rpc('/lenka/mobile/v1/operations', async()=>({status:401})), SessionExpired);
    await assert.rejects(rpc('/lenka/mobile/v1/operations', async()=>({ok:true,json:async()=>({error:{data:{name:'odoo.http.SessionExpiredException'}}})})), SessionExpired);
});
test('un error del servidor no expone el traceback', async () => {
    await assert.rejects(rpc('/lenka/mobile/v1/operations/3', async()=>({ok:true,json:async()=>({error:{data:{name:'odoo.exceptions.AccessError',debug:'SECRET TRACE'}}})})), e=>!e.message.includes('SECRET') && /acceso/.test(e.message));
});
