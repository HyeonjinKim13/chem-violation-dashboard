"""
위반사유(violt_cn) 규칙 기반 1차 분류 스크립트  (대강 분류용 초안)

입력 : product_scope_included_final.csv
출력 : product_with_violation_flags.csv  (원본 + 분류 컬럼 추가, 제품 1개 = 1행)
       analysis_long.csv                 (대시보드용, 1행 = 제품·위반유형·위반물질 1개)

실행 :  python classify_violations.py
※ 규칙 기반 '초안'입니다. 분류신뢰도가 '추정'/'미분류'인 행은 원문 대조로 검토하세요.
"""
import re
import sys
from pathlib import Path

import pandas as pd

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("product_scope_included_final.csv")
OUT_WIDE = Path("product_with_violation_flags.csv")
OUT_LONG = Path("analysis_long.csv")

T_SAFE, T_CONF, T_LABEL = "안전기준 위반", "안전기준 적합확인 위반", "표시기준 위반"
NO_SUBST, UNK_SUBST = "해당없음", "물질 미특정"

# ------------------------------------------------------------ 물질 사전 (표준명: 정규식)
SUBSTANCES = {
    "MIT": r"(?<![A-Za-z])MIT(?![A-Za-z])|(?<!클로로)메틸이소티아졸리논",
    "CMIT": r"CMIT|클로로메틸이소티아졸리논",
    "메틸메타크릴레이트(MMA)": r"MMA|메틸메타[아]?크릴레이트",
    "폼알데하이드": r"폼알데[하히]이?드|포름알데[하히]이?드",
    "아세트알데하이드": r"아세트알데[하히]이?드",
    "벤젠": r"벤젠",
    "톨루엔": r"톨루엔",
    "메탄올": r"메탄올",
    "니켈": r"니켈",
    "구리": r"구리",
    "납": r"(?<![가-힣])납(?![가-힣])",
    "아연": r"아연",
    "알루미늄": r"알루미늄",
    "카드뮴": r"카드뮴",
    "비소": r"(?<![가-힣])비소(?![가-힣])",
    "수은": r"수은",
    "트리클로로에틸렌": r"트리클로로\s*에틸렌|트라이클로로\s*에틸렌",
    "벤조(a)피렌": r"벤조\(a\)피렌|벤조피렌",
    "하이드로퀴논": r"하이드로퀴논|히드로퀴논",
    "아크릴로니트릴": r"아크릴로니트릴",
    "염화비닐": r"염화비닐",
    "5-나이트로-o-톨루이딘": r"나이트로-?o?-?톨루[이]?딘|니트로-?o?-?톨루이딘",
    "다이클로로메테인": r"다이클로로메테인|디클로로메탄",
    "에탄올": r"에탄올",
    "아세톤": r"아세톤",
    "자일렌": r"자일렌|크실렌",
    "아조염료": r"아조\s*염료|p-?cresidine|o-?아니시딘",
    "PHMB": r"PHMB",
    "PHMG": r"PHMG",
    "1,4-다이옥세인": r"1,\s*4-?\s*다이옥세[인엔]",
    "테트라클로로에틸렌": r"테트라클로로\s*에틸렌",
    "염화벤잘코늄류": r"염화\s*벤잘코늄",
    "은(Ag)": r"은\(銀\)",
    "클로로포름": r"클로로포름",
    "에틸렌글리콜": r"에틸렌\s*글리콜",
    "염산": r"염산",
    "황산": r"황산",
}
SUBST_RE = {k: re.compile(v) for k, v in SUBSTANCES.items()}

# ------------------------------------------------------------ 위반유형 규칙
RE_STRIP_PHRASE = re.compile(r"확인\s*을?\s*받은\s*내용과\s*다르게")           # '확인' 오탐 방지
RE_CONF = re.compile(
    r"(확인|신고|검사|승인|파생신고)[^,;()\[\]]{0,14}?(미실시|미이행|미수행|하지\s*(않|아니)|받지\s*(않|아니)|미필)"
    r"|미확인|미신고|확인\s*및\s*표시기준\s*미준수|안전확인[^,;]{0,10}미준수|신고\s*없이|적합확인[^,;]{0,10}(미실시|미이행)"
)
RE_LABEL = re.compile(r"표시|미표기|표기")
RE_SAFE = re.compile(
    r"안전기준\s*위반|안전기준을\s*위반|안전기준\s*초과|함유\s*금지|함량\s*제한|사용\s*금지\s*물질|"
    r"기준\s*초과|기준초과|검출|초과"
)
RE_DIFF = re.compile(r"(확인|승인)\s*을?\s*받은\s*(내용|사항)과?\s*다르게|확인\s*\(구\s*자가검사\)\s*받은\s*내용과\s*다르게|적합\s*확인\s*받은\s*내용과\s*다르게")
RE_LAW10 = re.compile(r"제\s*10\s*조[^.]{0,30}위반")
RE_LAW35 = re.compile(r"제\s*35\s*조")
RE_QUALITY = re.compile(r"무균시험\s*부적합|생분해도|주성분\s*함량|유효기간이?\s*만료|승인기준\s*위반")
RE_GENERIC = re.compile(r"안전\s*[·‧∙ㆍ.\-・]?\s*표시\s*기준\s*(위반|미준수)|행정처분")


def normalize(t: str) -> str:
    t = str(t).replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", t).strip()


def find_substances(t: str):
    return [name for name, rx in SUBST_RE.items() if rx.search(t)]


