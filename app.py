"""
생활화학제품 위반정보 분석 대시보드 (Streamlit v5)

- 대분류(품목군) → 중분류(품목) 계층 구조를 Treemap / Sunburst / Sankey 로 시각화
- 실행:  python -m streamlit run app.py
- 데이터: 같은 폴더의 analysis_long.csv (없으면 데모 데이터)
- 필요 라이브러리: streamlit, pandas, numpy, plotly  (requirements.txt)
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------ 설정
COL = {  # 오른쪽 = 실제 CSV 컬럼명 (다르면 여기만 수정)
    "id": "prdt_mstr_no", "item": "품목", "group": "품목군", "vtype": "위반유형",
    "subst": "위반물질", "action": "조치유형", "year": "조치연도", "conf": "분류신뢰도",
}
OPTIONAL = ["group", "conf"]
T_SAFE, T_CONF, T_LABEL, T_UNK = "안전기준 위반", "안전기준 적합확인 위반", "표시기준 위반", "미분류(검토필요)"
TYPE_ORDER = [T_SAFE, T_CONF, T_LABEL]
NO_SUBST, UNK_SUBST = "해당없음", "물질 미특정"

# 색상 (초록 계열 + 신뢰감 있는 청록·슬레이트)
INK, MUTED, LINE, BG = "#14261F", "#5E7068", "#D9E5DE", "#F3F7F4"
GREEN, GREEN_DARK, GREEN_SOFT = "#1E6B52", "#134536", "#E4EFE9"
TYPE_COLOR = {T_SAFE: "#B5473C", T_CONF: "#B7791F", T_LABEL: "#2F6F8F", T_UNK: "#8C9A94"}
GROUP_PALETTE = ["#1E6B52", "#2D7F7A", "#3E6C8E", "#5E7F2E", "#8C6B2A", "#2A5F4A", "#4A8A6A",
                 "#35657A", "#6E8B3D", "#9A7B35", "#3B7C94", "#557A5C", "#7A6A4F"]
SEQ = ["#134536", "#1E6B52", "#5FA58A", "#A9D0BF", "#B7791F", "#8C9A94"]
FONT = "Noto Sans KR, Malgun Gothic, AppleGothic, sans-serif"

st.set_page_config(page_title="생활화학제품 위반정보 대시보드", page_icon="🌿", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Noto+Serif+KR:wght@600;700&display=swap');
html, body, .stApp, .stMarkdown, p, label, button, input, textarea {{ font-family: 'Noto Sans KR', sans-serif; }}
.stApp {{ background: {BG}; color: {INK}; color-scheme: light; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 1240px; padding-top: 1.2rem; padding-bottom: 3rem; }}
h1, h2, h3, h4 {{ color: {INK}; letter-spacing: -0.01em; }}
h4 {{ font-family: 'Noto Serif KR', serif; font-weight: 700; font-size: 1.12rem; margin: .1rem 0 .3rem 0; }}

/* 사이드바 */
section[data-testid="stSidebar"] {{ background: #E6EFEA; border-right: 1px solid {LINE}; }}
section[data-testid="stSidebar"] h3 {{ font-family: 'Noto Serif KR', serif; color: {GREEN_DARK}; }}
span[data-baseweb="tag"] {{ background-color: {GREEN} !important; color: #fff !important; }}
span[data-baseweb="tag"] span, span[data-baseweb="tag"] svg {{ color: #fff !important; fill: #fff !important; }}

/* 상단 소개 영역 */
.hero {{ background: linear-gradient(135deg, {GREEN_DARK} 0%, {GREEN} 100%); color: #fff;
         border-radius: 18px; padding: 28px 34px 24px 34px; margin-bottom: 18px; }}
.hero .src {{ color: #BFE0D1; font-size: .92rem; margin-bottom: 6px; }}
.hero h1 {{ font-family: 'Noto Serif KR', serif; color: #fff; font-weight: 700; font-size: 2.05rem;
            margin: 0 0 6px 0; line-height: 1.3; }}
.hero .desc {{ color: #DDEFE6; font-size: 1rem; margin-bottom: 16px; }}
.chip {{ display: inline-block; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28);
         color: #fff; border-radius: 999px; padding: 4px 14px; font-size: .86rem; margin: 0 8px 4px 0; }}

/* 요약 문장 / 숫자 카드 */
.brief {{ background: {GREEN_SOFT}; border-radius: 14px; padding: 16px 22px; line-height: 1.9; margin-bottom: 14px; }}
.brief b {{ color: {GREEN_DARK}; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-bottom: 18px; }}
.kpi {{ background: #fff; border: 1px solid {LINE}; border-radius: 14px; padding: 16px 20px; }}
.kpi .k {{ color: {MUTED}; font-size: .9rem; }}
.kpi .v {{ font-family: 'Noto Serif KR', serif; font-weight: 700; font-size: 1.9rem; color: {GREEN_DARK}; line-height: 1.35; }}
.kpi .v small {{ font-family: 'Noto Sans KR', sans-serif; font-size: .95rem; color: {MUTED}; margin-left: 3px; font-weight: 400; }}
.note {{ color: {MUTED}; font-size: .86rem; }}

/* 그래프 카드 */
[data-testid="stVerticalBlockBorderWrapper"] {{ background: #fff; border: 1px solid {LINE} !important; border-radius: 14px; }}

/* 탭 */
button[data-baseweb="tab"] p {{ font-weight: 600; font-size: 1rem; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color: {GREEN_DARK}; }}
div[data-baseweb="tab-highlight"] {{ background-color: {GREEN} !important; }}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ 데이터
@st.cache_data
def load_data():
    path = Path(__file__).parent / "analysis_long.csv"
    if path.exists():
        return pd.read_csv(path, encoding="utf-8-sig"), False
    rng = np.random.default_rng(0)  # 데모 데이터
    tree = {"방향·탈취제품": ["방향제", "탈취제"], "세정제품": ["세정제", "합성세제"], "코팅제품": ["코팅제", "광택코팅제"]}
    subs = ["MIT", "CMIT", "폼알데하이드", "니켈", "벤젠", "톨루엔"]
    rows = []
    for pid in range(1, 301):
        grp = rng.choice(list(tree))
        it, yr = rng.choice(tree[grp]), int(rng.integers(2018, 2026))
        for t in rng.choice(TYPE_ORDER, size=int(rng.integers(1, 3)), replace=False):
            rows.append([pid, it, grp, t, rng.choice(subs) if t == T_SAFE else NO_SUBST,
                         rng.choice(["판매금지·회수명령", "회수명령"]), yr, "확실"])
    return pd.DataFrame(rows, columns=[COL[k] for k in COL]), True


raw, is_demo = load_data()
need = [v for k, v in COL.items() if k not in OPTIONAL]
miss = [c for c in need if c not in raw.columns]
if miss:
    st.error(f"CSV에 없는 컬럼: {miss}\n현재 컬럼: {list(raw.columns)}")
    st.stop()

ren = {v: k for k, v in COL.items() if v in raw.columns}
df = raw.rename(columns=ren)[list(ren.values())].copy()
if "group" not in df:
    df["group"] = "전체"
if "conf" not in df:
    df["conf"] = "확실"
df["subst"] = df["subst"].fillna(NO_SUBST)
df["year"] = pd.to_numeric(df["year"], errors="coerce")
n_year_missing = df.loc[df["year"].isna(), "id"].nunique()

# 대분류별 고정 색 (제품이 많은 순서대로 색 배정)
g_order = df.groupby("group")["id"].nunique().sort_values(ascending=False).index.tolist()
GCOL = {g: GROUP_PALETTE[i % len(GROUP_PALETTE)] for i, g in enumerate(g_order)}

# ------------------------------------------------------------------ 사이드바
st.sidebar.markdown("### 조건 설정")
sel_groups = st.sidebar.multiselect("대분류 (비우면 전체)", g_order, default=[])
pool = df[df["group"].isin(sel_groups)] if sel_groups else df
items_pool = sorted(pool["item"].unique())
sel_items = st.sidebar.multiselect("중분류 · 품목 (비우면 전체)", items_pool, default=[])

unit = st.sidebar.radio("비교 단위", ["중분류 (품목)", "대분류"], help="‘품목 비교’·‘위반물질’ 탭의 그래프 단위입니다.")
df["item_sel"] = df["item"] if unit.startswith("중분류") else df["group"]
top_max = max(4, min(20, df["item_sel"].nunique()))
top_k = st.sidebar.slider("그래프에 보여줄 개수 (상위 N)", 3, top_max, min(10, top_max))

yrs = df["year"].dropna()
y0, y1 = int(yrs.min()), int(yrs.max())
sel_years = st.sidebar.slider("조치연도", y0, y1, (y0, y1)) if y0 < y1 else (y0, y1)

types_all = [t for t in TYPE_ORDER + [T_UNK] if t in set(df["vtype"])]
sel_types = st.sidebar.multiselect("위반유형", types_all, default=[t for t in types_all if t != T_UNK])
use_guess = st.sidebar.checkbox("'추정' 분류 포함", value=True, help="규칙으로 추정한 분류(원문 대조 전)를 포함합니다.")

f = df[df["year"].between(*sel_years) & df["vtype"].isin(sel_types)]
if sel_groups:
    f = f[f["group"].isin(sel_groups)]
if sel_items:
    f = f[f["item"].isin(sel_items)]
if not use_guess:
    f = f[f["conf"] == "확실"]


# ------------------------------------------------------------------ 도우미
def pcount(d, by):
    """제품 수 (제품마스터번호 중복 제거)"""
    return d.groupby(by)["id"].nunique()


def xtab(d, row, colm):
    return d.groupby([row, colm])["id"].nunique().unstack(fill_value=0)


def rgba(hex_color, a):
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def style(fig, h=360, legend=True):
    fig.update_layout(
        height=h, margin=dict(l=6, r=24, t=24, b=6),
        font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_family=FONT, bgcolor="white"),
        showlegend=legend, legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
    )
    fig.update_xaxes(gridcolor="#E6EEE9", zeroline=False)
    fig.update_yaxes(gridcolor="#E6EEE9", zeroline=False)
    return fig


_key = [0]


def draw(build, *args, **kw):
    """그래프 하나가 실패해도 대시보드 전체가 멈추지 않게 보호"""
    _key[0] += 1
    try:
        st.plotly_chart(build(*args, **kw), config={"displayModeBar": False}, key=f"chart_{_key[0]}")
    except Exception as e:  # noqa
        st.caption(f"⚠️ 이 그래프를 그리지 못했습니다: {e}")


# ---- 계층 데이터 만들기 (순수 함수: 그래프 라이브러리와 분리) -------------
def tree_nodes(h):
    """h: DataFrame[group, item, n] -> 전체 > 대분류 > 중분류 노드 목록"""
    ids, labels, parents, values, colors = ["root"], ["전체"], [""], [0], ["#E4EFE9"]
    for g, gd in h.groupby("group"):
        gid = f"g|{g}"
        ids.append(gid); labels.append(g); parents.append("root"); values.append(int(gd["n"].sum())); colors.append(GCOL.get(g, GREEN))
        for r in gd.itertuples():
            ids.append(f"{gid}|{r.item}"); labels.append(r.item); parents.append(gid)
            values.append(int(r.n)); colors.append(GCOL.get(g, GREEN))
    values[0] = int(h["n"].sum())
    return ids, labels, parents, values, colors


def sun_nodes(h):
    """h: DataFrame[group, item, vtype, n] -> 전체 > 대분류 > 중분류 > 위반유형"""
    ids, labels, parents, values, colors = ["root"], ["전체"], [""], [int(h["n"].sum())], ["#E4EFE9"]
    for g, gd in h.groupby("group"):
        gid = f"g|{g}"
        ids.append(gid); labels.append(g); parents.append("root"); values.append(int(gd["n"].sum())); colors.append(GCOL.get(g, GREEN))
        for it, idd in gd.groupby("item"):
            iid = f"{gid}|{it}"
            ids.append(iid); labels.append(it); parents.append(gid); values.append(int(idd["n"].sum())); colors.append(GCOL.get(g, GREEN))
            for r in idd.itertuples():
                ids.append(f"{iid}|{r.vtype}"); labels.append(r.vtype); parents.append(iid)
                values.append(int(r.n)); colors.append(TYPE_COLOR.get(r.vtype, "#8C9A94"))
    return ids, labels, parents, values, colors


# ---- 그래프 ------------------------------------------------------------
def fig_treemap(h):
    ids, labels, parents, values, colors = tree_nodes(h)
    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
        marker=dict(colors=colors, line=dict(width=2, color="white")),
        texttemplate="<b>%{label}</b><br>%{value:,}개", textfont=dict(family=FONT, color="white", size=14),
        hovertemplate="%{label}<br>%{value:,}개 (제품 수 합계)<extra></extra>", root_color="#E4EFE9",
        tiling=dict(pad=4)))
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FONT))
    return fig


def fig_sunburst(h):
    ids, labels, parents, values, colors = sun_nodes(h)
    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
        marker=dict(colors=colors, line=dict(width=1.5, color="white")),
        insidetextfont=dict(family=FONT, color="white", size=12),
        hovertemplate="%{label}<br>%{value:,}건<extra></extra>"))
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FONT))
    return fig


def fig_sankey(d, n_sub=8):
    gt = d.groupby(["group", "vtype"])["id"].nunique().reset_index(name="n")
    groups = [g for g in g_order if g in set(gt["group"])]
    types = [t for t in types_all if t in set(gt["vtype"])]
    sa = d[(d["vtype"] == T_SAFE) & ~d["subst"].isin([NO_SUBST, UNK_SUBST])]
    subs = pcount(sa, "subst").sort_values(ascending=False).head(n_sub) if not sa.empty else pd.Series(dtype=int)
    labels = groups + types + list(subs.index)
    pos = {name: i for i, name in enumerate(labels)}
    colors = [GCOL.get(g, GREEN) for g in groups] + [TYPE_COLOR.get(t, "#8C9A94") for t in types] + [rgba(TYPE_COLOR[T_SAFE], 0.75)] * len(subs)
    src, tgt, val, lcol = [], [], [], []
    for r in gt.itertuples():
        src.append(pos[r.group]); tgt.append(pos[r.vtype]); val.append(int(r.n))
        lcol.append(rgba(GCOL.get(r.group, GREEN), 0.35))
    if T_SAFE in pos:
        for s, n in subs.items():
            src.append(pos[T_SAFE]); tgt.append(pos[s]); val.append(int(n)); lcol.append(rgba(TYPE_COLOR[T_SAFE], 0.25))
    fig = go.Figure(go.Sankey(
        node=dict(label=labels, color=colors, pad=16, thickness=18, line=dict(color="white", width=0.5)),
        link=dict(source=src, target=tgt, value=val, color=lcol),
        textfont=dict(family=FONT, size=13, color=INK)))
    fig.update_layout(height=560, margin=dict(l=6, r=6, t=10, b=6), font=dict(family=FONT, size=13, color=INK),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def hbar(labels, values, color, xtitle="제품 수"):
    cols = color if isinstance(color, list) else color
    fig = go.Figure(go.Bar(x=list(values), y=list(labels), orientation="h", marker_color=cols,
                           text=[f"{v:,}" for v in values], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:,}개<extra></extra>"))
    fig.update_layout(xaxis_title=xtitle, yaxis_title="")
    fig.update_yaxes(autorange="reversed")
    return style(fig, h=max(300, 34 * len(labels) + 70), legend=False)


def vbar_types(vt):
    fig = go.Figure(go.Bar(x=list(vt.index), y=list(vt.values),
                           marker_color=[TYPE_COLOR.get(t, "#999") for t in vt.index],
                           text=[f"{v:,}" for v in vt.values], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y:,}개<extra></extra>"))
    fig.update_layout(yaxis_title="제품 수", xaxis_title="")
    return style(fig, h=340, legend=False)


def trend(yt, h=340):
    fig = go.Figure()
    for t in [t for t in types_all if t in yt.columns]:
        fig.add_trace(go.Scatter(x=yt.index, y=yt[t], name=t, mode="lines+markers",
                                 line=dict(color=TYPE_COLOR.get(t), width=3), marker=dict(size=7)))
    fig.update_layout(hovermode="x unified", yaxis_title="제품 수", xaxis_title="")
    fig.update_xaxes(dtick=1)
    return style(fig, h=h)


def stacked_types(ct, pct, colors=None):
    data = ct.div(ct.sum(axis=1), axis=0) * 100 if pct else ct
    order = ct.sum(axis=1).sort_values().index.tolist()
    fig = go.Figure()
    for t in ct.columns:
        fig.add_trace(go.Bar(
            name=t, y=list(data.index), x=list(data[t].round(1 if pct else 0)), orientation="h",
            marker_color=TYPE_COLOR.get(t, "#999"),
            hovertemplate="%{y}<br>" + t + ": %{x}" + ("%" if pct else "개") + "<extra></extra>"))
    fig.update_layout(barmode="stack", xaxis_title="유형 구성비(%)" if pct else "제품 수", yaxis_title="")
    fig.update_yaxes(categoryorder="array", categoryarray=order)
    return style(fig, h=max(320, 36 * len(ct) + 90))


def heat(ct, unit_txt="개"):
    fig = go.Figure(go.Heatmap(
        z=ct.values, x=list(ct.columns), y=list(ct.index), text=ct.values, texttemplate="%{text}",
        colorscale=[[0, "#F1F6F3"], [1, GREEN_DARK]], showscale=False, xgap=2, ygap=2,
        hovertemplate="%{y} / %{x}: %{z}" + unit_txt + "<extra></extra>"))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(side="top", gridcolor="rgba(0,0,0,0)")
    return style(fig, h=max(300, 36 * len(ct) + 90), legend=False)


def stacked_actions(at):
    fig = go.Figure()
    for i, a in enumerate(at.columns):
        fig.add_trace(go.Bar(name=a, y=list(at.index), x=list(at[a]), orientation="h",
                             marker_color=SEQ[i % len(SEQ)], hovertemplate="%{y}<br>" + a + ": %{x}개<extra></extra>"))
    fig.update_layout(barmode="stack", xaxis_title="제품 수", yaxis_title="")
    fig.update_yaxes(autorange="reversed")
    return style(fig, h=max(300, 34 * len(at) + 90))


def card(title, caption=None):
    box = st.container(border=True)
    with box:
        st.markdown(f"#### {title}")
        if caption:
            st.markdown(f'<div class="note">{caption}</div>', unsafe_allow_html=True)
    return box


# ------------------------------------------------------------------ 헤더 + 요약
if is_demo:
    st.warning("데모(가짜) 데이터입니다. analysis_long.csv 를 app.py 와 같은 위치에 두면 실제 데이터로 바뀝니다.")
if f.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 왼쪽 조건을 넓혀 보세요.")
    st.stop()

total = f["id"].nunique()
sa = f[f["vtype"] == T_SAFE]
sub = sa[~sa["subst"].isin([NO_SUBST, UNK_SUBST])]
items_cnt = pcount(f, "item_sel").sort_values(ascending=False)
grp_cnt = pcount(f, "group").sort_values(ascending=False)
types_cnt = pcount(f, "vtype").sort_values(ascending=False)
top_items = items_cnt.head(top_k).index.tolist()

st.markdown(f"""
<div class="hero">
  <div class="src">초록누리 공개 위반제품 데이터</div>
  <h1>생활화학제품 위반정보 분석</h1>
  <div class="desc">대분류와 중분류 품목별로 위반유형과 위반물질을 살펴보는 시범 대시보드입니다.</div>
  <span class="chip">위반 제품 {df['id'].nunique():,}개</span>
  <span class="chip">조치연도 {y0}–{y1}</span>
  <span class="chip">대분류 {df['group'].nunique()}개 · 중분류 {df['item'].nunique()}개</span>
  <span class="chip">위반유형·물질은 규칙 기반 1차 분류(초안)</span>
