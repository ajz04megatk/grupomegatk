import { labels, money, date, totalsByCurrency, upcoming, rpc, SessionExpired } from './core.mjs';

const root = document.querySelector('#lenka-app');
const state = { operations: [], investments: [], statements: [], partner: {}, page: 'home', loading: true, error: '', detail: null, expired: false };
let requestNumber = 0;
const el = (tag, text, className = '') => {
    const node = document.createElement(tag); node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
};
function button(text, action, className = 'button') {
    const node = el('button', text, className); node.type = 'button'; node.addEventListener('click', action); return node;
}
function row(title, value) {
    const node = el('div', null, 'data-row'); node.append(el('span', title), el('strong', value)); return node;
}
function card(title, subtitle) {
    const node = el('section', null, 'card'); node.append(el('h2', title));
    if (subtitle) node.append(el('p', subtitle, 'muted')); return node;
}
function empty(text) { return el('p', text, 'empty'); }
function summary(title, records, field) {
    const node = card(title);
    const totals = Object.entries(totalsByCurrency(records, field));
    if (!totals.length) node.append(el('p', 'Sin saldo registrado', 'muted'));
    for (const [currency, value] of totals) node.append(el('p', money(value, currency), 'balance'));
    return node;
}
function changePage(page) { requestNumber++; state.page = page; state.detail = null; state.error = ''; render(); }
async function load() {
    const current = ++requestNumber; state.loading = true; state.detail = null; state.error = ''; state.expired = false; render();
    try {
        const [dashboard, operations, investments, statements] = await Promise.all([
            rpc('/lenka/mobile/v1/dashboard'), rpc('/lenka/mobile/v1/operations'),
            rpc('/lenka/mobile/v1/investments'), rpc('/lenka/mobile/v1/statements'),
        ]);
        if (current !== requestNumber) return;
        Object.assign(state, { partner: dashboard.partner, operations, investments, statements });
    } catch (error) {
        if (current !== requestNumber) return;
        state.expired = error instanceof SessionExpired;
        state.error = state.expired ? 'Tu sesión terminó. Iniciá sesión para continuar.' : navigator.onLine === false ? 'No hay conexión. Conectate para consultar tus saldos actualizados.' : error.message;
    } finally { if (current === requestNumber) { state.loading = false; render(); } }
}
async function openDetail(kind, id) {
    const current = ++requestNumber; state.loading = true; state.error = ''; state.detail = null; render();
    try {
        const detail = await rpc(`/lenka/mobile/v1/${kind}/${Number(id)}`);
        if (current === requestNumber) state.detail = { ...detail, kind };
    } catch (error) {
        if (current === requestNumber) { state.expired = error instanceof SessionExpired; state.error = state.expired ? 'Tu sesión terminó. Iniciá sesión para continuar.' : error.message; }
    } finally { if (current === requestNumber) { state.loading = false; render(); } }
}
function operationList(main) {
    main.append(el('h1', 'Mis préstamos'));
    if (!state.operations.length) main.append(empty('Todavía no tenés préstamos disponibles para consultar.'));
    for (const o of state.operations) {
        const node = card(o.name, labels[o.type] || o.type);
        node.append(row('Estado', labels[o.state] || o.state), row(['active', 'done'].includes(o.state) ? 'Capital pendiente' : 'Capital de la operación', money(o.outstanding_capital, o.currency)));
        if (o.next_payment && o.state === 'active') node.append(row('Próxima cuota', date(o.next_payment.date)), row('Pendiente de la cuota', money(o.next_payment.amount_due, o.currency)));
        node.append(button('Ver préstamo y pagos', () => openDetail('operations', o.id))); main.append(node);
    }
}
function investmentsList(main) {
    main.append(el('h1', 'Mis inversiones'));
    if (!state.investments.length) main.append(empty('Todavía no tenés inversiones disponibles para consultar.'));
    for (const i of state.investments) {
        const node = card(i.name, labels[i.state] || i.state);
        node.append(row('Capital vigente', money(i.outstanding_principal, i.currency)), row('Intereses acumulados', money(i.accrued_interest, i.currency)), row('Vencimiento', date(i.maturity_date)), button('Ver inversión', () => openDetail('investments', i.id))); main.append(node);
    }
}
function statementsList(main) {
    main.append(el('h1', 'Estados de cuenta'));
    if (!state.statements.length) main.append(empty('Todavía no hay estados de cuenta publicados.'));
    for (const s of state.statements) {
        const node = card(s.name, `${date(s.date_from)} — ${date(s.date_to)}`);
        node.append(row('Saldo inicial', money(s.opening_balance, s.currency)), row('Capital del período', money(s.period_capital, s.currency)), row('Intereses del período', money(s.period_interest, s.currency)), row('Mora del período', money(s.period_late_fees, s.currency)), row('Comisiones del período', money(s.period_fees, s.currency)), row('Saldo final', money(s.closing_balance, s.currency))); main.append(node);
    }
}
function detail(main, d) {
    main.append(button('← Volver', () => { state.detail = null; render(); }, 'text-button'), el('h1', d.name));
    const loan = d.kind === 'operations';
    const node = card(loan ? 'Tu préstamo' : 'Tu inversión', labels[d.state] || d.state);
    node.append(row('Capital inicial', money(d.principal_amount, d.currency)), row('Capital pendiente', money(loan ? d.outstanding_capital : d.outstanding_principal, d.currency)), row('Tasa', `${loan ? d.interest_rate : d.passive_rate} % ${d.rate_period === 'monthly' ? 'mensual' : 'anual'}`)); main.append(node);
    if (loan) {
        main.append(el('h2', 'Plan de pagos'));
        if (!d.schedule.length) main.append(empty('No hay cuotas registradas.'));
        for (const line of d.schedule) {
            const q = card(`Cuota ${line.sequence} · ${date(line.date)}`, labels[line.payment_state] || line.payment_state);
            q.append(row('Capital', money(line.capital, d.currency)), row('Intereses', money(line.interest, d.currency)), row('Mora generada', money(line.late_fee_due, d.currency)), row('Pendiente', money(line.amount_due, d.currency))); main.append(q);
        }
        main.append(el('h2', 'Pagos registrados'));
        if (!d.payments.length) main.append(empty('Todavía no hay pagos aplicados.'));
        for (const p of d.payments) {
            const q = card(p.name, date(p.date));
            q.append(row('Importe recibido', money(p.gross_amount, d.currency)), row('Neto aplicado', money(p.net_amount, d.currency)), row('Comisión de tarjeta', money(p.card_fee, d.currency)), row('Capital', money(p.capital, d.currency)), row('Intereses', money(p.interest, d.currency)), row('Mora', money(p.late_fee, d.currency))); main.append(q);
        }
    } else {
        main.append(el('h2', 'Intereses registrados'));
        if (!d.interest_history.length) main.append(empty('Todavía no hay intereses registrados.'));
        for (const line of d.interest_history) main.append(row(date(line.date), money(line.amount, d.currency)));
        main.append(el('h2', 'Retiros aplicados'));
        if (!d.withdrawals.length) main.append(empty('Todavía no hay retiros aplicados.'));
        for (const w of d.withdrawals) main.append(row(date(w.date), money(w.total_amount, d.currency)));
    }
}
function home(main) {
    main.append(el('p', 'BIENVENIDO A LENKA', 'eyebrow'), el('h1', state.partner.name || 'Tu información financiera'), el('p', 'Consultá tus préstamos, pagos e inversiones en un solo lugar.', 'muted'));
    const grid = el('div', null, 'summary-grid'); grid.append(summary('Capital por pagar', state.operations.filter(o => ['active', 'done'].includes(o.state)), 'outstanding_capital'), summary('Capital invertido', state.investments, 'outstanding_principal')); main.append(grid);
    const next = upcoming(state.operations)[0];
    if (next) {
        const node = card('Tu próxima cuota', next.name);
        node.append(el('p', money(next.next_payment.amount_due, next.currency), 'balance'), row('Fecha', date(next.next_payment.date)), button('Ver plan de pagos', () => { state.page = 'operations'; openDetail('operations', next.id); })); main.append(node);
    }
    main.append(el('p', 'Información consultada en Odoo. Los importes de distintas monedas se muestran por separado.', 'footnote'));
}
function render() {
    root.replaceChildren();
    const header = el('header', null, 'topbar');
    const logo = el('img'); logo.src = '/lenka_financiero/static/description/icon.png'; logo.alt = 'Inversiones Lenka';
    header.append(logo, el('strong', 'Financiero Lenka'));
    const logout = el('a', 'Salir', 'text-button'); logout.href = '/web/session/logout?redirect=/lenka/app'; header.append(logout); root.append(header);
    const main = el('main'); main.id = 'contenido'; main.setAttribute('aria-busy', String(state.loading));
    if (state.loading) { const busy = el('p', 'Consultando tu información…', 'empty'); busy.setAttribute('role', 'status'); main.append(busy); }
    else if (state.error) {
        const error = card('No pudimos mostrar la información'); error.setAttribute('role', 'alert'); error.append(el('p', state.error));
        if (state.expired) { const login = el('a', 'Iniciar sesión', 'button'); login.href = '/web/login?redirect=/lenka/app'; error.append(login); }
        else error.append(button('Intentar de nuevo', load)); main.append(error);
    } else if (state.detail) detail(main, state.detail);
    else ({home, operations: operationList, investments: investmentsList, statements: statementsList}[state.page])(main);
    if (!state.loading && !state.error) main.append(button('Actualizar información', load, 'text-button refresh'));
    root.append(main);
    const nav = el('nav', null, 'bottom-nav'); nav.setAttribute('aria-label', 'Navegación principal');
    for (const [page, label] of [['home','Inicio'], ['operations','Préstamos'], ['investments','Inversiones'], ['statements','Estados']]) {
        const b = button(label, () => changePage(page), state.page === page ? 'nav-item selected' : 'nav-item');
        b.disabled = state.loading || Boolean(state.error); if (state.page === page) b.setAttribute('aria-current', 'page'); nav.append(b);
    }
    root.append(nav);
}
window.addEventListener('offline', () => { requestNumber++; state.loading = false; state.detail = null; state.error = 'No hay conexión. Conectate para consultar tus saldos actualizados.'; render(); });
window.addEventListener('online', load);
load();