def classify(raw: str):
    t = normalize(raw)
    t2 = RE_STRIP_PHRASE.sub("", t)
    subs = find_substances(t2)

    conf = bool(RE_CONF.search(t2))
    label = bool(RE_LABEL.search(t2))
    # '동일한 신고번호' 문구(파생제품)는 적합확인 미실시가 아님
    t3 = re.sub(r"동일한\s*신고번호", "", t2)
    conf = conf and bool(RE_CONF.search(t3))
    safe_strong = bool(subs) or bool(re.search(
        r"안전기준을\s*위반|안전기준\s*초과|함유\s*금지|함량\s*제한|사용\s*금지\s*물질|기준\s*초과|기준초과|검출|초과|동일한\s*신고번호", t)) \
        or bool(RE_DIFF.search(t))
    safe_label = bool(re.search(r"안전기준\s*위반", t3))
    # '자가검사 미이행 (안전기준 위반)'처럼 라벨만 붙은 경우는 적합확인으로 본다
    safe = safe_strong or (safe_label and not conf)

    note, level = "", "확실"
    if not (safe or conf or label):
        if RE_DIFF.search(t):
            safe = True
            level, note = "추정", "'확인받은 내용과 다르게' → 안전기준 위반으로 추정"
        elif RE_GENERIC.search(t2):
            conf, label = True, True
            level, note = "추정", "세부 불명 '안전·표시기준 위반' → 적합확인+표시로 추정"
        elif RE_LAW10.search(t2):
            conf, label = True, bool(RE_LAW35.search(t2))
            level, note = "추정", "법 제10조(확인)/제35조(표시) 위반 문구로 추정"
        elif RE_QUALITY.search(t2):
            safe = True
            level, note = "추정", "품질·승인기준 부적합 → 안전기준 위반으로 추정"
        else:
            level, note = "미분류", "규칙에 해당하는 표현 없음(원문 검토 필요)"
    elif RE_DIFF.search(t) and not subs and not re.search(r"검출|초과", t):
        level, note = "추정", "'확인받은 내용과 다르게' → 안전기준 위반으로 추정"
    elif safe and not subs and not re.search(r"안전기준\s*위반|안전기준을\s*위반|동일한\s*신고번호", t):
        level, note = "추정", "물질명 미확인 검출/초과 표현"
    return int(safe), int(conf), int(label), subs, level, note


# ------------------------------------------------------------ 조치 정규화
ACTIONS = ["제조금지", "수입금지", "판매금지", "판매중단", "회수명령", "회수권고", "개선명령"]


def norm_action(a):
    if pd.isna(a) or str(a).strip() in ("", "-"):
        return "정보없음"
    a = str(a)
    got = [x for x in ACTIONS if x in a]
    if "회수" in a and "개선" in a and "회수명령" not in got:
        got += ["회수명령"]
    if "개선" in a and "개선명령" not in got:
        got.append("개선명령")
    if "회수" in a and not any(x in got for x in ["회수명령", "회수권고"]):
        got.append("회수명령")
    got = [x for x in ACTIONS if x in got]
    return "·".join(got) if got else "기타"


# ------------------------------------------------------------ 실행
df = pd.read_csv(SRC, encoding="utf-8-sig")
res = df["violt_cn"].fillna("").apply(classify)
df["안전기준_위반"] = res.str[0]
df["안전기준_적합확인_위반"] = res.str[1]
df["표시기준_위반"] = res.str[2]
df["위반물질"] = res.str[3].apply(lambda s: "; ".join(s))
df["분류신뢰도"] = res.str[4]
df["분류메모"] = res.str[5]
df["조치유형"] = df["action_cn"].apply(norm_action)

date = df["action_de_list"].fillna(df["action_de_detail"])
df["조치연도"] = (date // 10000).astype("Int64")

df.to_csv(OUT_WIDE, index=False, encoding="utf-8-sig")

# ---- 품목: product_type 과 product_group 을 '|' 기준으로 분리
split = lambda s: [x.strip() for x in str(s).split("|")]
single = df[(~df.product_type.str.contains(r"\|")) & (~df.product_group.str.contains(r"\|"))]
type2group = single.groupby("product_type")["product_group"].agg(lambda s: s.mode().iat[0]).to_dict()


def item_pairs(row):
    types, groups = split(row.product_type), split(row.product_group)
    if len(types) == len(groups):
        return list(zip(types, groups))
    return [(t, type2group.get(t, groups[0])) for t in types]


# ---- 대시보드용 long 형태
rows = []
for r in df.itertuples(index=False):
    items = item_pairs(r)
    vios = []
    if r.안전기준_위반:
        subs = [s for s in str(r.위반물질).split("; ") if s] or [UNK_SUBST]
        vios += [(T_SAFE, s) for s in subs]
    if r.안전기준_적합확인_위반:
        vios.append((T_CONF, NO_SUBST))
    if r.표시기준_위반:
        vios.append((T_LABEL, NO_SUBST))
    if not vios:
        vios = [("미분류(검토필요)", NO_SUBST)]
    for it, grp in items:
        for vt, sub in vios:
            rows.append([r.prdt_mstr_no, it, grp, vt, sub, r.조치유형, r.조치연도, r.분류신뢰도])

long_df = pd.DataFrame(rows, columns=["prdt_mstr_no", "품목", "품목군", "위반유형", "위반물질",
                                      "조치유형", "조치연도", "분류신뢰도"])
long_df.to_csv(OUT_LONG, index=False, encoding="utf-8-sig")

# ---- 요약 출력
print(f"제품 {len(df)}건 → 분류 결과")
print(df["분류신뢰도"].value_counts().to_string(), "\n")
print("안전기준 위반      :", df["안전기준_위반"].sum())
print("안전기준 적합확인  :", df["안전기준_적합확인_위반"].sum())
print("표시기준 위반      :", df["표시기준_위반"].sum())
print("조치연도 결측      :", df["조치연도"].isna().sum())
print(f"저장: {OUT_WIDE}, {OUT_LONG} (long {len(long_df)}행)")
