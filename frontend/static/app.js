const $ = selector => document.querySelector(selector);
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const today = () => {
  const now = new Date();
  return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
};
const modules = [['inventory','Inventario'],['recipes','Recetas'],['prices','Productos y precios'],['planning','Planificación'],['daily','Registro diario'],['reports','Reportes']];
let state = {ingredients:[], recipes:[], prices:[], plans:[], daily:[]};
const option = (value, text) => '<option value="' + escape(value) + '">' + escape(text) + '</option>';
function show(id) {
  for (const [section] of modules) $('#' + section).hidden = section !== id;
  document.querySelectorAll('nav button').forEach(button => {
    if (button.dataset.target === id) button.setAttribute('aria-current','page');
    else button.removeAttribute('aria-current');
  });
}
for (const [id, label] of modules) {
  const button = document.createElement('button');
  button.dataset.target = id;
  button.textContent = label;
  button.onclick = () => show(id);
  $('nav').append(button);
}
show('inventory');
document.querySelectorAll('.units').forEach(el => el.innerHTML = ['kg','L','unidad'].map(u => option(u,u)).join(''));
function dates() {
  document.querySelectorAll('input[type=date]').forEach(el => { if (!el.value) el.value = today(); });
}
function notify(message, error = false) {
  $('#notice').textContent = message;
  $('#notice').classList.toggle('error', error);
}
async function request(path, data) {
  const response = await fetch(path, data === undefined ? {} : {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}
function table(headers, rows) {
  if (!rows.length) return '<p>Sin registros.</p>';
  return '<table><thead><tr>' + headers.map(h => '<th scope="col">' + escape(h) + '</th>').join('') +
    '</tr></thead><tbody>' + rows.map(row => '<tr>' + row.map(value => '<td>' + escape(value) + '</td>').join('') + '</tr>').join('') + '</tbody></table>';
}
function prices() {
  const search = $('#search').value.trim().toLocaleLowerCase('es');
  $('#prices-table').innerHTML = table(['Producto','Unidad','Precio (S/)','Fuente','Ubicación','Fecha'],
    state.prices.filter(p => p.product.toLocaleLowerCase('es').includes(search))
      .map(p => [p.product,p.unit,p.amount,p.source,p.location,p.observed]));
}
function options(selector, markup) {
  document.querySelectorAll(selector).forEach(el => {
    const value = el.value;
    el.innerHTML = markup;
    if (Array.from(el.options).some(entry => entry.value === value)) el.value = value;
  });
}
function render() {
  options('.recipe-select', option('','Selecciona un plato') + state.recipes.map(r => option(r.id,r.name)).join(''));
  options('#quote', option('','Usar costo de inventario') + state.prices.map(p => option(p.id,p.product + ' · S/ ' + p.amount + '/' + p.unit + ' · ' + p.location + ' · ' + p.observed)).join(''));
  options('.ingredient-select', option('','Selecciona un ingrediente') + state.ingredients.map(i => option(i.id,i.name + ' (' + i.unit + ')')).join(''));
  $('#inventory-table').innerHTML = table(['Ingrediente','Unidad','Existencia','Costo unitario (S/)'], state.ingredients.map(i => [i.name,i.unit,i.stock,i.cost]));
  $('#recipes-table').innerHTML = table(['Plato','Rendimiento','Precio por porción (S/)'], state.recipes.map(r => [r.name,r.yield,r.price]));
  $('#daily-table').innerHTML = table(['Fecha','Plato','Preparadas','Vendidas','Sobrantes','Pedidos no atendidos'],
    state.daily.map(d => [d.day,d.name,d.prepared,d.sold,d.leftover,d.missed]));
  $('#reports-table').innerHTML = table(['Fecha','Plato','Plan','Margen estimado (S/)','Vendidas reales','Sobrantes previstos','Sobrantes reales'], state.plans.map(p => {
    const s = JSON.parse(p.snapshot).chosen;
    const actual = state.daily.find(d => d.day === p.day && d.recipe_id === p.recipe_id);
    return [p.day,p.name,s.portions,s.margin,actual?.sold ?? 'Pendiente',s.leftover,actual?.leftover ?? 'Pendiente'];
  }));
  $('#purchase-list').innerHTML = state.plans.map(p => {
    const s = JSON.parse(p.snapshot).chosen;
    return '<details><summary>Lista de compras · ' + escape(p.name) + ' · ' + escape(p.day) +
      '</summary>' + table(['Ingrediente','Unidad','Faltante','Referencia'], s.supplies.filter(i => Number(i.missing) > 0)
        .map(i => [i.ingredient,i.unit,i.missing,i.source])) + '</details>';
  }).join('');
  prices();
}
function addItem() {
  const item = document.createElement('div');
  item.className = 'item';
  item.innerHTML = '<label>Ingrediente<select class="ingredient-select" required></select></label><label>Cantidad por receta<input type="number" step="any" min="0.000001" required></label><button type="button" class="secondary">Quitar</button>';
  item.querySelector('button').onclick = () => item.remove();
  $('.items').append(item);
  render();
}
$('#add-item').onclick = addItem;
$('#search').oninput = prices;
function scenarios(result, payload) {
  const output = $('#scenario-output');
  output.innerHTML = '<p>Demanda estimada: <strong>' + result.expected + '</strong> porciones · ' +
    (result.samples ? result.samples + ' registros del mismo día de la semana' : 'Estimación inicial ingresada') +
    '</p><div class="cards">' + result.scenarios.map(s => '<article class="card"><h3>' + s.portions +
    ' porciones</h3><p>' + (s.portions === result.recommended ? 'Recomendado · ' : '') +
    (s.within_budget ? 'Dentro del presupuesto' : 'Supera el presupuesto') + '</p><p>Ventas: ' + s.sales +
    ' · Sobrantes: ' + s.leftover + ' · No atendidas: ' + s.unmet + '</p><p>Compras: S/ ' + s.purchase +
    ' · Margen: S/ ' + s.margin + '</p><div class="scroll">' + table(['Ingrediente','Unidad','Requerido','Faltante'],
      s.supplies.map(i => [i.ingredient,i.unit,i.required,i.missing])) + '</div>' +
    (s.within_budget ? '<button data-portions="' + s.portions + '">Guardar este plan</button>' : '') + '</article>').join('') + '</div>';
  output.querySelectorAll('button').forEach(btn => btn.onclick = async () => {
    btn.disabled = true;
    try {
      await request('/api/plan', {...payload, portions:btn.dataset.portions});
      await refresh();
      notify('Plan guardado. La lista de compras está disponible en Reportes.');
      show('reports');
    } catch (error) { notify(error.message,true); }
    finally { btn.disabled = false; }
  });
}
async function refresh() { state = await request('/api/state'); render(); }
for (const form of document.querySelectorAll('form')) form.onsubmit = async event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  const action = form.dataset.action;
  const submit = form.querySelector('button:not([type=button])');
  submit.disabled = true;
  if (action === 'calculate') $('#scenario-output').replaceChildren();
  try {
    if (action === 'recipe') data.items = [...form.querySelectorAll('.item')].map(row => ({
      ingredient_id: row.querySelector('select').value, quantity: row.querySelector('input').value
    }));
    const result = await request('/api/' + action,data);
    if (action === 'calculate') { scenarios(result,data); notify('Escenarios calculados.'); }
    else {
      form.reset();
      dates();
      if (action === 'recipe') { $('.items').replaceChildren(); addItem(); }
      await refresh();
      notify('Registro guardado.');
    }
  } catch (error) { notify(error.message,true); }
  finally { submit.disabled = false; }
};
dates();
refresh().then(addItem).catch(error => notify(error.message,true));
