"""
생활화학제품 위반정보 분석 대시보드 (Streamlit 시제품 v3)

실행 (VS Code 터미널):  python -m streamlit run app.py

데이터: 같은 폴더의 analysis_long.csv 를 읽습니다.
        (classify_violations.py 를 실행하면 자동 생성됩니다)
        파일이 없으면 '데모 데이터'로 화면만 띄웁니다.

analysis_long.csv 형식 (1행 = 제품 1개 x 위반유형 1개 x 위반물질 1개)
  prdt_mstr_no, 품목, 품목군, 위반유형, 위반물질, 조치유형, 조치연도, 분류신뢰도
  - 위반물질은 '안전기준 위반'일 때만 물질명, 그 외는 '해당없음'
  - 모든 건수는 '제품 수(제품마스터번호 기준 중복 제거)'로 셉니다.
"""
import platform
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from matplotlib import font_manager

# ------------------------------------------------------------------ 설정
COL = {  # 오른쪽 값 = 실제 CSV 컬럼명 (다르면 여기만 수정)
    "id": "prdt_mstr_no",
    "item": "품목",
    "group": "품목군",       # 없어도 동작
    "vtype": "위반유형",
    "subst": "위반물질",
    "action": "조치유형",
    "year": "조치연도",
    "conf": "분류신뢰도",    # 없어도 동작
}
OPTIONAL = ["group", "conf"]
T_SAFE, T_CONF, T_LABEL = "안전기준 위반", "안전기준 적합확인 위반", "표시기준 위반"
T_UNK = "미분류(검토필요)"
TYPE_ORDER = [T_SAFE, T_CONF, T_LABEL]
TYPE_COLOR = {T_SAFE: "#C44E52", T_CONF: "#DD8452", T_LABEL: "#4C72B0", T_UNK: "#999999"}
NO_SUBST, UNK_SUBST = "해당없음", "물질 미특정"

st.set_page_config(page_title="생활화학제품 위반정보 대시보드", layout="wide")
sns.set_theme(style="whitegrid")


def set_korean_font():
    cand = {"Windows": ["Malgun Gothic"], "Darwin": ["AppleGothic"],
            "Linux": ["NanumGothic", "Noto Sans CJK KR"]}.get(platform.system(), [])
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in cand:
        if name in installed:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


set_korean_font()


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
n_year_missing = df.loc[df["year"].isna(), "id"].nunique()
df["year"] = pd.to_numeric(df["year"], errors="coerce")

# ------------------------------------------------------------------ 사이드바
st.sidebar.header("필터")
basis = st.sidebar.radio("품목 기준", ["세부 품목", "품목군(대분류)"])
df["item_sel"] = df["item"] if basis == "세부 품목" else df["group"]

items_all = sorted(df["item_sel"].unique())
sel_items = st.sidebar.multiselect("품목 선택 (비우면 전체)", items_all, default=[])
top_k = st.sidebar.slider("그래프에 표시할 품목 수 (상위 N)", 3, max(4, min(20, len(items_all))), min(10, len(items_all)))

yrs = df["year"].dropna()
y0, y1 = int(yrs.min()), int(yrs.max())
sel_years = st.sidebar.slider("조치연도", y0, y1, (y0, y1)) if y0 < y1 else (y0, y1)

types_all = [t for t in TYPE_ORDER + [T_UNK] if t in set(df["vtype"])]
default_types = [t for t in types_all if t != T_UNK]
sel_types = st.sidebar.multiselect("위반유형", types_all, default=default_types)
use_guess = st.sidebar.checkbox("'추정' 분류 포함", value=True,
                                help="규칙으로 추정한 분류(원문 대조 전)를 포함합니다.")

f = df[df["year"].between(*sel_years) & df["vtype"].isin(sel_types)]
if sel_items:
    f = f[f["item_sel"].isin(sel_items)]
if not use_guess:
    f = f[f["conf"] == "확실"]