</div>
""", unsafe_allow_html=True)

lines = [f"선택 조건의 위반 제품은 <b>{total:,}개</b>이고, 대분류로는 <b>{grp_cnt.index[0]}</b>"
         f"({grp_cnt.iloc[0]:,}개, {grp_cnt.iloc[0] / total:.0%})이 가장 많습니다."]
top_it = pcount(f, "item").sort_values(ascending=False)
lines.append(f"중분류(품목)로는 <b>{top_it.index[0]}</b>이 {top_it.iloc[0]:,}개({top_it.iloc[0] / total:.0%})로 가장 많고, "
             f"위반유형은 <b>{types_cnt.index[0]}</b>이 {types_cnt.iloc[0]:,}개로 가장 많습니다.")
if not sub.empty:
    ts = pcount(sub, "subst").sort_values(ascending=False)
    lines.append(f"함유·함량 물질이 확인된 안전기준 위반에서는 <b>{ts.index[0]}</b>이 {ts.iloc[0]:,}개 제품에서 나왔습니다.")
st.markdown('<div class="brief">' + "<br>".join(lines) + "</div>", unsafe_allow_html=True)

n_subst = f.loc[~f["subst"].isin([NO_SUBST, UNK_SUBST]), "subst"].nunique()
st.markdown(f"""
<div class="kpis">
  <div class="kpi"><div class="k">위반 제품</div><div class="v">{total:,}<small>개</small></div></div>
  <div class="kpi"><div class="k">위반사유 건수</div><div class="v">{len(f.drop_duplicates(['id', 'vtype', 'subst'])):,}<small>건</small></div></div>
  <div class="kpi"><div class="k">대분류 · 중분류</div><div class="v">{f['group'].nunique()} · {f['item'].nunique()}<small>개</small></div></div>
  <div class="kpi"><div class="k">확인된 위반물질</div><div class="v">{n_subst:,}<small>종</small></div></div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["한눈에 보기", "구조 · 흐름", "품목 비교", "위반물질", "품목 상세", "데이터"])

