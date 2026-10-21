import streamlit as st
import heapq
from collections import deque

st.set_page_config(page_title="ParkSmart | Intelligent Parking Agent", page_icon="🅿️", layout="wide")

# Grid map: # = blocked lane, . = road, P = parking spot, E = entrance
DEFAULT_GRID = [
    list("E....#...."),
    list(".##..#..P."),
    list("....P....#"),
    list("#..##....."),
    list("....P.#.P."),
    list("..#......."),
    list("P....#...."),
]
ROWS, COLS = len(DEFAULT_GRID), len(DEFAULT_GRID[0])
SPOTS = {
    (1, 8): {"id":"P1","fee":40,"accessible":False,"vehicle":"Car","reserved":False,"occupied":False,"availability":0.92},
    (2, 4): {"id":"P2","fee":30,"accessible":True,"vehicle":"Car","reserved":False,"occupied":False,"availability":0.86},
    (4, 4): {"id":"P3","fee":25,"accessible":False,"vehicle":"Bike","reserved":False,"occupied":False,"availability":0.70},
    (4, 8): {"id":"P4","fee":50,"accessible":True,"vehicle":"Car","reserved":True,"occupied":False,"availability":0.95},
    (6, 0): {"id":"P5","fee":20,"accessible":False,"vehicle":"Bike","reserved":False,"occupied":False,"availability":0.60},
}
ENTRANCE=(0,0)
DIRECTIONS=[(-1,0,"↑"),(1,0,"↓"),(0,-1,"←"),(0,1,"→")]