# ------------------------------------------------------------------ 본문
st.title("생활화학제품 품목별 위반 특성 대시보드")
if is_demo:
    st.warning("⚠️ 데모(가짜) 데이터입니다. analysis_long.csv 를 같은 폴더에 두면 실제 데이터로 바뀝니다.")
else:
    st.info("위반유형·위반물질은 규칙 기반 1차 분류(초안)입니다. '추정' 건은 원문 대조 후 확정 예정입니다.")
if f.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()


def pcount(d, by):
    """by 기준 '제품 수'(중복 제거)"""
    return d.groupby(by)["id"].nunique()


def xtab(d, row, colm):
    """row x colm 제품 수 교차표"""
    return d.groupby([row, colm])["id"].nunique().unstack(fill_value=0)


def finish(fig):
    st.pyplot(fig)
    plt.close(fig)


top_items = pcount(f, "item_sel").sort_values(ascending=False).head(top_k).index.tolist()

c1, c2, c3, c4 = st.columns(4)
c1.metric("위반 제품 수", f["id"].nunique())
c2.metric("위반사유 건수", len(f.drop_duplicates(["id", "vtype", "subst"])))
c3.metric("품목 수", f["item_sel"].nunique())
c4.metric("확인된 위반물질 수", f.loc[~f["subst"].isin([NO_SUBST, UNK_SUBST]), "subst"].nunique())
st.caption(f"※ 모든 건수는 제품 수 기준입니다. 한 제품이 여러 유형·품목에 해당할 수 있어 합계가 전체 제품 수보다 클 수 있습니다. "
           f"조치일자 결측 제품 {n_year_missing:,}개는 연도 필터 적용 시 제외됩니다.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["① 전체 통합", "② 품목 간 비교", "③ 위반물질 분석", "④ 품목 상세", "⑤ 원자료"])

# ---------- ① 전체 통합
with tab1:
    a, b = st.columns(2)
    with a:
        st.subheader("품목별 위반 제품 수")
        cnt = pcount(f, "item_sel").loc[top_items].sort_values()
        fig, ax = plt.subplots(figsize=(6, max(3.5, 0.4 * len(cnt))))
        ax.barh(cnt.index, cnt.values, color="#55A868")
        ax.set_xlabel("제품 수")
        finish(fig)
    with b:
        st.subheader("위반유형별 제품 수")
        vt = pcount(f, "vtype").reindex(types_all).dropna()
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(vt.index, vt.values, color=[TYPE_COLOR.get(t, "gray") for t in vt.index])
        ax.set_ylabel("제품 수")
        plt.xticks(rotation=15)
        finish(fig)

    st.subheader("연도별 위반유형 추이")
    yt = xtab(f.dropna(subset=["year"]), "year", "vtype")
    fig, ax = plt.subplots(figsize=(10, 4))
    for t in [t for t in types_all if t in yt.columns]:
        ax.plot(yt.index, yt[t], marker="o", label=t, color=TYPE_COLOR.get(t))
    ax.set_xlabel("조치연도")
    ax.set_ylabel("제품 수")
    ax.legend()
    finish(fig)

# ---------- ② 품목 간 비교
with tab2:
    mode = st.radio("표시 방식", ["제품 수", "비율(%)"], horizontal=True)
    sub_f = f[f["item_sel"].isin(top_items)]
    ct = xtab(sub_f, "item_sel", "vtype").reindex(columns=[t for t in types_all if t in set(sub_f["vtype"])])
    ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index]

    st.subheader("품목별 위반유형 구성 (누적 막대)")
    data = ct if mode == "제품 수" else ct.div(ct.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(10, 4.5))
    data.plot(kind="bar", stacked=True, ax=ax, color=[TYPE_COLOR.get(t, "gray") for t in data.columns])
    ax.set_xlabel("")
    ax.set_ylabel(mode)
    plt.xticks(rotation=30, ha="right")
    finish(fig)

    st.subheader("품목 × 위반유형 히트맵")
    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.45 * len(ct))))
    sns.heatmap(ct, annot=True, fmt="d", cmap="Blues", ax=ax)
    ax.set_xlabel("")
    ax.set_ylabel("")
    finish(fig)