# ---------- 한눈에 보기
with tab1:
    with card("대분류 → 중분류 품목 규모", "칸이 클수록 위반 제품이 많습니다. 색은 대분류, 안의 칸은 중분류(품목)입니다."):
        h = f.groupby(["group", "item"])["id"].nunique().reset_index(name="n")
        draw(fig_treemap, h)
    a, b = st.columns([1, 1])
    with a:
        with card("위반유형별 제품 수"):
            vt = types_cnt.reindex([t for t in types_all if t in types_cnt.index])
            draw(vbar_types, vt)
    with b:
        with card("연도별 위반유형 추이"):
            yt = xtab(f.dropna(subset=["year"]), "year", "vtype")
            yt.index = yt.index.astype(int)
            draw(trend, yt)

# ---------- 구조 · 흐름
with tab2:
    a, b = st.columns([1, 1])
    with a:
        with card("대분류 → 중분류 → 위반유형", "조각을 클릭하면 확대됩니다. 중앙을 클릭하면 되돌아옵니다. 건수는 제품×유형 기준입니다."):
            hs = f.groupby(["group", "item", "vtype"])["id"].nunique().reset_index(name="n")
            draw(fig_sunburst, hs)
    with b:
        with card("대분류별 위반유형 구성 (%)"):
            ctg = xtab(f, "group", "vtype")
            ctg = ctg[[t for t in types_all if t in ctg.columns]]
            draw(stacked_types, ctg, True)
    with card("대분류 → 위반유형 → 주요 위반물질 흐름", "띠의 두께는 제품 수입니다. 위반물질은 ‘안전기준 위반’에서 확인된 상위 8개만 표시합니다."):
        draw(fig_sankey, f)

