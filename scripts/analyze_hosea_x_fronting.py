#!/usr/bin/env python3
"""Merge the 14 Hosea CTT 1.135 files with BHSA 2021 clause atoms.

Baseline values are immutable. A separate Talstra–Park/WIVU research layer
records chapter-spanning and high-priority hierarchy proposals.
"""
from __future__ import annotations
import argparse, csv, json, re, textwrap, urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import yaml
from tf.app import use

TAG="1.135"; N0=575395; N1=576230
COUNTS={1:36,2:108,3:23,4:81,5:65,6:41,7:64,8:59,9:76,10:69,11:50,12:53,13:63,14:48}
LINE_RE=re.compile(r"^\s*HOS\s+(\d{2}),(\d{2})\b")
ROOTS={575395,575399,575431,575444,575503,575539,575562,575625,575643,575674,575708,575723,575749,575776,575795,575813,575872,575897,575912,575948,575966,575983,575998,576017,576044,576067,576076,576093,576120,576138,576153,576163,576177,576183,576188,576224}

RAW=[
("D-HOS-0001",575431,"MOTHER_OVERRIDE",575428,575430,"RESTORATION-REVERSAL-PROGRAM","PROVISIONAL","A-","FN-HOS-0001",[575429,575430],"MT 2:1 answers לא עמי with בני אל חי; no new speech formula intervenes."),
("D-HOS-0002",575444,"MOTHER_OVERRIDE",575440,575440,"DIRECTIVE-AFTER-RESTORATION-PROGRAM","PROVISIONAL","B","FN-HOS-0002",[575431],"MT 2:3 follows the restored-children program of MT 2:2 and is not a whole-book root."),
("D-HOS-0003",575539,"MOTHER_OVERRIDE",575399,575399,"NONADJACENT-PARALLEL-SYMBOLIC-ACT","PROVISIONAL","B","FN-HOS-0003",[0],"ויאמר יהוה אלי עוד reintroduces the YHWH–Hosea set and parallels the first symbolic-act opening."),
("D-HOS-0004",575643,"MOTHER_OVERRIDE",575562,575562,"PARALLEL-ADDRESSEE-INDICTMENT","PROVISIONAL","B","FN-HOS-0004",[0,575625],"שמעו/הקשיבו/האזינו renew the covenant-lawsuit speech while expanding the addressee set."),
("D-HOS-0005",575708,"ANCHOR_ONLY",None,575707,"ANTICIPATED-RESPONSE-ANCHOR","ANCHOR_ONLY","A-anchor/C-mother","FN-HOS-0005",[575707,0],"5:15 predicts seeking YHWH; 6:1 is a self-contained cohortative response, so anchor and mother are separated."),
("D-HOS-0006",575749,"ANCHOR_ONLY",None,575748,"RESTORATION-FRAME-SCOPE-ANCHOR","OPEN","C+","FN-HOS-0006",[575748,0],"בשובי שבות עמי and כרפאי לישראל are adjacent restoration frames, but their syntactic scope is unresolved."),
("D-HOS-0007",575813,"ANCHOR_ONLY",None,575812,"TRUMPET-WARNING-CONTINUATION","OPEN","C","FN-HOS-0007",[575812,0],"The trumpet imperative continues the accusation domain but may open a new directive unit."),
("D-HOS-0008",575872,"ANCHOR_ONLY",None,575871,"EXILE-ORACLE-BOOK-ANCHOR","OPEN","C","FN-HOS-0008",[575871,0],"The prohibition opens direct address and a possible speaker shift; no syntactic override is applied."),
("D-HOS-0009",575948,"ANCHOR_ONLY",None,575947,"ISRAEL-METAPHOR-BACKLINK","OPEN","B","FN-HOS-0009",[575872,575912,575947,0],"The vine evaluation continues Hosea's assessment, but its nonadjacent mother remains disputed."),
("D-HOS-0010",576017,"RETAIN_ROOT",0,576016,"DIVINE-HISTORY-REVIEW-ROOT","PROVISIONAL","B+","FN-HOS-0010",[576016],"כי נער ישראל and first-person אהבהו establish a new divine retrospective frame."),
("D-HOS-0011",576067,"MOTHER_OVERRIDE",576044,576066,"CONTINUED-DIVINE-ASSESSMENT","PROVISIONAL","B","FN-HOS-0011",[576066,0],"MT 12:1 continues the Ephraim/Israel/Judah assessment without a new speech-introduction formula."),
("D-HOS-0012",576120,"ANCHOR_ONLY",None,576119,"EPHRAIM-RETROSPECT-BACKLINK","OPEN","B","FN-HOS-0012",[576117,576067,0],"כדבר אפרים resumes the Ephraim evaluation; the precise nonadjacent mother remains open."),
("D-HOS-0013",576183,"MOTHER_OVERRIDE",576177,576182,"SAMARIA-JUDGMENT-CULMINATION","PROVISIONAL","A-","FN-HOS-0013",[576182],"14:1 directly culminates the east-wind/desiccation/plunder judgment of 13:15."),
("D-HOS-0014",575503,"RETAIN_ROOT",0,575503,"RESTORATION-RHETORICAL-RESTART","PROVISIONAL","A","FN-HOS-0014",[575466],"The second לכן reverses judgment into restoration and must not remain under the punitive לכן domain."),
("D-HOS-0015",575720,"MOTHER_OVERRIDE",575717,575717,"MOTIVATING-COMPARISON","PROVISIONAL","B","FN-HOS-0015",[575718,575710],"כשחר נכון מוצאו motivates the renewed cohortative knowing/pursuit sequence in 6:3."),
("D-HOS-0016",575723,"RETAIN_ROOT",0,575708,"DIVINE-SPEECH-RETURN","PROVISIONAL","B","FN-HOS-0016",[575708],"First-person questions and Ephraim/Judah vocatives mark YHWH's speech return after 6:1–3."),
("D-HOS-0017",575733,"SCOPE_REVIEW",None,575723,"CAUSE-SCOPE-REVIEW","OPEN","C","FN-HOS-0017",[575730,575723],"כי may ground only 6:5 or the whole 6:4–5 evaluation; baseline mother is retained."),
("D-HOS-0018",575705,"SCOPE_REVIEW",None,575703,"TEMPORAL-SCOPE-REVIEW","OPEN","C","FN-HOS-0018",[575703,575704],"The reach of עד אשר over 575706–575707 controls the link to 6:1; baseline is retained."),
]
KEYS=("id","node","action","proposed_mother","anchor","relation","status","confidence","footnote","alternatives","reason")
DECISIONS=[dict(zip(KEYS,row)) for row in RAW]

