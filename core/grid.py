"""Tabela moderna (AG Grid em JavaScript) com formatação brasileira, selos, barras de score,
contagem regressiva de prazo, busca, filtros, paginação e edição em linha.

Uso:
    linha, dados = grid(df, "chave", {"score": "score", "valor": "brl", "objeto": "longo",
                                      "fase": {"tipo": "badge", "cores": {"Aberto": "#059669"}}})
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from st_aggrid.shared import StAggridTheme

TEMA = StAggridTheme(base="quartz").withParams(
    accentColor="#4f46e5", fontFamily={"googleFont": "Inter"}, fontSize=13,
    headerBackgroundColor="#f8fafc", headerTextColor="#475569", headerFontWeight=600,
    rowHoverColor="#eef2ff", selectedRowBackgroundColor="#e0e7ff", borderColor="#e8edf3",
    oddRowBackgroundColor="#fbfcfe", wrapperBorderRadius=14, rowHeight=44, headerHeight=44,
    spacing=7, browserColorScheme="light",
)

PT = {
    "page": "Página", "of": "de", "to": "a", "more": "mais", "next": "Próxima", "last": "Última",
    "first": "Primeira", "previous": "Anterior", "pageSizeSelectorLabel": "Linhas:",
    "noRowsToShow": "Nenhum registro", "loadingOoo": "Carregando…", "searchOoo": "Buscar…",
    "selectAll": "(Todos)", "filterOoo": "Filtrar…", "equals": "Igual a", "notEqual": "Diferente de",
    "contains": "Contém", "notContains": "Não contém", "startsWith": "Começa com", "endsWith": "Termina com",
    "lessThan": "Menor que", "greaterThan": "Maior que", "lessThanOrEqual": "Menor ou igual",
    "greaterThanOrEqual": "Maior ou igual", "inRange": "Entre", "blank": "Vazio", "notBlank": "Preenchido",
    "andCondition": "E", "orCondition": "OU", "applyFilter": "Aplicar", "resetFilter": "Limpar",
    "clearFilter": "Limpar", "before": "Antes", "after": "Depois",
}

# ------------------------------------------------------------------ formatadores JS
_BRL = JsCode("""function(p){ if(p.value==null||p.value==='') return '—';
 return new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(p.value); }""")
_NUM = JsCode("""function(p){ if(p.value==null||p.value==='') return '—';
 return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(p.value); }""")
_PCT = JsCode("""function(p){ if(p.value==null||p.value==='') return '—';
 return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:1}).format(p.value)+'%'; }""")
_DATA = JsCode("""function(p){ if(!p.value) return '—'; const d=new Date(p.value);
 return isNaN(d)?p.value:d.toLocaleDateString('pt-BR'); }""")
_DATAHORA = JsCode("""function(p){ if(!p.value) return '—'; const d=new Date(p.value);
 return isNaN(d)?p.value:d.toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}); }""")


def _renderer(corpo_js: str) -> JsCode:
    """Cria um cellRenderer (classe) a partir de uma função JS `html(p)` que devolve HTML."""
    return JsCode(f"""class R {{
  init(p){{ const html=(function(p){{ {corpo_js} }})(p); this.e=document.createElement('div');
    this.e.style.cssText='display:flex;align-items:center;height:100%;gap:6px;line-height:1.5;'; this.e.innerHTML=html; }}
  getGui(){{ return this.e; }} refresh(){{ return false; }} }}""")


_SCORE = _renderer("""
 const v=Math.round(p.value||0); const c=v>=70?'#059669':v>=50?'#d97706':'#e11d48';
 return `<div style="flex:1;height:8px;background:#eef2f7;border-radius:99px;overflow:hidden">
   <div style="width:${v}%;height:100%;background:linear-gradient(90deg,${c}aa,${c});border-radius:99px"></div></div>
   <b style="color:${c};min-width:26px;text-align:right">${v}</b>`;""")

_PRAZO = _renderer("""
 if(!p.value) return '<span style="color:#94a3b8">—</span>';
 const d=new Date(p.value), ms=d-new Date(), h=ms/36e5;
 const quando=d.toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
 let txt,c;
 if(ms<0){txt='encerrado';c='#94a3b8';}
 else if(h<24){txt=Math.floor(h)+'h '+Math.floor((h%1)*60)+'min';c='#e11d48';}
 else {const dd=Math.floor(h/24);txt=dd+'d '+Math.floor(h%24)+'h';c=dd<3?'#d97706':'#059669';}
 return `<span style="background:${c}18;color:${c};display:inline-block;line-height:1.5;padding:1px 9px;border-radius:99px;font-weight:600;font-size:12px;white-space:nowrap">⏱ ${txt}</span>
   <span style="color:#64748b;font-size:12px">${quando}</span>`;""")

_LINK = _renderer("""
 if(!p.value) return '';
 return `<a href="${p.value}" target="_blank" rel="noopener" style="color:#4f46e5;font-weight:600;text-decoration:none">abrir ↗</a>`;""")

_DIAS = _renderer("""
 if(p.value==null||p.value==='') return '<span style="color:#94a3b8">sem data</span>';
 const v=Math.round(p.value); let c,t;
 if(v<0){c='#e11d48';t='vencida há '+(-v)+'d';} else if(v<=15){c='#d97706';t=v+' dias';} else {c='#059669';t=v+' dias';}
 return `<span style="background:${c}18;color:${c};display:inline-block;line-height:1.5;padding:1px 9px;border-radius:99px;font-weight:600;font-size:12px;white-space:nowrap">${t}</span>`;""")


def _badge(cores: dict) -> JsCode:
    import json
    return _renderer(f"""
 const C={json.dumps(cores)}; if(p.value==null||p.value==='') return '';
 const c=C[p.value]||'#64748b';
 return `<span style="background:${{c}}1a;color:${{c}};display:inline-block;line-height:1.5;padding:1px 10px;border-radius:99px;font-weight:600;font-size:12px;white-space:nowrap">${{p.value}}</span>`;""")


def _iso(s: pd.Series) -> pd.Series:
    s = pd.to_datetime(s, errors="coerce")
    return s.map(lambda x: x.isoformat() if pd.notna(x) else None)


def grid(df: pd.DataFrame, key: str, colunas: dict | None = None, *, altura: int | None = None,
         selecao: bool = True, pagina: int = 20, editavel: bool = False, busca: bool = True):
    """Mostra o DataFrame em AG Grid. Retorna (linha_selecionada_original | None, dados_editados)."""
    if df is None or df.empty:
        st.info("Nenhum registro para mostrar.")
        return None, df
    colunas = colunas or {c: "texto" for c in df.columns}
    colunas = {c: s for c, s in colunas.items() if c in df.columns}
    base = df.reset_index(drop=True)
    vis = base[list(colunas)].copy()
    vis["_rid"] = range(len(vis))

    gb = GridOptionsBuilder.from_dataframe(vis)
    gb.configure_default_column(resizable=True, sortable=True, filter=True, minWidth=80, width=150,
                                wrapHeaderText=True, autoHeaderHeight=True, editable=False)
    gb.configure_column("_rid", hide=True)
    for col, spec in colunas.items():
        spec = {"tipo": spec} if isinstance(spec, str) else dict(spec)
        tipo = spec.get("tipo", "texto")
        opts = {"headerName": spec.get("titulo", col)}
        if "largura" in spec:
            opts["width"] = spec["largura"]
        if spec.get("fixa"):
            opts["pinned"] = "left"
        if spec.get("editavel"):
            opts["editable"] = True
            opts["cellStyle"] = {"backgroundColor": "#fffbeb"}
        if tipo == "brl":
            vis[col] = pd.to_numeric(vis[col], errors="coerce")
            opts.update(valueFormatter=_BRL, type=["numericColumn"], filter="agNumberColumnFilter")
        elif tipo == "num":
            vis[col] = pd.to_numeric(vis[col], errors="coerce")
            opts.update(valueFormatter=_NUM, type=["numericColumn"], filter="agNumberColumnFilter")
        elif tipo == "pct":
            vis[col] = pd.to_numeric(vis[col], errors="coerce")
            opts.update(valueFormatter=_PCT, type=["numericColumn"], filter="agNumberColumnFilter")
        elif tipo in ("data", "datahora", "prazo"):
            vis[col] = _iso(vis[col])
            if tipo == "prazo":
                opts.update(cellRenderer=_PRAZO, minWidth=200, cellStyle={"display": "flex", "alignItems": "center"})
            else:
                opts.update(valueFormatter=_DATA if tipo == "data" else _DATAHORA)
            if spec.get("editavel"):
                opts.update(cellEditor="agDateStringCellEditor", cellDataType="dateString")
                vis[col] = vis[col].map(lambda x: x[:10] if isinstance(x, str) else None)
        elif tipo == "score":
            vis[col] = pd.to_numeric(vis[col], errors="coerce")
            opts.update(cellRenderer=_SCORE, width=spec.get("largura", 150), filter="agNumberColumnFilter", cellStyle={"display": "flex", "alignItems": "center"})
        elif tipo == "badge":
            opts.update(cellRenderer=_badge(spec.get("cores", {})), cellStyle={"display": "flex", "alignItems": "center"})
        elif tipo == "link":
            opts.update(cellRenderer=_LINK, width=spec.get("largura", 95), filter=False, sortable=False, cellStyle={"display": "flex", "alignItems": "center"})
        elif tipo == "dias":
            vis[col] = pd.to_numeric(vis[col], errors="coerce")
            opts.update(cellRenderer=_DIAS, filter="agNumberColumnFilter", cellStyle={"display": "flex", "alignItems": "center"})
        elif tipo == "wrap":
            opts.update(flex=spec.get("flex", 1), minWidth=spec.get("min", 260), wrapText=True, autoHeight=True,
                        cellStyle={"lineHeight": "1.45", "paddingTop": "8px", "paddingBottom": "8px",
                                   "whiteSpace": "pre-line"})
        elif tipo == "longo":
            opts.update(flex=spec.get("flex", 2), minWidth=spec.get("min", 280), tooltipField=col)
        elif tipo == "select":
            opts.update(cellEditor="agSelectCellEditor", cellEditorParams={"values": spec["opcoes"]},
                        editable=True, cellRenderer=_badge(spec.get("cores", {})),
                        cellStyle={"cursor": "pointer"})
        gb.configure_column(col, **opts)

    if selecao:
        gb.configure_selection("single", use_checkbox=False)
    gb.configure_grid_options(
        pagination=len(vis) > pagina, paginationPageSize=pagina, paginationPageSizeSelector=[10, 20, 50, 100],
        animateRows=True, enableCellTextSelection=True, ensureDomOrder=True, tooltipShowDelay=250,
        localeText=PT, loadThemeGoogleFonts=True, singleClickEdit=True, stopEditingWhenCellsLoseFocus=True,
        suppressCellFocus=not editavel, rowHeight=44,
    )
    if altura is None:
        altura = min(620, 100 + 44 * min(len(vis), pagina) + (48 if len(vis) > pagina else 0))
    opcoes = gb.build()
    opcoes.pop("autoSizeStrategy", None)  # não espremer colunas: usa larguras definidas + rolagem horizontal
    resp = AgGrid(
        vis, gridOptions=opcoes, theme=TEMA, allow_unsafe_jscode=True, height=altura, key=key,
        update_on=(["selectionChanged"] if selecao else []) + (["cellValueChanged"] if editavel else []),
        show_search=busca, show_toolbar=busca,
        data_return_mode="AS_INPUT" if editavel else "FILTERED_AND_SORTED",
    )
    linha = None
    sel = resp.selected_rows
    if sel is not None and len(sel):
        rid = int(sel.iloc[0]["_rid"]) if isinstance(sel, pd.DataFrame) else int(sel[0]["_rid"])
        linha = base.iloc[rid]
    dados = resp.data if editavel and resp.data is not None else vis
    if isinstance(dados, pd.DataFrame) and "_rid" in dados:
        # índice = posição da linha no DataFrame recebido (base.iloc[i])
        dados = dados.assign(_rid=dados["_rid"].astype(int)).set_index("_rid").sort_index()
        dados.index.name = None
    return linha, dados