# ---------- 품목 비교
with tab3:
    mode = st.radio("표시 방식", ["제품 수", "구성비(%)"], horizontal=True)
    sub_f = f[f["item_sel"].isin(top_items)]
    ct = xtab(sub_f, "item_sel", "vtype")
    ct = ct[[t for t in types_all if t in ct.columns]]
    with card(f"{unit} 별 위반유형 구성"):
        draw(stacked_types, ct, mode != "제품 수")
    with card(f"{unit} × 위반유형"):
        draw(heat, ct.loc[ct.sum(axis=1).sort_values(ascending=False).index])

# ---------- 위반물질
with tab4:
    st.markdown(f"**{T_SAFE}** 중 함유·함량 물질이 확인된 건이 대상입니다. '{UNK_SUBST}'(파생제품 등)은 제외했습니다.")
    if sa.empty:
        st.info("왼쪽 위반유형에 '안전기준 위반'을 포함해 주세요.")
    elif sub.empty:
        st.info("물질이 확인된 데이터가 없습니다.")
    else:
        st.markdown(f'<div class="note">안전기준 위반 제품 {sa["id"].nunique():,}개 중 물질이 확인된 제품은 {sub["id"].nunique():,}개입니다.</div>',
                    unsafe_allow_html=True)
        n_sub = st.slider("보여줄 물질 수", 3, 20, 10)
        top = pcount(sub, "subst").sort_values(ascending=False).head(n_sub)
        a, b = st.columns(2)
        with a:
            with card("주요 위반물질"):
                draw(hbar, top.index, top.values, TYPE_COLOR[T_SAFE])
        with b:
            with card("물질별 조치유형"):
                at = xtab(sub[sub["subst"].isin(top.index)], "subst", "action").loc[top.index]
                at = at[at.sum().sort_values(ascending=False).head(5).index]
                draw(stacked_actions, at)
        with card(f"{unit} × 위반물질"):
            ss = sub[sub["item_sel"].isin(top_items) & sub["subst"].isin(top.index)]
            if ss.empty:
                st.info("표시할 데이터가 없습니다.")
            else:
                ct2 = xtab(ss, "item_sel", "subst")
                ct2 = ct2[[c for c in top.index if c in ct2.columns]]
                draw(heat, ct2)