def fs(api:Any,name:str,node:int,default:Any="")->Any:
    try: value=api.Fs(name).v(node)
    except Exception: return default
    return default if value is None else value

def inode(value:Any)->int:
    if value in (None,"",0,"0"): return 0
    try:return int(float(value))
    except (TypeError,ValueError):return 0

def get(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":"hosea-hierarchy-research"})
    with urllib.request.urlopen(req,timeout=60) as res:return res.read().decode("utf-8")

def lines(text:str)->list[str]:return [x.rstrip() for x in text.splitlines() if LINE_RE.match(x)]

def htext(api:Any,words:list[int])->str:
    try:return api.T.text(words,fmt="text-orig-full").strip()
    except Exception:return "".join(str(fs(api,"g_word_utf8",w,""))+str(fs(api,"trailer_utf8",w,"")) for w in words).strip()

def tsv(path:Path,rows:list[dict[str,Any]],fields:list[str])->None:
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,delimiter="\t",fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)

def depths(rows:list[dict[str,Any]],key:str)->dict[int,int]:
    by={r["node"]:r for r in rows};cache={0:-1};active=set()
    def visit(n:int)->int:
        if n in cache:return cache[n]
        if n in active:raise ValueError(f"cycle at {n}")
        active.add(n);m=inode(by[n][key])
        if m and m not in by:raise ValueError(f"outside mother {n}->{m}")
        cache[n]=visit(m)+1;active.remove(n);return cache[n]
    for r in rows:visit(r["node"])
    return cache

def notes(by:dict[int,dict[str,Any]])->str:
    out=["# 호세아서 전권 clause-atom 하이라키 수정 각주 — Phase 2\n",
    "CTT/BHSA 초안은 보존하며 Talstra–Park/WIVU의 form-to-function 절차에 따라 별도 연구 레이어를 제안한다. PROVISIONAL은 미확정, OPEN은 경쟁 모델 유지, ANCHOR_ONLY는 통사 mother와 담화 anchor의 분리를 뜻한다.\n",
    "## 공통 원칙\n\n1. 장 번호는 통사 경계의 증거가 아니다.\n2. clause type·어순·접속/범위 표지·인용 도입을 먼저 판정한다.\n3. syntactic mother와 discourse anchor를 구별한다.\n4. 화자·참여자 이동은 통사 판정 뒤 검증한다.\n5. 변경 전 baseline은 삭제하지 않는다.\n"]
    for d in DECISIONS:
        r=by[d["node"]];base=r["baseline_mother"] or "ROOT";p=d["proposed_mother"]
        prop="유지/미적용" if p is None else ("ROOT" if p==0 else str(p));alts=", ".join("ROOT" if x==0 else str(x) for x in d["alternatives"])
        out.append(textwrap.dedent(f"""
        ## {d['footnote']} — {r['reference']} / node {d['node']}

        - **초안 mother:** `{base}`
        - **연구 조치:** `{d['action']}`
        - **제안 mother:** `{prop}`
        - **담화 anchor:** `{d['anchor'] or '없음'}`
        - **관계:** `{d['relation']}`
        - **상태/확신도:** `{d['status']}` / `{d['confidence']}`
        - **대안:** {alts or '없음'}
        - **근거:** {d['reason']}
        - **수정 설명:** 장별 root/직렬 mother를 최종값으로 간주하지 않고 표면 형식, 재귀적 내포, 반복 프레임과 참여자 연속성을 비교하였다. OPEN/ANCHOR_ONLY 항목은 syntactic mother를 바꾸지 않았다.
        """))
    return "\n".join(out)

