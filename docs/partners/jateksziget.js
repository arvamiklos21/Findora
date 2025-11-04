// partners/jateksziget.js
export async function init(cfg){
  // cfg: { container, dt, feed, utm, title }
  const root = document.querySelector(cfg.container);
  if (!root) return;

  // ha már egyszer felépítettük, ne építsük újra
  if (root.dataset.ready === '1') return;
  root.dataset.ready = '1';

  // UI váz
  root.innerHTML = `
    <section style="max-width:1200px;margin:0 auto;padding:16px">
      <h1 style="margin:6px 0 14px 0">${cfg.title || 'Játéksziget – Ajánlatok'}</h1>

      <header style="display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:8px">
        <button onclick="history.back()">⟵ Vissza</button>
        <div style="display:flex;gap:8px;align-items:center">
          <label for="sortAll_j">Rendezés:</label>
          <select id="sortAll_j">
            <option value="price_asc">Ár ↑ (olcsóbb elöl)</option>
            <option value="price_desc">Ár ↓ (drágább elöl)</option>
          </select>
        </div>
        <div style="opacity:.8" id="statsAll_j"></div>
      </header>

      <nav style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <button id="tabAll_j" class="tab active" data-tab="all">Összes</button>
        <button id="tabD25_j" class="tab" data-tab="d25">–25–49%</button>
        <button id="tabD50_j" class="tab" data-tab="d50">–50%+</button>
      </nav>

      <div id="wrapAll_j">
        <div id="gridAll_j" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px"></div>
        <nav id="pagerAll_j" style="display:flex;gap:6px;align-items:center;justify-content:center;margin-top:12px"></nav>
      </div>

      <div id="wrapD25_j" hidden>
        <div id="gridD25_j" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px"></div>
        <nav id="pagerD25_j" style="display:flex;gap:6px;align-items:center;justify-content:center;margin-top:12px"></nav>
      </div>

      <div id="wrapD50_j" hidden>
        <div id="gridD50_j" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px"></div>
        <nav id="pagerD50_j" style="display:flex;gap:6px;align-items:center;justify-content:center;margin-top:12px"></nav>
      </div>
    </section>

    <style>
      .tab { padding:8px 10px; border:1px solid #ddd; border-radius:999px; background:#fff; cursor:pointer }
      .tab.active { background:#111; color:#fff; border-color:#111 }
      .card { border:1px solid #eee; border-radius:14px; padding:12px; display:flex; flex-direction:column; gap:10px; background:#fff; box-shadow:0 1px 2px rgba(0,0,0,.04) }
      .price-pill { margin-left:auto; font-size:.85rem; padding:2px 6px; border-radius:6px; border:1px solid #ddd }
    </style>
  `;

  // állapot – csak memóriában
  let loaded = false;
  let allItems = [];
  let listAll = [], listD25 = [], listD50 = [];
  let pageAll = 1, pageD25 = 1, pageD50 = 1;
  let curTab = 'all';

  // segédek
  const $ = s => root.querySelector(s);
  const Ft = n => (Math.round(n).toLocaleString("hu-HU") + " Ft");
  const pct = (oldP, nowP) => oldP>0 ? Math.round((1 - (nowP/oldP)) * 100) : 0;

  function dognetLink(targetUrl){
    const base = `https://go.dognet.com/?dt=${encodeURIComponent(cfg.dt)}&url=`;
    const utm = cfg.utm ? (targetUrl.includes("?") ? "&" : "?") + cfg.utm.replace(/^&/,"") : "";
    return base + encodeURIComponent(targetUrl + utm);
  }
  function parseNumber(s){
    if (s == null) return NaN;
    return Number(String(s).replace(/[^\d.,]/g,"").replace(",","."));
  }
  function el(tag, attrs={}, children=[]){
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k,v])=>{
      if(k==="class") e.className = v;
      else if(k==="html") e.innerHTML = v;
      else e.setAttribute(k,v);
    });
    (children||[]).forEach(c => e.appendChild(c));
    return e;
  }

  // feed – csak az első aktiváláskor
  async function loadOnce(){
    if (loaded) return;
    const res = await fetch(cfg.feed, { cache: 'no-store' });
    if (!res.ok) throw new Error('Feed letöltési hiba: ' + res.status);
    const xml = await res.text();
    const doc = new DOMParser().parseFromString(xml, 'text/xml');
    const nodes = Array.from(doc.getElementsByTagName('SHOPITEM'));

    allItems = nodes.map(n=>{
      const val = t => (n.getElementsByTagName(t)[0]?.textContent || '').trim();
      const id   = val('ITEM_ID') || val('ID') || val('CODE') || '';
      const name = val('PRODUCTNAME') || val('NAME') || '';
      const url  = val('URL') || '';
      const img  = val('IMGURL') || val('IMAGE') || '';
      const pNow = parseNumber(val('PRICE_VAT') || val('PRICE'));
      const pOld = parseNumber(val('OLD_PRICE')  || val('PRICE_ORIG') || val('PRICE_BEFORE'));
      const inStockRaw = val('AVAILABILITY') || val('IN_STOCK') || '';
      const inStock = /in|stock|rakt|skladem|igen|yes|1/i.test(inStockRaw);
      const brand= val('MANUFACTURER') || val('BRAND') || '';
      return {
        id, name, url, img,
        price: isNaN(pNow)?0:pNow,
        oldPrice: isNaN(pOld)?0:pOld,
        discount: (!isNaN(pOld) && pOld>0 && !isNaN(pNow)) ? pct(pOld, pNow) : 0,
        inStock, brand
      };
    }).filter(x=>x.name && x.url);

    listAll = [...allItems];
    listD25 = allItems.filter(x => x.discount >= 25 && x.discount < 50);
    listD50 = allItems.filter(x => x.discount >= 50);
    loaded = true;
  }

  // rendezés + kirajzolás
  function applySort(list){
    const s = $('#sortAll_j').value;
    if (s === 'price_asc') list.sort((a,b)=>a.price-b.price);
    if (s === 'price_desc') list.sort((a,b)=>b.price-a.price);
  }

  function renderList(list, page, gridId, pagerId){
    applySort(list);
    const grid = root.querySelector('#'+gridId);
    const pager = root.querySelector('#'+pagerId);
    grid.innerHTML = ''; pager.innerHTML = '';

    const PAGE_SIZE = 20;
    const total = list.length;
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (page > pages) page = pages;

    const from = (page-1)*PAGE_SIZE;
    const items = list.slice(from, from+PAGE_SIZE);

    items.forEach(p=>{
      const priceRow = el('div',{style:'display:flex;gap:6px;align-items:baseline;flex-wrap:wrap'});
      if (p.oldPrice && p.oldPrice > p.price){
        priceRow.appendChild(el('span',{style:'text-decoration:line-through;opacity:.6'},[document.createTextNode(Ft(p.oldPrice))]));
      }
      priceRow.appendChild(el('strong',{},[document.createTextNode(Ft(p.price))]));
      if (p.discount >= 25){
        priceRow.appendChild(el('span',{class:'price-pill'},[document.createTextNode(`-${p.discount}%`)]));
      }

      const card = el('article',{class:'card'});
      const a = el('a',{href: dognetLink(p.url), target:'_blank', rel:'nofollow sponsored noopener'});
      const img = el('img',{src:p.img, alt:p.name, loading:'lazy', style:'width:100%;aspect-ratio:1/1;object-fit:contain;border-radius:10px;background:#fafafa'});
      a.appendChild(img);

      card.appendChild(a);
      card.appendChild(el('a',{href: dognetLink(p.url), target:'_blank', rel:'nofollow sponsored noopener',
        style:'font-weight:600;line-height:1.3;text-decoration:none;color:#111'}, [document.createTextNode(p.name)]));
      card.appendChild(priceRow);

      const meta = el('div',{style:'font-size:.85rem;opacity:.75;display:flex;gap:8px;flex-wrap:wrap'});
      if (p.brand) meta.appendChild(el('span',{},[document.createTextNode(p.brand)]));
      if (p.inStock) meta.appendChild(el('span',{},[document.createTextNode('Raktáron')]));
      card.appendChild(meta);

      const cta = el('a',{href: dognetLink(p.url), target:'_blank', rel:'nofollow sponsored noopener',
        style:'margin-top:auto;display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:10px 12px;border-radius:10px;background:#111;color:#fff;text-decoration:none'},
        [document.createTextNode('Megnézem a Játékszigetnél →')]);
      card.appendChild(cta);

      grid.appendChild(card);
    });

    function addBtn(txt, to, disabled=false, bold=false){
      const b = el('button',{disabled});
      b.textContent = txt;
      if (bold) b.style.fontWeight = '700';
      if(!disabled) b.onclick = ()=>{
        if (gridId==='gridAll_j') pageAll = to;
        if (gridId==='gridD25_j') pageD25 = to;
        if (gridId==='gridD50_j') pageD50 = to;
        render();
      };
      pager.appendChild(b);
    }
    addBtn('⟨', Math.max(1, page-1), page<=1);
    const nums = new Set([1, page-1, page, page+1, pages].filter(p=>p>=1 && p<=pages));
    let last = 0;
    [...nums].sort((a,b)=>a-b).forEach(p=>{
      if (p - last > 1) pager.appendChild(el('span',{style:'padding:0 4px'},[document.createTextNode('…')]));
      addBtn(String(p), p, p===page, p===page);
      last = p;
    });
    addBtn('⟩', Math.min(pages, page+1), page>=pages);
  }

  function render(){
    $('#statsAll_j').textContent = `${allItems.length} termék • 20/oldal`;

    root.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
    root.querySelectorAll('[id^="wrap"]').forEach(w=>w.hidden=true);

    if (curTab==='all'){ $('#tabAll_j').classList.add('active'); $('#wrapAll_j').hidden=false; renderList(listAll, pageAll, 'gridAll_j', 'pagerAll_j'); }
    if (curTab==='d25'){ $('#tabD25_j').classList.add('active'); $('#wrapD25_j').hidden=false; renderList(listD25, pageD25, 'gridD25_j', 'pagerD25_j'); }
    if (curTab==='d50'){ $('#tabD50_j').classList.add('active'); $('#wrapD50_j').hidden=false; renderList(listD50, pageD50, 'gridD50_j', 'pagerD50_j'); }
  }

  // események
  root.addEventListener('click', (e)=>{
    const t = e.target.closest('.tab');
    if (t){
      curTab = t.dataset.tab;
      render();
    }
  });
  root.addEventListener('change', (e)=>{
    if (e.target && e.target.id==='sortAll_j'){ render(); }
  });

  // aktiváláskor első betöltés
  try{
    await loadOnce();
    render();
  }catch(err){
    console.error(err);
    root.innerHTML = `<div style="padding:12px;border:1px solid #eee;border-radius:10px">
      Hiba a Játéksziget feed betöltésekor. Ellenőrizd az URL-t.
    </div>`;
  }
}
