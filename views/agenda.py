import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core import storage, theme, docs

cart = storage.carregar()
theme.hero("📅", "Agenda de disputas",
           "Sessões públicas e prazos dos editais do funil, vencimento de certidões e previsões do PCA. "
           "Exporte para Google Agenda/Outlook com lembrete automático 1 dia antes.")

eventos = []
for s in cart["salvos"].values():
    fim = pd.to_datetime(s.get("fim_propostas"), errors="coerce")
    if pd.notna(fim):
        cor = storage.CORES_FUNIL.get(s.get("status", "Triagem"), theme.INDIGO)
        eventos.append({"title": f"⚖ {(s.get('objeto') or '')[:60]}", "start": fim.isoformat(), "color": cor,
                        "url": s.get("link_pncp") or "", "extendedProps": {
                            "tipo": "Disputa", "orgao": s.get("orgao", ""), "status": s.get("status", "Triagem")}})
for c in cart.get("certidoes", []):
    v = pd.to_datetime(c.get("validade"), errors="coerce")
    if pd.notna(v):
        eventos.append({"title": f"🛡 Vence: {c['documento'][:40]}", "start": v.date().isoformat(), "allDay": True,
                        "color": theme.AMBAR, "extendedProps": {"tipo": "Certidão", "orgao": c.get("orgao", "")}})

c1, c2 = st.columns([3, 1])
c2.metric("Eventos", len(eventos))
if eventos:
    ics_evts = [{"titulo": e["title"], "inicio": e["start"], "url": e.get("url"),
                 "descricao": f"{e['extendedProps'].get('tipo')} – {e['extendedProps'].get('orgao', '')}"} for e in eventos]
    c2.download_button("📥 Exportar .ics", docs.ics(ics_evts), "radarlic_agenda.ics", "text/calendar",
                       use_container_width=True, help="Importe no Google Agenda, Outlook ou celular.")
else:
    st.info("Nenhum evento. Salve editais no funil e informe a validade das certidões.")

components.html(f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@fullcalendar/core@6.1.15/locales/pt-br.global.min.js"></script>
<style>
 body{{margin:0;font-family:Inter,sans-serif}}
 #cal{{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:14px;box-shadow:0 6px 18px #0f172a08}}
 .fc .fc-toolbar-title{{font-size:1.15rem;font-weight:700;color:#0f172a;text-transform:capitalize}}
 .fc .fc-button-primary{{background:#4f46e5;border:0;border-radius:9px;text-transform:capitalize}}
 .fc .fc-button-primary:not(:disabled).fc-button-active{{background:#312e81}}
 .fc-event{{border:0;border-radius:6px;padding:1px 4px;font-size:12px;cursor:pointer}}
 .fc .fc-daygrid-day.fc-day-today{{background:#eef2ff}}
 .fc-theme-standard td,.fc-theme-standard th{{border-color:#eef2f7}}
 #tip{{position:fixed;display:none;background:#0f172a;color:#fff;padding:8px 10px;border-radius:8px;font-size:12px;max-width:320px;z-index:9;pointer-events:none}}
</style>
<div id="cal"></div><div id="tip"></div>
<script>
const tip=document.getElementById('tip');
const cal=new FullCalendar.Calendar(document.getElementById('cal'),{{
  locale:'pt-br', initialView:'dayGridMonth', height:640, nowIndicator:true, dayMaxEvents:3,
  headerToolbar:{{left:'prev,next today',center:'title',right:'dayGridMonth,timeGridWeek,listMonth'}},
  events:{json.dumps(eventos, ensure_ascii=False)},
  eventClick:(i)=>{{ if(i.event.url){{ i.jsEvent.preventDefault(); window.open(i.event.url,'_blank'); }} }},
  eventMouseEnter:(i)=>{{ const p=i.event.extendedProps; tip.innerHTML='<b>'+i.event.title+'</b><br>'+(p.orgao||'')+
     (p.status?'<br>Status: '+p.status:'')+'<br>'+i.event.start.toLocaleString('pt-BR');
     tip.style.display='block'; tip.style.left=(i.jsEvent.clientX+12)+'px'; tip.style.top=(i.jsEvent.clientY+12)+'px'; }},
  eventMouseLeave:()=>{{ tip.style.display='none'; }},
}});
cal.render();
</script>""", height=700)