def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--version",default="2021");p.add_argument("--out-dir",default="out/hosea-x");a=p.parse_args()
    out=Path(a.out_dir);src=out/"source_ctt";src.mkdir(parents=True,exist_ok=True)
    A=use("ETCBC/bhsa",version=a.version,silent="deep");api=A.api;F,L,T=api.F,api.L,api.T
    atoms=sorted(n for n in F.otype.s("clause_atom") if L.d(n,"word") and T.sectionFromNode(L.d(n,"word")[0])[0]=="Hosea")
    assert len(atoms)==836 and atoms==list(range(N0,N1+1))
    bychap=defaultdict(list)
    for n in atoms:bychap[int(T.sectionFromNode(L.d(n,"word")[0])[1])].append(n)
    assert {k:len(v) for k,v in bychap.items()}==COUNTS
    rows=[];iv=defaultdict(int);seq=0
    for ch in range(1,15):
        url=f"https://raw.githubusercontent.com/ETCBC/CTT/{TAG}/hosea/{ch:02d}/hosea{ch:02d}.CTT";text=get(url);(src/f"hosea{ch:02d}.CTT").write_text(text,encoding="utf-8")
        dl=lines(text);assert len(dl)==len(bychap[ch]),(ch,len(dl),len(bychap[ch]))
        for line,n in zip(dl,bychap[ch]):
            seq+=1;words=L.d(n,"word");_,tc,v=T.sectionFromNode(words[0]);m=LINE_RE.match(line);assert m and tuple(map(int,m.groups()))==(int(tc),int(v))
            iv[(ch,int(v))]+=1;clauses=L.u(n,"clause");mother=inode(fs(api,"mother",n,0))
            rows.append(dict(seq=seq,node=n,reference=f"호 {ch}:{int(v)} CA{iv[(ch,int(v))]}",chapter=ch,verse=int(v),atom_in_verse=iv[(ch,int(v))],typ=str(fs(api,"typ",n,"")),kind=str(fs(api,"kind",n,"")),code=str(fs(api,"code",n,"")),tab=str(fs(api,"tab",n,"")),domain=str(fs(api,"domain",n,"")),txt=str(fs(api,"txt",n,"")),baseline_mother=mother,baseline_root=int(mother==0),ctt_root_marker=int("[R]" in line),ctt_line=line,ctt_url=url,clause_node=clauses[0] if clauses else 0,slot_start=min(words),slot_end=max(words),hebrew=htext(api,words)))
    by={r["node"]:r for r in rows};assert len(by)==836
    for r in rows:r.update(research_mother=r["baseline_mother"],research_relation="BASELINE",decision_status="BASELINE",decision_confidence="",decision_id="",footnote_id="",discourse_anchor=0,alternatives="",changed=0)
    for n in ROOTS:
        r=by[n];r.update(research_mother=0,research_relation="LOCAL-ROOT-FIRST-PASS",decision_status="PROVISIONAL",decision_confidence="B",decision_id=f"LR-{n}",changed=int(r["baseline_mother"]!=0))
    for d in DECISIONS:
        r=by[d["node"]]
        if d["action"] in {"MOTHER_OVERRIDE","RETAIN_ROOT"}:r["research_mother"]=inode(d["proposed_mother"])
        r.update(research_relation=d["relation"],decision_status=d["status"],decision_confidence=d["confidence"],decision_id=d["id"],footnote_id=d["footnote"],discourse_anchor=inode(d["anchor"]),alternatives=",".join(map(str,d["alternatives"])),changed=int(r["research_mother"]!=r["baseline_mother"]))
    bd=depths(rows,"baseline_mother");rd=depths(rows,"research_mother")
    for r in rows:r["baseline_depth"]=bd[r["node"]];r["research_depth"]=rd[r["node"]]
    fields=["seq","node","reference","chapter","verse","atom_in_verse","typ","kind","code","tab","domain","txt","clause_node","slot_start","slot_end","hebrew","ctt_line","ctt_url","baseline_mother","baseline_root","ctt_root_marker","baseline_depth","research_mother","research_depth","research_relation","changed","decision_status","decision_confidence","decision_id","footnote_id","discourse_anchor","alternatives"]
    tsv(out/"hosea_clause_atom_master_baseline.tsv",rows,fields[:22]);tsv(out/"hosea_clause_atom_master_research.tsv",rows,fields)
    merged=["# Hosea ETCBC CTT 1.135 chapter files concatenated verbatim"]
    for ch in range(1,15):merged += [f"\n# ===== HOS CHAPTER {ch:02d} =====",(src/f"hosea{ch:02d}.CTT").read_text(encoding="utf-8").rstrip()]
    (out/"hosea_fullbook_ctt_1.135_baseline.CTT").write_text("\n".join(merged)+"\n",encoding="utf-8")
    cv=["# Hosea whole-book clause-atom research hierarchy — Phase 2","# B=baseline; R=research; A=anchor; PROVISIONAL/OPEN require review","#"]
    for r in rows:
        indent="│  "*min(r["research_depth"],12)+"└─ ";cv.append(f"HOS {r['chapter']:02d},{r['verse']:02d} CA{r['atom_in_verse']:02d} N={r['node']:06d} {r['typ']:<5} B={r['baseline_mother']:06d} R={r['research_mother']:06d} A={r['discourse_anchor']:06d} D={r['research_depth']:02d} S={r['decision_status']:<12} REL={r['research_relation'][:28]:<28} {indent}{r['hebrew']}")
    (out/"hosea_fullbook_research_hierarchy_phase2.CTT").write_text("\n".join(cv)+"\n",encoding="utf-8")
    export={"metadata":{"book":"Hosea","bhsa_version":a.version,"ctt_version":TAG,"unit":"clause_atom","row_count":836,"method":"Talstra–Park/WIVU form-to-function","status":"Phase 2 research proposal"},"local_roots_first_pass":sorted(ROOTS),"decisions":DECISIONS}
    (out/"hierarchy_decisions_phase2.yaml").write_text(yaml.safe_dump(export,allow_unicode=True,sort_keys=False),encoding="utf-8");(out/"hierarchy_revision_footnotes_phase2.md").write_text(notes(by),encoding="utf-8")
    cross=[]
    for r in rows:
        m=r["research_mother"]
        if m and by[m]["chapter"]!=r["chapter"]:cross.append(dict(node=r["node"],reference=r["reference"],mother=m,mother_reference=by[m]["reference"],relation=r["research_relation"],status=r["decision_status"],confidence=r["decision_confidence"],footnote_id=r["footnote_id"],discourse_anchor=r["discourse_anchor"]))
    tsv(out/"cross_chapter_edges_phase2.tsv",cross,["node","reference","mother","mother_reference","relation","status","confidence","footnote_id","discourse_anchor"])
    review=[dict(priority="P0" if r["footnote_id"] in {"FN-HOS-0005","FN-HOS-0006","FN-HOS-0017","FN-HOS-0018"} else "P1",node=r["node"],reference=r["reference"],status=r["decision_status"],baseline_mother=r["baseline_mother"],research_mother=r["research_mother"],anchor=r["discourse_anchor"],relation=r["research_relation"],footnote_id=r["footnote_id"]) for r in rows if r["decision_status"] in {"OPEN","ANCHOR_ONLY","PROVISIONAL"}]
    tsv(out/"research_review_queue_phase2.tsv",review,["priority","node","reference","status","baseline_mother","research_mother","anchor","relation","footnote_id"])
    val=dict(bhsa_version=a.version,ctt_version=TAG,atom_count=836,node_range=[N0,N1],contiguous_nodes=True,chapter_counts=dict(Counter(r["chapter"] for r in rows)),ctt_tf_reference_alignment=True,baseline_cycle_free=True,research_cycle_free=True,baseline_root_count=sum(r["baseline_mother"]==0 for r in rows),research_root_count=sum(r["research_mother"]==0 for r in rows),changed_mother_count=sum(r["changed"] for r in rows),cross_chapter_mother_count=len(cross),decision_status_counts=dict(Counter(r["decision_status"] for r in rows)),warning="Phase 2 applies only the encoded boundary/high-priority layer; remaining chapter-level overrides require Phase 3 import and researcher confirmation.")
    (out/"validation.json").write_text(json.dumps(val,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"README.md").write_text(f"# Hosea whole-book clause-atom hierarchy — Phase 2\n\n- CTT {TAG} chapter files preserved verbatim.\n- BHSA {a.version}: 836 clause atoms, nodes {N0}–{N1}.\n- Baseline and research mothers are separate.\n- Boundary/high-priority decisions and footnotes are included.\n\nThe authoritative table is `hosea_clause_atom_master_research.tsv`. This is a research proposal, not the final confirmed hierarchy.\n",encoding="utf-8")
    print(json.dumps(val,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
