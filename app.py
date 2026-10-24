"""
생활화학제품 위반정보 분석 대시보드 (Streamlit v4 - Plotly 디자인판)

실행:  python -m streamlit run app.py
데이터: 같은 폴더의 analysis_long.csv  (없으면 데모 데이터)
필요 라이브러리: streamlit, pandas, numpy, plotly   (requirements.txt 참고)
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------ 설정
COL = {  # 오른쪽 값 = 실제 CSV 컬럼명 (다르면 여기만 수정)
    "id": "prdt_mstr_no", "item": "품목", "group": "품목군", "vtype": "위반유형",
    "subst": "위반물질", "action": "조치유형", "year": "조치연도", "conf": "분류신뢰도",
}
OPTIONAL = ["group", "conf"]
T_SAFE, T_CONF, T_LABEL, T_UNK = "안전기준 위반", "안전기준 적합확인 위반", "표시기준 위반", "미분류(검토필요)"
TYPE_ORDER = [T_SAFE, T_CONF, T_LABEL]
NO_SUBST, UNK_SUBST = "해당없음", "물질 미특정"

# 색: 위반유형은 어느 그래프에서나 같은 색
INK, MUTED, LINE, BG = "#12303A", "#5B6F77", "#DCE5E8", "#F5F8F9"
TEAL, TEAL_DARK = "#1F7A8C", "#0B4F5C"
TYPE_COLOR = {T_SAFE: "#D1495B", T_CONF: "#E9A23B", T_LABEL: "#30638E", T_UNK: "#9AA5AA"}
SEQ = ["#0B4F5C", "#1F7A8C", "#6FB1BF", "#B7D7DD", "#E9A23B", "#9AA5AA"]
FONT = "Noto Sans KR, Malgun Gothic, AppleGothic, sans-serif"

st.set_page_config(page_title="생활화학제품 위반정보 대시보드", page_icon="🧪", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800&display=swap');
html, body, .stApp, .stMarkdown, p, h1, h2, h3, h4, label, button, input, textarea {{
    font-family: 'Noto Sans KR', sans-serif;
}}
.stApp {{ background: {BG}; color: {INK}; color-scheme: light; }}
.block-container {{ max-width: 1180px; padding-top: 2.2rem; }}
h1 {{ font-weight: 800; letter-spacing: -0.02em; color: {INK}; margin-bottom: .2rem; }}
h3, h4 {{ color: {INK}; font-weight: 700; letter-spacing: -0.01em; }}
section[data-testid="stSidebar"] {{ background: #E8EFF1; border-right: 1px solid {LINE}; }}
.sub {{ color: {MUTED}; font-size: 0.98rem; margin-bottom: 1.1rem; }}
.brief {{ background: #fff; border: 1px solid {LINE}; border-left: 5px solid {TEAL};
          border-radius: 8px; padding: 14px 20px; margin: .4rem 0 1.2rem 0; line-height: 1.85; }}
.brief b {{ color: {TEAL_DARK}; }}
.note {{ color: {MUTED}; font-size: .85rem; }}
[data-testid="stMetric"] {{ border-left: 3px solid {TEAL}; padding: 2px 0 2px 14px; }}
[data-testid="stMetricValue"] {{ font-weight: 800; color: {INK}; }}
[data-testid="stMetricLabel"] p {{ color: {MUTED}; }}
button[data-baseweb="tab"] p {{ font-weight: 600; font-size: 1rem; }}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ 데이터
@st.cache_data
def load_data():
    path = Path(__file__).parent / "analysis_long.csv"
    if path.exists():
        return pd.read_csv(path, encoding="utf-8-sig"), False
    rng = np.random.default_rng(0)  # 데모 데이터
    items = ["코팅제", "물체 염색제", "방향제", "세정제", "접착제", "살균제"]
    subs = ["MIT", "CMIT", "폼알데하이드", "니켈", "벤젠", "톨루엔"]
    rows = []
    for pid in range(1, 301):
        it, yr = rng.choice(items), int(rng.integers(2018, 2026))
        for t in rng.choice(TYPE_ORDER, size=int(rng.integers(1, 3)), replace=False):
            rows.append([pid, it, it, t, rng.choice(subs) if t == T_SAFE else NO_SUBST,
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
    df["group"] = df["item"]
if "conf" not in df:
    df["conf"] = "확실"
df["subst"] = df["subst"].fillna(NO_SUBST)
df["year"] = pd.to_numeric(df["year"], errors="coerce")
n_year_missing = df.loc[df["year"].isna(), "id"].nunique()

# ------------------------------------------------------------------ 사이드바
st.sidebar.markdown("### 조건 설정")
basis = st.sidebar.radio("품목 기준", ["세부 품목", "품목군(대분류)"])
df["item_sel"] = df["item"] if basis == "세부 품목" else df["group"]
items_all = sorted(df["item_sel"].unique())
sel_items = st.sidebar.multiselect("품목 선택 (비우면 전체)", items_all, default=[])
top_max = max(4, min(20, len(items_all)))
top_k = st.sidebar.slider("그래프에 보여줄 품목 수", 3, top_max, min(10, top_max))

yrs = df["year"].dropna()
y0, y1 = int(yrs.min()), int(yrs.max())
sel_years = st.sidebar.slider("조치연도", y0, y1, (y0, y1)) if y0 < y1 else (y0, y1)

types_all = [t for t in TYPE_ORDER + [T_UNK] if t in set(df["vtype"])]
sel_types = st.sidebar.multiselect("위반유형", types_all, default=[t for t in types_all if t != T_UNK])
use_guess = st.sidebar.checkbox("'추정' 분류 포함", value=True,
                                help="규칙으로 추정한 분류(원문 대조 전)를 포함합니다.")

f = df[df["year"].between(*sel_years) & df["vtype"].isin(sel_types)]
if sel_items:
    f = f[f["item_sel"].isin(sel_items)]
if not use_guess:
    f = f[f["conf"] == "확실"]


# ------------------------------------------------------------------ 도우미
def pcount(d, by):
    """by 기준 제품 수 (제품마스터번호 중복 제거)"""
    return d.groupby(by)["id"].nunique()


def xtab(d, row, colm):
    return d.groupby([row, colm])["id"].nunique().unstack(fill_value=0)


def style(fig, h=360, legend=True):
    fig.update_layout(
        height=h, margin=dict(l=4, r=24, t=30, b=6),
        font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_family=FONT, bgcolor="white"),
        showlegend=legend, legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
    )
    fig.update_xaxes(gridcolor="#E3EAED", zeroline=False)
    fig.update_yaxes(gridcolor="#E3EAED", zeroline=False)
    return fig


def draw(build, *args, **kw):
    """그래프 하나가 실패해도 대시보드 전체가 멈추지 않게 보호"""
    try:
        st.plotly_chart(build(*args, **kw), config={"displayModeBar": False})
    except Exception as e:  # noqa
        st.caption(f"⚠️ 이 그래프를 그리지 못했습니다: {e}")


def hbar(labels, values, color, xtitle="제품 수"):
    fig = go.Figure(go.Bar(x=list(values), y=list(labels), orientation="h", marker_color=color,
                           text=list(values), textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x}개<extra></extra>"))
    fig.update_layout(xaxis_title=xtitle, yaxis_title="")
    fig.update_yaxes(autorange="reversed")
    return style(fig, h=max(300, 34 * len(labels) + 70), legend=False)


def vbar_types(vt):
    fig = go.Figure(go.Bar(x=list(vt.index), y=list(vt.values),
                           marker_color=[TYPE_COLOR.get(t, "#999") for t in vt.index],
                           text=list(vt.values), textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y}개<extra></extra>"))
    fig.update_layout(yaxis_title="제품 수", xaxis_title="")
    return style(fig, h=340, legend=False)


def trend(yt):
    fig = go.Figure()
    for t in [t for t in types_all if t in yt.columns]:
        fig.add_trace(go.Scatter(x=yt.index, y=yt[t], name=t, mode="lines+markers",
                                 line=dict(color=TYPE_COLOR.get(t), width=3), marker=dict(size=7)))
    fig.update_layout(hovermode="x unified", yaxis_title="제품 수", xaxis_title="")
    fig.update_xaxes(dtick=1)
    return style(fig, h=340)


def stacked_types(ct, pct):
    data = ct.div(ct.sum(axis=1), axis=0) * 100 if pct else ct
    order = ct.sum(axis=1).sort_values().index.tolist()  # 합계 작은 것부터 (가로막대는 아래→위)
    fig = go.Figure()
    for t in ct.columns:
        fig.add_trace(go.Bar(
            name=t, y=list(data.index), x=list(data[t].round(1 if pct else 0)), orientation="h",
            marker_color=TYPE_COLOR.get(t, "#999"),
            hovertemplate="%{y}<br>" + t + ": %{x}" + ("%" if pct else "개") + "<extra></extra>"))
    fig.update_layout(barmode="stack", xaxis_title="유형 구성비(%)" if pct else "제품 수", yaxis_title="")
    fig.update_yaxes(categoryorder="array", categoryarray=order)
    return style(fig, h=max(320, 36 * len(ct) + 90))


def heat(ct, tooltip_unit="개"):
    fig = go.Figure(go.Heatmap(
        z=ct.values, x=list(ct.columns), y=list(ct.index), text=ct.values, texttemplate="%{text}",
        colorscale=[[0, "#F1F6F7"], [1, TEAL_DARK]], showscale=False, xgap=2, ygap=2,
        hovertemplate="%{y} / %{x}: %{z}" + tooltip_unit + "<extra></extra>"))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(side="top", gridcolor="rgba(0,0,0,0)")
    return style(fig, h=max(300, 36 * len(ct) + 90), legend=False)


def stacked_actions(at):
    fig = go.Figure()
    for i, a in enumerate(at.columns):
        fig.add_trace(go.Bar(name=a, y=list(at.index), x=list(at[a]), orientation="h",
                             marker_color=SEQ[i % len(SEQ)],
                             hovertemplate="%{y}<br>" + a + ": %{x}개<extra></extra>"))
    fig.update_layout(barmode="stack", xaxis_title="제품 수", yaxis_title="")
    fig.update_yaxes(autorange="reversed")
    return style(fig, h=max(300, 34 * len(at) + 90))


# ------------------------------------------------------------------ 헤더
st.title("생활화학제품 위반정보, 품목별로 보기")
st.markdown('<div class="sub">초록누리 공개 위반제품 데이터를 조치일자 기준으로 정리했습니다. '
            '왼쪽에서 품목·연도·위반유형을 고르면 모든 그래프가 함께 바뀝니다.</div>', unsafe_allow_html=True)

if is_demo:
    st.warning("데모(가짜) 데이터입니다. analysis_long.csv 를 app.py 와 같은 위치에 두면 실제 데이터로 바뀝니다.")
if f.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 왼쪽 조건을 넓혀 보세요.")
    st.stop()

total = f["id"].nunique()
items_cnt = pcount(f, "item_sel").sort_values(ascending=False)
types_cnt = pcount(f, "vtype").sort_values(ascending=False)
sa = f[f["vtype"] == T_SAFE]
sub = sa[~sa["subst"].isin([NO_SUBST, UNK_SUBST])]
top_items = items_cnt.head(top_k).index.tolist()

# 핵심 요약 (선택한 조건에 맞춰 자동 계산)
lines = [f"선택 조건의 위반 제품은 <b>{total:,}개</b>이고, 가장 많은 품목은 <b>{items_cnt.index[0]}</b>"
         f"({items_cnt.iloc[0]:,}개, {items_cnt.iloc[0] / total:.0%})입니다."]
if len(types_cnt):
    lines.append(f"위반유형은 <b>{types_cnt.index[0]}</b>이 {types_cnt.iloc[0]:,}개({types_cnt.iloc[0] / total:.0%})로 가장 많습니다.")
if not sub.empty:
    ts = pcount(sub, "subst").sort_values(ascending=False)
    lines.append(f"함유·함량 물질이 확인된 안전기준 위반에서는 <b>{ts.index[0]}</b>이 {ts.iloc[0]:,}개 제품에서 나왔습니다.")
st.markdown('<div class="brief">' + "<br>".join(lines) + "</div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("위반 제품", f"{total:,}개")
c2.metric("위반사유 건수", f"{len(f.drop_duplicates(['id', 'vtype', 'subst'])):,}건")
c3.metric("품목 수", f"{f['item_sel'].nunique():,}개")
c4.metric("확인된 위반물질", f"{f.loc[~f['subst'].isin([NO_SUBST, UNK_SUBST]), 'subst'].nunique():,}종")
st.write("")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["한눈에 보기", "품목 비교", "위반물질", "품목 상세", "데이터"])

# ---------- 한눈에 보기
with tab1:
    a, b = st.columns([3, 2])
    with a:
        st.markdown("#### 품목별 위반 제품 수")
        cnt = items_cnt.loc[top_items]
        draw(hbar, cnt.index, cnt.values, TEAL)
    with b:
        st.markdown("#### 위반유형별 제품 수")
        vt = types_cnt.reindex([t for t in types_all if t in types_cnt.index])
        draw(vbar_types, vt)
    st.markdown("#### 연도별 위반유형 추이")
    yt = xtab(f.dropna(subset=["year"]), "year", "vtype")
    yt.index = yt.index.astype(int)
    draw(trend, yt)

# ---------- 품목 비교
with tab2:
    mode = st.radio("표시 방식", ["제품 수", "구성비(%)"], horizontal=True)
    sub_f = f[f["item_sel"].isin(top_items)]
    ct = xtab(sub_f, "item_sel", "vtype")
    ct = ct[[t for t in types_all if t in ct.columns]]
    st.markdown("#### 품목별 위반유형 구성")
    draw(stacked_types, ct, mode != "제품 수")
    st.markdown("#### 품목 × 위반유형")
    draw(heat, ct.loc[ct.sum(axis=1).sort_values(ascending=False).index])

# ---------- 위반물질
with tab3:
    st.markdown(f"**{T_SAFE}** 중 함유·함량 물질이 확인된 건이 대상입니다. "
                f"'{UNK_SUBST}'(파생제품 등)은 제외했습니다.")
    if sa.empty:
        st.info("왼쪽 위반유형에 '안전기준 위반'을 포함해 주세요.")
    elif sub.empty:
        st.info("물질이 확인된 데이터가 없습니다.")
    else:
        st.markdown(f'<div class="note">안전기준 위반 제품 {sa["id"].nunique():,}개 중 '
                    f'물질이 확인된 제품은 {sub["id"].nunique():,}개입니다.</div>', unsafe_allow_html=True)
        n_sub = st.slider("보여줄 물질 수", 3, 20, 10)
        top = pcount(sub, "subst").sort_values(ascending=False).head(n_sub)
        a, b = st.columns(2)
        with a:
            st.markdown("#### 주요 위반물질")
            draw(hbar, top.index, top.values, TYPE_COLOR[T_SAFE])
        with b:
            st.markdown("#### 물질별 조치유형")
            at = xtab(sub[sub["subst"].isin(top.index)], "subst", "action").loc[top.index]
            at = at[at.sum().sort_values(ascending=False).head(5).index]
            draw(stacked_actions, at)
        st.markdown("#### 품목 × 위반물질")
        ss = sub[sub["item_sel"].isin(top_items) & sub["subst"].isin(top.index)]
        if ss.empty:
            st.info("표시할 품목에 해당하는 물질 데이터가 없습니다.")
        else:
            ct2 = xtab(ss, "item_sel", "subst")
            ct2 = ct2[[c for c in top.index if c in ct2.columns]]
            draw(heat, ct2)

# ---------- 품목 상세
with tab4:
    one = st.selectbox("품목 선택", sorted(f["item_sel"].unique()))
    g = f[f["item_sel"] == one]
    st.markdown(f"**{one}** 위반 제품은 **{g['id'].nunique():,}개**입니다.")
    a, b = st.columns(2)
    with a:
        st.markdown("#### 위반유형")
        s = pcount(g, "vtype")
        s = s.reindex([t for t in types_all if t in s.index])
        draw(vbar_types, s)
    with b:
        st.markdown("#### 주요 위반물질")
        gs = g[(g["vtype"] == T_SAFE) & ~g["subst"].isin([NO_SUBST, UNK_SUBST])]
        if gs.empty:
            st.info("이 품목은 물질이 확인된 안전기준 위반이 없습니다.")
        else:
            s = pcount(gs, "subst").sort_values(ascending=False).head(8)
            draw(hbar, s.index, s.values, TYPE_COLOR[T_SAFE])

# ---------- 데이터
with tab5:
    out = f.drop(columns=["item_sel"])
    st.dataframe(out)
    st.download_button("현재 조건의 데이터를 CSV로 저장", out.to_csv(index=False).encode("utf-8-sig"),
                       "filtered.csv", "text/csv")

with st.expander("분류 기준과 데이터 안내"):
    st.markdown(f"""
- **건수 기준**: 모든 숫자는 제품마스터번호 기준 제품 수입니다. 한 제품이 여러 유형·품목에 해당하면 각각에 포함되어 합계가 전체 제품 수보다 클 수 있습니다.
- **위반유형 분류**: 위반사유 원문을 키워드 규칙으로 나눈 1차 결과이며, '추정' 건은 원문 대조 후 확정합니다.
- **위반물질**: 안전기준 위반 중 함유금지·함량제한 물질이 적힌 경우에만 집계합니다.
- **조치일자 결측**: {n_year_missing:,}개 제품은 연도를 알 수 없어 연도 조건과 추이 그래프에서 빠집니다.
""")
