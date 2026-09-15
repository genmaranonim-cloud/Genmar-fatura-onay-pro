function guvenliMetin(v) {
    return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function kisaltma(ad) {
    const p = String(ad || '?').trim().split(/\s+/);
    return (p.length > 1 ? p[0][0] + p[p.length - 1][0] : p[0][0]).toUpperCase();
}

async function veriYukle() {
    try {
        const [kullanicilar, departmanlar, projeler] = await Promise.all([
            apiFetch('/api/yonetim/kullanicilar'),
            apiFetch('/api/yonetim/departmanlar'),
            apiFetch('/api/yonetim/projeler')
        ]);
        renderKullanicilar(Array.isArray(kullanicilar) ? kullanicilar : []);
        renderDepartmanlar(Array.isArray(departmanlar) ? departmanlar : []);
        renderProjeler(Array.isArray(projeler) ? projeler : []);
        deptDropdownDoldur(Array.isArray(departmanlar) ? departmanlar : []);
    } catch (e) {
        toast('Yönetim bilgileri yüklenemedi', 'error');
    }
}

function renderKullanicilar(liste) {
    document.getElementById('kullaniciSayisi').textContent = `${liste.length} kullanıcı`;
    const el = document.getElementById('kullaniciListe');
    if (!liste.length) { el.innerHTML = '<div class="bos-liste">Henüz kullanıcı yok</div>'; return; }
    el.innerHTML = [...liste].sort((a,b) => a.ad_soyad.localeCompare(b.ad_soyad, 'tr')).map(k => `
      <div class="liste-item">
        <div class="avatar">${kisaltma(k.ad_soyad)}</div>
        <div class="item-info"><div class="item-ad">${guvenliMetin(k.ad_soyad)}</div>
        <div class="item-alt">${guvenliMetin(k.departman_ad || '—')}${k.email ? ' · '+guvenliMetin(k.email) : ''}${k.atanan_faturalari_gizle ? ' · 🔒 Özel faturalar' : ''}</div></div>
        <span class="dept-badge">${guvenliMetin(k.departman_kod || '?')}</span>
        <div class="item-actions"><button class="btn btn-ghost btn-sm kul-duzenle" data-id="${k.id}">✎</button>
        <button class="btn btn-red btn-sm kul-sil" data-id="${k.id}" data-ad="${guvenliMetin(k.ad_soyad)}">✕</button></div>
      </div>`).join('');
    el.querySelectorAll('.kul-duzenle').forEach(b => b.onclick = () => {
        const k = liste.find(x => x.id === Number(b.dataset.id));
        kullaniciDuzenle(k.id, k.ad_soyad, k.departman_id, k.email, k.atanan_faturalari_gizle, k.gizlilik_duzenlenebilir);
    });
    el.querySelectorAll('.kul-sil').forEach(b => b.onclick = () => kullaniciSil(Number(b.dataset.id), b.dataset.ad));
}

function deptDropdownDoldur(liste) {
    const sel = document.getElementById('yeniKullaniciDept');
    sel.innerHTML = '<option value="">Seçiniz...</option>' + liste.map(d =>
        `<option value="${d.id}">${guvenliMetin(d.kod)} — ${guvenliMetin(d.ad)}</option>`).join('');
}
async function kullaniciEkle() {
    const ad=document.getElementById('yeniKullaniciAd').value.trim(), email=document.getElementById('yeniKullaniciEmail').value.trim();
    const departman_id=document.getElementById('yeniKullaniciDept').value || null;
    if(!ad) return toast('Ad Soyad girin','error');
    const r=await apiFetch('/api/yonetim/kullanici-ekle','POST',{ad_soyad:ad,email,departman_id});
    if(r.basarili){ toast('Kullanıcı eklendi','success'); document.getElementById('yeniKullaniciAd').value=''; document.getElementById('yeniKullaniciEmail').value=''; veriYukle(); }
    else toast(r.hata||'Hata','error');
}
function kullaniciDuzenle(id,ad,deptId,email,gizliAtama,gizlilikDuzenlenebilir){
    document.getElementById('duzenleKulId').value=id; document.getElementById('duzenleKulAd').value=ad;
    document.getElementById('duzenleKulEmail').value=email||'';
    document.getElementById('duzenleKulGizliAtama').checked=Boolean(gizliAtama);
    document.getElementById('gizliAtamaAlani').style.display=gizlilikDuzenlenebilir?'flex':'none';
    apiFetch('/api/yonetim/departmanlar').then(l=>{ document.getElementById('duzenleKulDept').innerHTML='<option value="">Seçiniz...</option>'+l.map(d=>`<option value="${d.id}" ${d.id==deptId?'selected':''}>${guvenliMetin(d.kod)} — ${guvenliMetin(d.ad)}</option>`).join(''); });
    document.getElementById('kulDuzenleModal').classList.add('open');
}
function kulDuzenleKapat(){ document.getElementById('kulDuzenleModal').classList.remove('open'); }
async function kullaniciGuncelle(){
    const id=document.getElementById('duzenleKulId').value, ad=document.getElementById('duzenleKulAd').value.trim();
    const email=document.getElementById('duzenleKulEmail').value.trim(), departman_id=document.getElementById('duzenleKulDept').value||null;
    const atanan_faturalari_gizle=document.getElementById('duzenleKulGizliAtama').checked;
    const r=await apiFetch(`/api/yonetim/kullanici-guncelle/${id}`,'POST',{ad_soyad:ad,email,departman_id,atanan_faturalari_gizle});
    if(r.basarili){toast('Güncellendi','success');kulDuzenleKapat();veriYukle();}else toast(r.hata||'Hata','error');
}
async function kullaniciSil(id,ad){ if(confirm(`"${ad}" silinsin mi?`)){const r=await apiFetch(`/api/yonetim/kullanici-sil/${id}`,'DELETE');if(r.basarili)veriYukle();else toast(r.hata||'Hata','error');} }

function renderDepartmanlar(liste){
    const el=document.getElementById('departmanListe');
    if(!liste.length){el.innerHTML='<div class="bos-liste">Henüz departman yok</div>';return;}
    el.innerHTML=[...liste].sort((a,b)=>a.ad.localeCompare(b.ad,'tr')).map(d=>`<div class="liste-item"><span class="dept-badge">${guvenliMetin(d.kod)}</span><div class="item-info"><div class="item-ad">${guvenliMetin(d.ad)}</div></div><button class="btn btn-ghost btn-sm dept-edit" data-id="${d.id}">✎</button><button class="btn btn-red btn-sm dept-del" data-id="${d.id}">✕</button></div>`).join('');
    el.querySelectorAll('.dept-edit').forEach(b=>b.onclick=()=>{const d=liste.find(x=>x.id===Number(b.dataset.id));departmanDuzenle(d.id,d.kod,d.ad);});
    el.querySelectorAll('.dept-del').forEach(b=>b.onclick=()=>{const d=liste.find(x=>x.id===Number(b.dataset.id));departmanSil(d.id,d.kod);});
}
async function departmanEkle(){const kod=document.getElementById('yeniDeptKod').value.trim().toUpperCase(),ad=document.getElementById('yeniDeptAd').value.trim();const r=await apiFetch('/api/yonetim/departman-ekle','POST',{kod,ad});if(r.basarili){toast('Departman eklendi','success');veriYukle();}else toast(r.hata||'Hata','error');}
function departmanDuzenle(id,kod,ad){document.getElementById('dunzenleDeptId').value=id;document.getElementById('dunzenleDeptKod').value=kod;document.getElementById('dunzenleDeptAd').value=ad;document.getElementById('deptDuzenleModal').classList.add('open');}
function deptDuzenleKapat(){document.getElementById('deptDuzenleModal').classList.remove('open');}
async function departmanGuncelle(){const id=document.getElementById('dunzenleDeptId').value,kod=document.getElementById('dunzenleDeptKod').value.trim().toUpperCase(),ad=document.getElementById('dunzenleDeptAd').value.trim();const r=await apiFetch(`/api/yonetim/departman-guncelle/${id}`,'POST',{kod,ad});if(r.basarili){deptDuzenleKapat();veriYukle();}else toast(r.hata||'Hata','error');}
async function departmanSil(id,kod){if(confirm(`"${kod}" departmanı silinsin mi?`)){const r=await apiFetch(`/api/yonetim/departman-sil/${id}`,'DELETE');if(r.basarili)veriYukle();else toast(r.hata||'Hata','error');}}

function renderProjeler(liste){
    const el=document.getElementById('projeAgaci');
    if(!liste.length){el.innerHTML='<div class="bos-liste">Henüz proje yok</div>';return;}
    el.innerHTML=liste.map(p=>{
      const gruplar={}; p.alt_projeler.forEach(a=>(gruplar[a.kod]??=[]).push(a));
      const altHtml=Object.entries(gruplar).map(([kod,kirilimlar])=>`<div style="border:1px solid var(--border);border-radius:7px;overflow:hidden"><div style="padding:7px 10px;background:var(--surface2);font-weight:700;color:var(--accent2)">${guvenliMetin(kod)} <span style="font-weight:400;color:var(--text2)">(${kirilimlar.length} kırılım)</span></div>${kirilimlar.map(a=>`<div class="alt-proje-item"><div class="item-info">${guvenliMetin(a.ad)}</div><button class="btn btn-ghost btn-sm alt-toggle" data-id="${a.id}">${a.aktif?'Pasif':'Aktif'}</button>${p.silinebilir?`<button class="btn btn-red btn-sm alt-delete" data-id="${a.id}">Sil</button>`:''}</div>`).join('')}</div>`).join('');
      return `<div class="ana-proje-item"><div class="ana-proje-baslik" data-toggle="${p.id}"><span class="ana-proje-ikon" id="ikon-${p.id}">▶</span><span class="dept-badge">${guvenliMetin(p.kod)}</span><div class="item-info"><div class="item-ad">${guvenliMetin(p.ad)}</div><div class="item-alt">${p.alt_projeler.length} alt kırılım</div></div><button class="btn btn-ghost btn-sm alt-add" data-id="${p.id}">+ Alt</button><button class="btn btn-ghost btn-sm ana-toggle" data-id="${p.id}">${p.aktif?'Pasif':'Aktif'}</button>${p.silinebilir?`<button class="btn btn-red btn-sm ana-delete" data-id="${p.id}">Sil</button>`:''}</div><div class="alt-projeler-listesi" id="alt-${p.id}">${altHtml}<div class="alt-ekle-satir alt-add" data-id="${p.id}"><span>+ Alt kırılım ekle</span></div></div></div>`;
    }).join('');
    el.querySelectorAll('[data-toggle]').forEach(x=>x.onclick=()=>toggleAlt(Number(x.dataset.toggle)));
    el.querySelectorAll('.alt-add').forEach(b=>b.onclick=e=>{e.stopPropagation();const p=liste.find(x=>x.id===Number(b.dataset.id));altModalAc(p.id,`${p.kod} — ${p.ad}`);});
    el.querySelectorAll('.ana-toggle').forEach(b=>b.onclick=e=>{e.stopPropagation();const p=liste.find(x=>x.id===Number(b.dataset.id));anaProjeToggle(p.id,p.aktif);});
    el.querySelectorAll('.alt-toggle').forEach(b=>b.onclick=()=>{const a=liste.flatMap(p=>p.alt_projeler).find(x=>x.id===Number(b.dataset.id));altProjeToggle(a.id,a.aktif);});
    el.querySelectorAll('.ana-delete').forEach(b=>b.onclick=e=>{e.stopPropagation();anaProjeSil(Number(b.dataset.id));});
    el.querySelectorAll('.alt-delete').forEach(b=>b.onclick=()=>altProjeSil(Number(b.dataset.id)));
}
function toggleAlt(id){document.getElementById(`alt-${id}`).classList.toggle('acik');document.getElementById(`ikon-${id}`).classList.toggle('acik');}
async function anaProjeEkle(){const kod=document.getElementById('yeniAnaKod').value.trim().toUpperCase(),ad=document.getElementById('yeniAnaAd').value.trim();const r=await apiFetch('/api/yonetim/ana-proje-ekle','POST',{kod,ad});if(r.basarili){toast('Ana proje eklendi','success');veriYukle();}else toast(r.hata||'Hata','error');}
async function anaProjeToggle(id,aktif){const r=await apiFetch(`/api/yonetim/ana-proje-toggle/${id}`,'POST',{aktif:!aktif});if(r.basarili)veriYukle();else toast(r.hata||'Hata','error');}
function altModalAc(id,ad){document.getElementById('altAnaProjeId').value=id;document.getElementById('altModalAnaAd').textContent=ad;document.getElementById('altKod').value='';document.getElementById('altAd').value='';document.getElementById('altProjeModal').classList.add('open');}
function altModalKapat(){document.getElementById('altProjeModal').classList.remove('open');}
async function altProjeEkle(){const ana_proje_id=Number(document.getElementById('altAnaProjeId').value),kod=document.getElementById('altKod').value.trim().toUpperCase(),ad=document.getElementById('altAd').value.trim();const r=await apiFetch('/api/yonetim/alt-proje-ekle','POST',{ana_proje_id,kod,ad});if(r.basarili){altModalKapat();veriYukle();}else toast(r.hata||'Hata','error');}
async function altProjeToggle(id,aktif){const r=await apiFetch(`/api/yonetim/alt-proje-toggle/${id}`,'POST',{aktif:!aktif});if(r.basarili)veriYukle();else toast(r.hata||'Hata','error');}
async function anaProjeSil(id){if(!confirm('Bu ana proje silinsin mi?'))return;const r=await apiFetch(`/api/yonetim/ana-proje-sil/${id}`,'DELETE');if(r.basarili){toast('Ana proje silindi','success');veriYukle();}else toast(r.hata||'Silinemedi','error');}
async function altProjeSil(id){if(!confirm('Bu alt kırılım silinsin mi?'))return;const r=await apiFetch(`/api/yonetim/alt-proje-sil/${id}`,'DELETE');if(r.basarili){toast('Alt kırılım silindi','success');veriYukle();}else toast(r.hata||'Silinemedi','error');}

async function excelYukle(dosya){if(!dosya)return;const form=new FormData();form.append('dosya',dosya);const r=await fetch('/api/proje-excel-import',{method:'POST',body:form});const d=await r.json();if(d.basarili){toast(`${d.ana_eklenen} ana, ${d.alt_eklenen} alt proje eklendi`,'success');veriYukle();}else toast(d.hata||'Excel yüklenemedi','error');}
async function kulExcelYukle(dosya){if(!dosya)return;const form=new FormData();form.append('dosya',dosya);const r=await fetch('/api/kullanici-excel-import',{method:'POST',body:form});const d=await r.json();if(d.basarili){toast('Excel başarıyla işlendi','success');veriYukle();}else toast(d.hata||'Excel yüklenemedi','error');}

['kulDuzenleModal','deptDuzenleModal','altProjeModal'].forEach(id=>document.getElementById(id)?.addEventListener('click',e=>{if(e.target===e.currentTarget)e.currentTarget.classList.remove('open');}));
veriYukle();