# ---------- ③ 위반물질 분석
with tab3:
    st.markdown(f"**'{T_SAFE}'** 중 함유·함량 물질이 확인된 건을 대상으로 합니다. "
                f"('{UNK_SUBST}'은 파생제품·물질 미기재 등)")
    sa = f[f["vtype"] == T_SAFE]
    sub = sa[~sa["subst"].isin([NO_SUBST, UNK_SUBST])]
    if sa.empty:
        st.info("위반유형 필터에 '안전기준 위반'을 포함해 주세요.")
    elif sub.empty:
        st.info("물질이 확인된 데이터가 없습니다.")
    else:
        st.caption(f"안전기준 위반 제품 {sa['id'].nunique():,}개 중 물질 확인 {sub['id'].nunique():,}개")
        n_sub = st.slider("표시할 물질 수 (상위 N)", 3, 20, 10)
        top = pcount(sub, "subst").sort_values(ascending=False).head(n_sub)
        a, b = st.columns(2)
        with a:
            st.subheader("주요 위반물질 순위")
            fig, ax = plt.subplots(figsize=(6, max(3.5, 0.4 * len(top))))
            ax.barh(top.index[::-1], top.values[::-1], color="#C44E52")
            ax.set_xlabel("제품 수")
            finish(fig)
        with b:
            st.subheader("물질별 조치유형")
            at = xtab(sub[sub["subst"].isin(top.index)], "subst", "action").loc[top.index]
            keep = at.sum().sort_values(ascending=False).head(5).index  # 상위 5개 조치만
            at = at[keep]
            fig, ax = plt.subplots(figsize=(6, max(3.5, 0.4 * len(top))))
            at.plot(kind="barh", stacked=True, ax=ax)
            ax.invert_yaxis()
            ax.set_ylabel("")
            ax.legend(fontsize=7)
            finish(fig)

        st.subheader("품목 × 위반물질 히트맵")
        ss = sub[sub["item_sel"].isin(top_items) & sub["subst"].isin(top.index)]
        if ss.empty:
            st.info("표시할 품목에 해당하는 물질 데이터가 없습니다.")
        else:
            ct2 = xtab(ss, "item_sel", "subst").reindex(columns=[c for c in top.index if c in set(ss["subst"])])
            fig, ax = plt.subplots(figsize=(11, max(3.5, 0.45 * len(ct2))))
            sns.heatmap(ct2, annot=True, fmt="d", cmap="Reds", ax=ax)
            ax.set_xlabel("")
            ax.set_ylabel("")
            finish(fig)

# ---------- ④ 품목 상세
with tab4:
    one = st.selectbox("품목 선택", sorted(f["item_sel"].unique()))
    g = f[f["item_sel"] == one]
    st.write(f"**{one}** : 위반 제품 {g['id'].nunique():,}개")
    a, b = st.columns(2)
    with a:
        st.caption("위반유형 구성 (제품 수)")
        s = pcount(g, "vtype").reindex(types_all).dropna()
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(s.index, s.values, color=[TYPE_COLOR.get(t, "gray") for t in s.index])
        plt.xticks(rotation=15)
        finish(fig)
    with b:
        st.caption(f"주요 위반물질 ({T_SAFE})")
        gs = g[(g["vtype"] == T_SAFE) & ~g["subst"].isin([NO_SUBST, UNK_SUBST])]
        s = pcount(gs, "subst").sort_values(ascending=False).head(8) if not gs.empty else gs
        if len(s) == 0:
            st.info("해당 품목의 물질 확인 데이터가 없습니다.")
        else:
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.barh(s.index[::-1], s.values[::-1], color="#C44E52")
            finish(fig)

# ---------- ⑤ 원자료
with tab5:
    st.dataframe(f.drop(columns=["item_sel"]), use_container_width=True)
    st.download_button("필터링된 데이터 CSV 다운로드",
                       f.drop(columns=["item_sel"]).to_csv(index=False).encode("utf-8-sig"),
                       "filtered.csv", "text/csv")