# ---------- 품목 상세 (대분류 → 중분류 선택)
with tab5:
    c1, c2 = st.columns(2)
    sel_g = c1.selectbox("대분류", sorted(f["group"].unique()))
    gi = f[f["group"] == sel_g]
    sel_i = c2.selectbox("중분류 (품목)", ["대분류 전체"] + sorted(gi["item"].unique()))
    g = gi if sel_i == "대분류 전체" else gi[gi["item"] == sel_i]
    st.markdown(f"**{sel_g}{'' if sel_i == '대분류 전체' else ' › ' + sel_i}** 위반 제품은 **{g['id'].nunique():,}개**입니다.")
    a, b = st.columns(2)
    with a:
        with card("위반유형"):
            s = pcount(g, "vtype")
            s = s.reindex([t for t in types_all if t in s.index])
            draw(vbar_types, s)
    with b:
        if sel_i == "대분류 전체":
            with card("중분류(품목)별 제품 수"):
                s = pcount(g, "item").sort_values(ascending=False)
                draw(hbar, s.index, s.values, GCOL.get(sel_g, GREEN))
        else:
            with card("주요 위반물질"):
                gs = g[(g["vtype"] == T_SAFE) & ~g["subst"].isin([NO_SUBST, UNK_SUBST])]
                if gs.empty:
                    st.info("물질이 확인된 안전기준 위반이 없습니다.")
                else:
                    s = pcount(gs, "subst").sort_values(ascending=False).head(8)
                    draw(hbar, s.index, s.values, TYPE_COLOR[T_SAFE])
    with card("연도별 위반유형 추이"):
        yt2 = xtab(g.dropna(subset=["year"]), "year", "vtype")
        yt2.index = yt2.index.astype(int)
        draw(trend, yt2, 300)

# ---------- 데이터
with tab6:
    out = f.drop(columns=["item_sel"])
    st.dataframe(out)
    st.download_button("현재 조건의 데이터를 CSV로 저장", out.to_csv(index=False).encode("utf-8-sig"),
                       "filtered.csv", "text/csv")

with st.expander("분류 기준과 데이터 안내"):
    st.markdown(f"""
- **계층 구조**: 대분류는 `product_group`, 중분류는 `product_type`(품목)입니다. 한 제품이 여러 품목에 걸치면 각 품목에 포함됩니다.
- **건수 기준**: 막대·히트맵의 숫자는 제품마스터번호 기준 제품 수입니다. 트리맵의 큰 칸 합계는 품목별 제품 수의 합이라 전체 제품 수보다 클 수 있습니다.
- **위반유형 분류**: 위반사유 원문을 키워드 규칙으로 나눈 1차 결과이며, '추정' 건은 원문 대조 후 확정합니다.
- **위반물질**: 안전기준 위반 중 함유금지·함량제한 물질이 적힌 경우에만 집계합니다.
- **조치일자 결측**: {n_year_missing:,}개 제품은 연도를 알 수 없어 연도 조건과 추이 그래프에서 빠집니다.
""")