st.markdown("""
<style>
.stApp {background:linear-gradient(135deg,#f6f8fc 0%,#eef4ff 100%);}
.block-container {padding-top:1.5rem; max-width:1450px;}
.hero {background:linear-gradient(120deg,#101d42,#1d4ed8);padding:25px 30px;border-radius:20px;color:white;margin-bottom:18px;box-shadow:0 10px 30px #1e3a8a20;}
.hero h1 {color:white;margin:0;font-size:2.2rem;}
.hero p {color:#dbeafe;margin:8px 0 0 0;}
.kpi {background:white;border:1px solid #e2e8f0;padding:16px;border-radius:15px;box-shadow:0 4px 14px #0f172a08;}
.kpi-label {font-size:.85rem;color:#64748b}.kpi-value {font-size:1.7rem;font-weight:800;color:#0f172a}
.legend {display:flex;gap:12px;flex-wrap:wrap;font-size:.85rem;color:#475569;margin:8px 0 16px}
.legend span {background:white;border:1px solid #e2e8f0;border-radius:8px;padding:6px 10px}
</style>
""",unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🅿️ ParkSmart</h1><p>Intelligent Parking Search Agent · Find a suitable space and navigate using BFS, DFS or A*.</p></div>',unsafe_allow_html=True)

# Controls
with st.sidebar:
    st.header("⚙️ Search settings")
    algorithm=st.selectbox("Pathfinding algorithm",["A* Search","BFS","DFS"])
    vehicle=st.selectbox("Vehicle type",["Car","Bike"])
    accessible=st.checkbox("Require accessible parking")
    allow_reserved=st.checkbox("Allow reserved spaces",False)
    max_fee=st.slider("Maximum parking fee (₹)",0,100,60,5)
    objective=st.selectbox("Parking preference",["Balanced","Shortest distance","Lowest fee","Highest availability"])
    st.divider()
    st.subheader("🚧 Parking conditions")
    st.caption("Toggle a space to simulate live occupancy.")
    occupancy={}
    for pos,meta in SPOTS.items():
        occupancy[pos]=st.checkbox(f"{meta['id']} — {'₹'+str(meta['fee'])}",value=meta["occupied"],key=f"occ_{meta['id']}")
    blocked_input=st.text_input("Extra blocked cells (row,col)",placeholder="e.g. 2,2; 3,5")
    one_way=st.selectbox("Optional one-way rule",["None","Only move right/down","Only move left/right"])

def parse_blocked(s):
    out=set()
    try:
        for item in s.split(";"):
            if item.strip():
                r,c=map(int,item.strip().split(","))
                if 0<=r<ROWS and 0<=c<COLS: out.add((r,c))
    except Exception:
        st.sidebar.error("Use row,col pairs separated by semicolons.")
    return out

blocked=parse_blocked(blocked_input)
blocked |= {(r,c) for r in range(ROWS) for c in range(COLS) if DEFAULT_GRID[r][c]=="#"}
blocked |= {p for p,v in occupancy.items() if v}
# build directional neighbors
def neighbors(pos):
    r,c=pos
    result=[]
    for dr,dc,arrow in DIRECTIONS:
        nr,nc=r+dr,c+dc
        if not (0<=nr<ROWS and 0<=nc<COLS) or (nr,nc) in blocked: continue
        if one_way=="Only move right/down" and (dr<0 or dc<0): continue
        if one_way=="Only move left/right" and dr!=0: continue
        result.append((nr,nc))
    return result

def search(start,goal,algo):
    frontier=[]
    came={start:None}
    g={start:0}
    expanded=[]
    if algo=="A* Search":
        heapq.heappush(frontier,(abs(start[0]-goal[0])+abs(start[1]-goal[1]),0,start))
        while frontier:
            _,cost,node=heapq.heappop(frontier)
            if node in expanded: continue
            expanded.append(node)
            if node==goal: break
            for nxt in neighbors(node):
                ng=g[node]+1
                if nxt not in g or ng<g[nxt]:
                    g[nxt]=ng; came[nxt]=node
                    h=abs(nxt[0]-goal[0])+abs(nxt[1]-goal[1])
                    heapq.heappush(frontier,(ng+h,ng,nxt))
    else:
        q=deque([start]) if algo=="BFS" else [start]
        seen={start}
        while q:
            node=q.popleft() if algo=="BFS" else q.pop()
            expanded.append(node)
            if node==goal: break
            for nxt in neighbors(node):
                if nxt not in seen:
                    seen.add(nxt); came[nxt]=node; g[nxt]=g[node]+1
                    q.append(nxt)
    if goal not in came: return None,expanded,g
    path=[]; cur=goal
    while cur is not None: path.append(cur); cur=came[cur]
    return path[::-1],expanded,g

# Candidate ranking
candidates=[]
for pos,meta0 in SPOTS.items():
    meta={**meta0,"occupied":occupancy[pos]}
    if meta["occupied"] or pos in blocked or meta["fee"]>max_fee: continue
    if accessible and not meta["accessible"]: continue
    if vehicle not in (meta["vehicle"],"Car") and meta["vehicle"]!="Car": continue
    if meta["reserved"] and not allow_reserved: continue
    path,expanded,costs=search(ENTRANCE,pos,algorithm)
    if path:
        dist=len(path)-1
        if objective=="Lowest fee": score=meta["fee"]*3+dist
        elif objective=="Highest availability": score=(1-meta["availability"])*100+dist
        elif objective=="Shortest distance": score=dist
        else: score=dist+meta["fee"]*.08+(0 if meta["accessible"] else 1)
        candidates.append((score,pos,meta,path,expanded,costs))
candidates.sort(key=lambda x:x[0])
best=candidates[0] if candidates else None

# Summary metrics
total=len(SPOTS); open_count=sum(1 for p,m in SPOTS.items() if not occupancy[p] and p not in blocked)
c1,c2,c3,c4=st.columns(4)
for col,label,value in [
    (c1,"PARKING SPACES",str(total)),
    (c2,"AVAILABLE",str(open_count)),
    (c3,"ROUTE LENGTH",f"{len(best[3])-1} steps" if best else "—"),
    (c4,"SEARCH NODES",str(len(best[4])) if best else "0"),
]:
    with col: st.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>',unsafe_allow_html=True)

st.write("")
left,right=st.columns([1.35,1])
with left:
    st.subheader("🗺️ Parking lot map")
    st.caption("Grid coordinates are zero-indexed. Entrance is at (0, 0).")
    pathset=set(best[3]) if best else set()
    expandedset=set(best[4]) if best else set()
    # Build HTML grid
    html='<div style="display:grid;grid-template-columns:repeat(10,minmax(36px,1fr));gap:5px;padding:12px;background:#e2e8f0;border-radius:16px;">'
    for r in range(ROWS):
        for c in range(COLS):
            p=(r,c); ch=DEFAULT_GRID[r][c]
            if p in blocked: bg="#334155"; fg="white"; label="✕"; title="Blocked / occupied"
            elif p==ENTRANCE: bg="#2563eb"; fg="white"; label="🚪"; title="Entrance"
            elif p in SPOTS:
                m=SPOTS[p]
                if occupancy[p]: bg="#dc2626"; label="✕"; title=f"{m['id']} occupied"
                elif best and p==best[1]: bg="#16a34a"; label="P"; title=f"{m['id']} selected"
                elif m["reserved"]: bg="#a855f7"; label="R"; title=f"{m['id']} reserved"
                else: bg="#f59e0b"; label="P"; title=f"{m['id']} parking"
                fg="white"
            elif p in pathset: bg="#bfdbfe"; fg="#1e3a8a"; label="●"; title="Final route"
            elif p in expandedset: bg="#e0e7ff"; fg="#4338ca"; label="·"; title="Explored node"
            else: bg="#ffffff"; fg="#64748b"; label=""; title=f"Road ({r},{c})"
            html+=f'<div title="{title}" style="aspect-ratio:1;display:flex;align-items:center;justify-content:center;border-radius:8px;background:{bg};color:{fg};font-weight:800;border:1px solid #cbd5e1;font-size:18px;">{label}</div>'
    html+='</div>'
    st.markdown(html,unsafe_allow_html=True)
    st.markdown('<div class="legend"><span>🚪 Entrance</span><span>🟩 Selected spot</span><span>🟨 Available</span><span>🟥 Occupied / blocked</span><span>🟦 Route</span><span>🟪 Reserved</span></div>',unsafe_allow_html=True)
    if best:
        st.success(f"Recommended: {best[2]['id']} · ₹{best[2]['fee']} · {len(best[3])-1} steps from entrance")
    else:
        st.warning("No suitable space found. Try changing filters or unblocking a lane.")

with right:
    st.subheader("🎯 Recommendation")
    if best:
        score,pos,meta,path,expanded,costs=best
        a,b=st.columns(2)
        a.metric("Selected space",meta["id"])
        b.metric("Parking fee",f"₹{meta['fee']}")
        a.metric("Distance",f"{len(path)-1} grid steps")
        b.metric("Availability estimate",f"{meta['availability']*100:.0f}%")
        st.write(f"**Coordinates:** `{pos}`  ·  **Accessible:** {'Yes' if meta['accessible'] else 'No'}  ·  **Reserved:** {'Yes' if meta['reserved'] else 'No'}")
        st.markdown("**Route directions**")
        for i,p in enumerate(path):
            if i==0: step="Start at entrance"
            elif i==len(path)-1: step=f"Park at {meta['id']}"
            else:
                prev=path[i-1]
                dr=p[0]-prev[0]; dc=p[1]-prev[1]
                step={( -1,0):"Move up",(1,0):"Move down",(0,-1):"Move left",(0,1):"Move right"}.get((dr,dc),"Continue")
            st.write(f"{i}. {step} — `{p}`")
    else:
        st.write("Adjust parking preferences to get a recommendation.")

st.divider()
tab1,tab2,tab3=st.tabs(["📍 Candidate spaces","🧠 Search details","ℹ️ How it works"])
with tab1:
    if candidates:
        import pandas as pd
        rows=[]
        for score,pos,meta,path,expanded,costs in candidates:
            rows.append({"Space":meta["id"],"Grid position":str(pos),"Distance (steps)":len(path)-1,"Fee (₹)":meta["fee"],"Accessible": "Yes" if meta["accessible"] else "No","Reserved":"Yes" if meta["reserved"] else "No","Availability":f"{meta['availability']*100:.0f}%","Score":round(score,2)})
        st.dataframe(rows,use_container_width=True,hide_index=True)
    else: st.info("No spaces match your current filters.")
with tab2:
    if best:
        score,pos,meta,path,expanded,costs=best
        open_nodes=[f"{p} (g={costs.get(p,'—')})" for p in expanded]
        st.write("**Open list / expansion order**")
        st.code(" → ".join(open_nodes) if open_nodes else "Empty")
        st.write("**Closed / explored list**")
        st.code(", ".join(map(str,expanded)))
        st.write("**Path cost:**",len(path)-1)
        st.write("**Heuristic:** Manhattan distance, `h(n) = |rₙ-rg| + |cₙ-cg|`")
        st.write("**Selected parking space:**",meta["id"],"at",pos)
        st.write("**Final route:**"," → ".join(map(str,path)))
    else: st.info("Run a successful search to see search diagnostics.")
with tab3:
    st.markdown("""
    - **State space:** every road cell and parking space is a state.
    - **Actions:** move one cell up, down, left or right, respecting blocked lanes and one-way rules.
    - **BFS:** finds a shortest path when every move has equal cost.
    - **DFS:** explores deeply first; it does not guarantee the shortest route.
    - **A\*:** uses `f(n) = g(n) + h(n)` with Manhattan-distance heuristic.
    - **Constraints:** occupied/blocked spaces, reserved parking, vehicle type, accessibility and fee limit.
    - **Advanced ranking:** combines distance, fee and expected availability according to your selected preference.

    This is a demonstration with simulated parking data, not a live sensor-connected parking system.
    """)
st.caption("ParkSmart · Intelligent Parking Search Agent · Python + Streamlit")
