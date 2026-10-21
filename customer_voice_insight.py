import streamlit as st
import pandas as pd
import json, re, os, requests, time
from datetime import datetime
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities import Hasher

st.set_page_config(page_title="🔍 客户之声洞察", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.yaml")

def _load_users():
    with open(_CONFIG_PATH, encoding="utf-8") as _f:
        return yaml.load(_f, Loader=SafeLoader)

def _save_users(cfg):
    with open(_CONFIG_PATH, "w", encoding="utf-8") as _f:
        yaml.dump(cfg, _f, allow_unicode=True, sort_keys=False)

_auth_config = _load_users()

_authenticator = stauth.Authenticate(
    _auth_config["credentials"],
    _auth_config["cookie"]["name"],
    _auth_config["cookie"]["key"],
    _auth_config["cookie"]["expiry_days"],
)

_authenticator.login("main")

_auth_status = st.session_state.get("authentication_status")
_name = st.session_state.get("name", "")
_username = st.session_state.get("username", "")

if _auth_status == False:
    st.error("❌ 用户名或密码错误，请重试")
    st.stop()

if not _auth_status:
    st.markdown("""
    <div style="text-align:center;padding:80px 20px">
      <div style="font-size:64px;margin-bottom:16px">🔐</div>
      <h2 style="color:#0f172a">客户之声洞察 · 登录</h2>
      <p style="color:#64748b;margin-top:8px">请使用团队分配的账号登录后使用</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.session_state["current_user"] = _username
st.session_state["current_name"] = _name

if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("OPENAI_API_KEY", "") or os.environ.get("DASHSCOPE_API_KEY", "")
if "api_url" not in st.session_state:
    st.session_state.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
if "model" not in st.session_state:
    st.session_state.model = "qwen3.5-27b"
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.3

st.markdown("""
<style>
/* ===== 全局变量 ===== */
:root {
  --brand:#1e3a8a; --brand-light:#3b82f6; --brand-soft:#dbeafe;
  --c-green:#059669; --c-orange:#ea580c; --c-red:#dc2626;
  --c-purple:#7c3aed; --c-pink:#db2777;
  --bg:#f1f5f9; --card:#ffffff; --text:#0f172a; --text2:#475569; --text3:#94a3b8;
  --border:#e2e8f0; --border-strong:#cbd5e1;
  --shadow-sm:0 1px 2px rgba(0,0,0,0.04);
  --shadow-md:0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg:0 10px 30px rgba(0,0,0,0.12);
}
.stApp { background: var(--bg); }
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1400px; }

/* ===== 侧栏：浅色 + 顶部品牌区 ===== */
section[data-testid="stSidebar"] { background: var(--card) !important; border-right:1px solid var(--border) !important; }
section[data-testid="stSidebar"] .block-container { padding-top:0; }
.sidebar-brand {
  background: linear-gradient(135deg,#1e3a8a 0%,#1a56db 100%);
  margin:-1rem -1rem 1rem -1rem; padding:24px 20px; border-radius:0 0 20px 20px;
  box-shadow:0 4px 20px rgba(30,58,138,0.25);
}
.sidebar-brand .sb-title { font-size:20px; font-weight:800; color:#ffffff; letter-spacing:0.5px; }
.sidebar-brand .sb-sub { font-size:12px; color:#bfdbfe; margin-top:4px; }
.sidebar-brand .sb-badge {
  display:inline-block; margin-top:10px; padding:3px 10px; background:rgba(255,255,255,0.18);
  border-radius:20px; font-size:11px; color:#ffffff; font-weight:500;
}
.sidebar-section-title {
  font-size:13px; font-weight:700; color:var(--text); margin:18px 0 8px 0;
  display:flex; align-items:center; gap:6px;
}
.sidebar-section-title::after {
  content:""; flex:1; height:1px; background:var(--border); margin-left:4px;
}

/* ===== Hero 顶部横幅 ===== */
.hero {
  background: linear-gradient(135deg,#1e3a8a 0%,#1a56db 60%,#2563eb 100%);
  border-radius:20px; padding:32px 36px; color:white; margin-bottom:24px;
  box-shadow:0 12px 40px rgba(26,86,219,0.35); border:1px solid #1e40af;
  position:relative; overflow:hidden;
}
.hero::before {
  content:""; position:absolute; top:-40px; right:-40px; width:180px; height:180px;
  background:rgba(255,255,255,0.08); border-radius:50%;
}
.hero::after {
  content:""; position:absolute; bottom:-60px; right:60px; width:120px; height:120px;
  background:rgba(255,255,255,0.06); border-radius:50%;
}
.hero h1 { font-size:30px; font-weight:800; margin:0 0 6px 0; letter-spacing:0.5px; position:relative; z-index:1; }
.hero p { font-size:14px; color:#dbeafe; margin:0; position:relative; z-index:1; }
.hero .hero-stats { display:flex; gap:24px; margin-top:18px; position:relative; z-index:1; }
.hero .hero-stat { font-size:22px; font-weight:800; color:#ffffff; }
.hero .hero-stat-label { font-size:11px; color:#bfdbfe; margin-top:2px; }

/* ===== 卡片：白底 + 粗左边框 + hover ===== */
.card {
  background:var(--card); border-radius:14px; padding:18px 22px;
  border:1px solid var(--border); border-left-width:6px; margin:12px 0;
  transition: all 0.2s ease;
}
.card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.card-blue { border-left-color:var(--brand-light); }
.card-green { border-left-color:var(--c-green); }
.card-orange { border-left-color:var(--c-orange); }
.card-red { border-left-color:var(--c-red); }
.card-purple { border-left-color:var(--c-purple); }
.card-pink { border-left-color:var(--c-pink); }

/* ===== 分数圆 ===== */
.score-circle {
  display:inline-flex; align-items:center; justify-content:center;
  width:54px; height:54px; border-radius:50%;
  font-weight:700; font-size:20px; text-align:center; color:white;
  box-shadow:0 4px 12px rgba(0,0,0,0.12);
  flex-shrink:0;
}

/* ===== 对话气泡：带头像 ===== */
.bubble-wrap { display:flex; gap:10px; margin:8px 0; align-items:flex-start; }
.avatar {
  width:36px; height:36px; border-radius:50%; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-size:16px; font-weight:700;
}
.avatar-customer { background:#dbeafe; color:#1e3a8a; border:2px solid #93c5fd; }
.avatar-agent { background:#dcfce7; color:#166534; border:2px solid #86efac; }
.bubble-box { max-width:75%; }
.bubble-time { font-size:11px; color:var(--text3); margin-bottom:3px; font-weight:500; }
.bubble {
  padding:10px 16px; border-radius:16px; font-size:14px; line-height:1.6;
  color:var(--text); border:1px solid var(--border-strong);
}
.bubble-customer { background:#bfdbfe; border-color:#60a5fa; border-top-left-radius:4px; }
.bubble-agent { background:#f0fdf4; border-color:#86efac; border-top-right-radius:4px; }

/* ===== Tag 标签：实色白字 + 圆角 ===== */
.tag {
  display:inline-block; padding:4px 14px; border-radius:20px;
  font-size:12px; margin:4px 6px 4px 0; font-weight:600; color:#ffffff;
  box-shadow:0 1px 3px rgba(0,0,0,0.1);
}
.tag-red { background:var(--c-red); }
.tag-yellow { background:var(--c-orange); }
.tag-green { background:var(--c-green); }
.tag-blue { background:var(--brand); }
.tag-purple { background:var(--c-purple); }

/* ===== Tab 标签页 ===== */
.stTabs [data-baseweb="tab-list"] {
  gap:4px; background:var(--card); border-radius:14px; padding:5px;
  border:1px solid var(--border); box-shadow: var(--shadow-sm);
}
.stTabs [data-baseweb="tab"] { border-radius:10px; padding:8px 14px; color:var(--text2); font-weight:500; }
.stTabs [aria-selected="true"] {
  background:var(--brand) !important; color:#ffffff !important; font-weight:600;
  box-shadow:0 2px 8px rgba(30,58,138,0.3);
}

/* ===== 指标卡 ===== */
.metric-box {
  background:var(--card); border-radius:14px; padding:18px 22px;
  text-align:center; border:1px solid var(--border); box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}
.metric-box:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.metric-box .val { font-size:30px; font-weight:800; color:var(--text); line-height:1.2; }
.metric-box .lbl { font-size:12px; color:var(--text2); margin-top:4px; font-weight:500; }

/* ===== 按钮美化 ===== */
.stButton > button {
  border-radius:10px !important; font-weight:600 !important;
  transition: all 0.15s ease; border:none !important;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
.stButton > button:active { transform: translateY(0); }

/* ===== 进度条美化 ===== */
.stProgress > div > div { background: linear-gradient(90deg,#1e3a8a,#3b82f6) !important; }

/* ===== Streamlit 原生组件微调 ===== */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
  border-radius:8px !important; border-color:var(--border-strong) !important;
  transition: border-color 0.15s ease;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox > div > div:hover {
  border-color: var(--brand-light) !important; box-shadow: 0 0 0 2px rgba(59,130,246,0.15) !important;
}
.stSlider > div > div > div > div { background: var(--brand) !important; }

/* ===== Alert 美化 ===== */
div[data-testid="stAlert"] { border-radius:10px !important; }

/* ===== 全局文字 ===== */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
  color:var(--text) !important; font-weight:700 !important;
}
hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)

def call_llm(system_prompt, user_prompt, temperature=None):
    if temperature is None:
        temperature = st.session_state.get("temperature", 0.3)
    api_key = st.session_state.get("api_key", "")
    api_url = st.session_state.get("api_url", "")
    model = st.session_state.get("model", "qwen3.5-27b")
    if not api_key:
        st.error("请先在左侧栏填写 API Key ！")
        return None
    headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
    
    is_dashscope_native = "dashscope.aliyuncs.com/api/v1" in api_url and "compatible-mode" not in api_url
    
    if is_dashscope_native:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        payload = {
            "model": model,
            "input": {"messages": messages},
            "parameters": {"temperature": temperature, "result_format": "message"}
        }
    else:
        payload = {"model": model, "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ], "temperature": temperature}
    
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=(10, 180))
            if resp.status_code == 200:
                data = resp.json()
                if is_dashscope_native:
                    return data["output"]["choices"][0]["message"]["content"]
                else:
                    return data["choices"][0]["message"]["content"]
            elif resp.status_code in (429, 500, 502, 503, 504):
                wait = min(4 ** attempt, 30)
                st.warning(f"服务临时不可用 ({resp.status_code})，{wait}秒后第{attempt+1}次重试...")
                time.sleep(wait)
            else:
                st.error(f"API 错误: {resp.status_code} {resp.text[:200]}")
                return None
        except requests.exceptions.ReadTimeout:
            wait = min(4 ** attempt, 30)
            st.warning(f"响应超时，{wait}秒后第{attempt+1}次重试...")
            time.sleep(wait)
        except requests.exceptions.ConnectionError:
            wait = min(4 ** attempt, 30)
            st.warning(f"连接失败，{wait}秒后第{attempt+1}次重试...")
            time.sleep(wait)
        except Exception as e:
            st.error(f"未知错误: {e}")
            return None
    st.error("多次重试后仍然失败，请检查网络或稍后再试")
    return None

def call_llm_json(system_prompt, user_prompt, temperature=None):
    raw = call_llm(system_prompt, user_prompt, temperature)
    if not raw:
        return None
    cleaned = re.sub(r"^```json\s*", "", raw)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", cleaned)
        if m:
            try: return json.loads(m.group())
            except: pass
        st.error(f"JSON 解析失败: {raw[:200]}")
        return None

SAMPLE_CONVERSATIONS = {
    "零售客户A · 理财咨询": [
        {"role":"客户","time":"2026-10-03 09:15:02","content":"你好，我想问问你们行最近有什么好的理财产品吗？"},
        {"role":"坐席","time":"2026-10-03 09:15:35","content":"您好！感谢咨询。请问您之前买过我行理财吗？我根据您的风险偏好推荐。"},
        {"role":"客户","time":"2026-10-03 09:16:10","content":"买过一些稳健型的。手上大概有50万闲钱，之前那个年化才2.8%太低了。"},
        {"role":"坐席","time":"2026-10-03 09:17:45","content":"好的！我行最新\"智选赢\"系列，90天封闭年化3.6%，180天4.0%，都是R2稳健级。给您发个说明书参考？"},
        {"role":"客户","time":"2026-10-03 09:18:30","content":"3.6%和4.0%比之前好，但有没有灵活点的？我可能随时要用钱。"},
        {"role":"坐席","time":"2026-10-03 09:19:12","content":"有的！\"随e宝\"货币增强，T+1到账近7日年化2.3%。建议做组合——一部分放随e宝当流动资金，一部分买智选赢锁收益。"},
        {"role":"客户","time":"2026-10-03 09:20:00","content":"你这个建议挺合理的。对了，我之前在工行买的类似产品收益好像比你们高点？"},
        {"role":"坐席","time":"2026-10-03 09:21:30","content":"感谢反馈！不同银行各有优势，我行赎回速度最快，而且您是VIP客户额外享0.1%收益加成。要不帮您约个理财经理详细聊？"},
        {"role":"客户","time":"2026-10-03 09:22:15","content":"好啊，约明天下午吧。"},
        {"role":"坐席","time":"2026-10-03 09:22:45","content":"已帮您约明天下午2点李经理，她会提前10分钟确认。稍后发您产品资料。还有其他问题吗？"},
        {"role":"客户","time":"2026-10-03 09:23:00","content":"没有了谢谢！你们服务挺好的，比之前专业多了。"},
        {"role":"坐席","time":"2026-10-03 09:23:20","content":"感谢认可！祝您生活愉快，再见！"},
    ],
    "客户B · 信用卡投诉": [
        {"role":"客户","time":"2026-10-03 10:05:00","content":"喂！我要投诉！我申请信用卡都一个月了还没下来！"},
        {"role":"坐席","time":"2026-10-03 10:05:20","content":"非常抱歉给您带来不便。能告诉我手机号吗？我帮您查一下。"},
        {"role":"客户","time":"2026-10-03 10:05:45","content":"138XXXX6789。我同事和我一起申请的人家上周就拿到了，你们这是歧视吗？"},
        {"role":"坐席","time":"2026-10-03 10:06:30","content":"绝对没有这种情况。查了一下，您的资料上周到卡中心了，但工作证明需要补公章扫描件所以暂时搁置了。"},
        {"role":"客户","time":"2026-10-03 10:07:20","content":"公章扫描件？没人通知我啊！我等了一个月才说缺材料？"},
        {"role":"坐席","time":"2026-10-03 10:08:00","content":"非常抱歉！系统9月25日确实发过短信，可能被您屏蔽了。我马上重新发链接，您今天传一下我帮您加急，争取这周办好可以吗？"},
        {"role":"客户","time":"2026-10-03 10:08:45","content":"行吧。链接发过来我下午传。对了你们效率真的有问题，上次贷款也等了好久，每次都要我主动问。"},
        {"role":"坐席","time":"2026-10-03 10:09:30","content":"您说得对，我们会反馈改进。链接已发您，传完可以直接回复我，我帮您盯着进度。"},
        {"role":"客户","time":"2026-10-03 10:10:00","content":"暂时没了。希望这次能快点。"},
    ],
    "客户C · 经营贷需求": [
        {"role":"客户","time":"2026-10-03 14:20:00","content":"你好，我想问一下经营贷怎么申请？"},
        {"role":"坐席","time":"2026-10-03 14:20:15","content":"您好！请问是个体还是有限公司？经营多久了？"},
        {"role":"客户","time":"2026-10-03 14:20:40","content":"有限公司，电子元器件批发，快4年了。"},
        {"role":"坐席","time":"2026-10-03 14:21:00","content":"明白了。我行\"商e贷\"最高500万，年化3.85%，线上可申请。您大概需要多少？主要用途？"},
        {"role":"客户","time":"2026-10-03 14:21:30","content":"大概200万，年底要备货，供应商催得紧。之前在你们行开的基本户流水应该挺好。"},
        {"role":"坐席","time":"2026-10-03 14:22:00","content":"200万备货非常适合。您作为老客户征信没问题的话审批很快。我给您发入口，在线填基本信息，系统预审批当天就能出结果。"},
        {"role":"客户","time":"2026-10-03 14:22:30","content":"这么快？太好了！能不能帮我对接客户经理？有些细节比如担保方式，我没抵押物怎么办？"},
        {"role":"坐席","time":"2026-10-03 14:23:10","content":"没问题！我行普惠金融团队针对轻资产有信用贷方案，基于流水和纳税就能批。已帮您约明天上午10点张经理，他是专家。"},
        {"role":"客户","time":"2026-10-03 14:23:45","content":"好的明天准时到！谢谢！"},
        {"role":"坐席","time":"2026-10-03 14:24:00","content":"不客气！明天见，祝您生意兴隆！"},
    ],
}

QUALITY_SYSTEM = """你是银行客户服务质检专家。从四个维度专业评分（0-100），返回严格JSON：
{
    "礼貌度":数字, "专业度":数字, "合规性":数字, "问题解决率":数字,
    "问题项":[{"内容":"具体问题","等级":"red|yellow"}],
    "亮点项":[{"内容":"具体亮点","等级":"green"}]
}
评分标准：礼貌度(问候/告别/文明用语/同理心)、专业度(产品知识准确/主动建议)、合规性(不泄密/不违规承诺)、解决率(客户问题是否闭环)"""

KNOWLEDGE_SYSTEM = """你是银行业务知识萃取专家。从对话中提炼可复用知识，返回严格JSON数组：
[{"类型":"产品知识|异议处理|服务规范|最佳实践|客户洞察", "内容":"具体可复用", "复用性":"极高|高|中|低"}]"""

LEAD_SYSTEM = """你是银行营销线索挖掘专家。从服务对话中发现被动销售机会，返回严格JSON数组：
[{"客户画像":"特征描述","意向产品":"具体产品","意向等级":"⭐1-5星","跟进动作":"具体行动","话术建议":"参考要点"}]"""

BREAKPOINT_SYSTEM = """你是银行服务流程诊断专家。找出流程断点和瓶颈，返回严格JSON数组：
[{"断点位置":"环节","问题描述":"发生了什么","根因分析":"根本原因","影响程度":"🔴高|🟡中|🟢低","优化建议":"具体措施"}]"""

DEMAND_SYSTEM = """你是银行客户需求分析师。挖掘客户产品/服务/体验需求，返回严格JSON数组：
[{"需求类型":"产品需求|服务需求|体验需求","需求描述":"具体内容","客户层级":"全量|普通|VIP|小微企业主","需求频次":"高频|中频|低频","优先级":"P0|P1|P2"}]"""

RISK_SYSTEM = """你是银行舆情风险监测专家。分析情绪风险，返回严格JSON：
{
    "情绪等级":"🔴高危|🟡中危|🟢安全",
    "情绪关键词命中":["负面词汇"],
    "风险词汇":["监管/法律相关"],
    "建议动作":"应对措施",
    "情绪走势":[{"轮次":1,"说话方":"客户","情绪分":85}]
}
情绪分0-100，越低越差。"""

def conv_to_text(conv):
    return "\n".join(f"[{t['time']}] {t['role']}：{t['content']}" for t in conv)

def score_circle(score):
    c = "#10b981" if score >= 90 else "#3b82f6" if score >= 75 else "#f59e0b" if score >= 60 else "#ef4444"
    return f'<span class="score-circle" style="background:{c}">{score}</span>'

def tag(txt, level="blue"):
    return f'<span class="tag tag-{level}">{txt}</span>'

AGENTS_BATCH = [
    ("质检", QUALITY_SYSTEM),
    ("知识", KNOWLEDGE_SYSTEM),
    ("线索", LEAD_SYSTEM),
    ("断点", BREAKPOINT_SYSTEM),
    ("需求", DEMAND_SYSTEM),
    ("风险", RISK_SYSTEM),
]

def parse_conversation_df(df):
    rm = {"角色":"role","role":"role","说话方":"role",
          "时间":"time","time":"time","timestamp":"time","时间戳":"time",
          "内容":"content","content":"content","对话内容":"content"}
    cm = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        orig_rm = {"角色":"role","时间":"time","内容":"content"}
        if c.strip() in orig_rm: cm[orig_rm[c.strip()]] = c
        elif cl in rm: cm[rm[cl]] = c
    if {"role","time","content"} - set(cm.keys()):
        return None
    return [{"role":str(r[cm["role"]]).strip(),
             "time":str(r[cm["time"]]).strip(),
             "content":str(r[cm["content"]]).strip()} for _,r in df.iterrows()]

def batch_analyze(convs_dict, progress_cb=None):
    all_results = []
    total = len(convs_dict)
    for idx, (name, conv) in enumerate(convs_dict.items()):
        conv_text = conv_to_text(conv)
        one = {"名称": name, "对话": conv, "分析": {}}
        for aname, sys_prompt in AGENTS_BATCH:
            one["分析"][aname] = call_llm_json(sys_prompt, conv_text)
        all_results.append(one)
        if progress_cb:
            progress_cb((idx + 1) / total, name)
    return all_results

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="sb-title">🧠 客户之声洞察</div>
      <div class="sb-sub">大模型智能体平台 · v3.1</div>
      <span class="sb-badge">Powered by Qwen3.5-27B</span>
    </div>
    """, unsafe_allow_html=True)

    _cur_name = st.session_state.get("current_name", "")
    _cur_user = st.session_state.get("current_user", "")
    st.markdown(
        f"""<div style="background:#f1f5f9;border-radius:10px;padding:10px 14px;margin-bottom:14px;
              border:1px solid #e2e8f0;display:flex;align-items:center;gap:10px">
              <div style="width:32px;height:32px;background:#1e3a8a;color:#fff;border-radius:50%;
                   display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px">
              {_cur_name[:1] if _cur_name else "U"}</div>
              <div style="flex:1">
                <div style="font-weight:600;color:#0f172a;font-size:13px">{_cur_name}</div>
                <div style="font-size:11px;color:#94a3b8">@{_cur_user}</div>
              </div>
        </div>""", unsafe_allow_html=True)
    _authenticator.logout("🚪 退出登录", "sidebar")

    if _username == "admin":
        with st.expander("👥 用户管理 (Admin)", expanded=False):
            st.caption("当前账号列表")
            _cfg_now = _load_users()
            _users_now = _cfg_now["credentials"]["usernames"]
            for _u, _info in list(_users_now.items()):
                _is_me = _u == _username
                _cols = st.columns([3, 1])
                with _cols[0]:
                    st.markdown(f"**{_info['name']}** `@{_u}`  <span style='color:#94a3b8;font-size:11px'>{_info['email']}</span>" + (" ✅" if _is_me else ""), unsafe_allow_html=True)
                with _cols[1]:
                    if not _is_me and st.button("🗑️", key=f"delu_{_u}", help="删除此用户"):
                        del _users_now[_u]
                        _save_users(_cfg_now)
                        st.success(f"已删除 @{_u}")
                        time.sleep(1)
                        st.rerun()

            st.divider()
            st.markdown("**➕ 添加新用户**")
            _new_user = st.text_input("用户名 (英文)", key="nu_user", placeholder="zhangsan")
            _new_name = st.text_input("姓名", key="nu_name", placeholder="张三")
            _new_email = st.text_input("邮箱", key="nu_email", placeholder="zhangsan@company.com")
            _new_pwd = st.text_input("初始密码", key="nu_pwd", type="password", placeholder="至少6位")
            if st.button("✅ 创建用户", type="primary", use_container_width=True, key="btn_add_user"):
                if not all([_new_user, _new_name, _new_email, _new_pwd]):
                    st.error("所有字段必填")
                elif _new_user in _users_now:
                    st.error(f"用户名 @{_new_user} 已存在")
                elif len(_new_pwd) < 6:
                    st.error("密码至少 6 位")
                else:
                    _hashed = Hasher.hash_list([_new_pwd])
                    _users_now[_new_user] = {
                        "email": _new_email,
                        "name": _new_name,
                        "password": _hashed[0],
                    }
                    _save_users(_cfg_now)
                    st.success(f"✅ 用户 @{_new_user} 创建成功！密码已安全哈希存储。")
                    time.sleep(1)
                    st.rerun()

    st.markdown('<div class="sidebar-section-title">🔑 API 配置</div>', unsafe_allow_html=True)
    
    provider = st.selectbox("服务提供商", [
        "阿里云 DashScope (兼容模式)",
        "阿里云 DashScope (原生API)",
        "OpenAI",
        "本地/其他 (兼容OpenAI协议)",
    ], index=0, label_visibility="collapsed")
    
    default_urls = {
        "阿里云 DashScope (兼容模式)": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "阿里云 DashScope (原生API)": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "OpenAI": "https://api.openai.com/v1/chat/completions",
        "本地/其他 (兼容OpenAI协议)": st.session_state.get("api_url", "http://localhost:8000/v1/chat/completions"),
    }
    if provider != st.session_state.get("_last_provider"):
        st.session_state.api_url = default_urls.get(provider, st.session_state.api_url)
        st.session_state._last_provider = provider
    st.text_input("Endpoint", key="api_url", label_visibility="collapsed")
    st.text_input("API Key", type="password", key="api_key", placeholder="sk-... 粘贴你的API Key", label_visibility="collapsed")
    st.text_input("Model", key="model", label_visibility="collapsed")
    st.slider("Temperature", 0.0, 1.0, 0.3, 0.1, key="temperature")
    
    if st.button("🧪 测试连接", use_container_width=True, type="secondary"):
        if not st.session_state.api_key.strip():
            st.error("请先填写 API Key")
        else:
            with st.spinner("测试连接中..."):
                ok = call_llm("你是助手。", "回复：连接成功", temperature=0.1)
                if ok: st.success("✅ 连接成功！")
                else: st.error("❌ 连接失败，请检查配置")
    
    st.divider()
    
    st.markdown('<div class="sidebar-section-title">📥 数据输入</div>', unsafe_allow_html=True)
    input_mode = st.radio("", [
        "🎯 预设样本",
        "📝 粘贴文本",
        "✍️ 逐条手动录入",
        "📂 Excel/CSV 导入",
        "📊 批量看板 (多样本)",
    ], index=0, label_visibility="collapsed")
    st.session_state.input_mode_raw = input_mode
    
    conversation = None
    if "预设样本" in input_mode:
        selected = st.selectbox("选择样本", list(SAMPLE_CONVERSATIONS.keys()))
        conversation = SAMPLE_CONVERSATIONS[selected]
    elif "粘贴文本" in input_mode:
        raw = st.text_area("每行：角色|时间|内容", "客户|2026-10-03 09:15|你好我想问问理财\n坐席|2026-10-03 09:15:35|您好请问之前买过吗？", height=120)
        if raw.strip():
            conversation = []
            for line in raw.strip().split("\n"):
                parts = line.split("|")
                if len(parts) >= 3:
                    conversation.append({"role":parts[0].strip(),"time":parts[1].strip(),"content":parts[2].strip()})
    elif "逐条" in input_mode:
        if "manual_conv" not in st.session_state: st.session_state.manual_conv = []
        if st.session_state.get("_clear_m_content"):
            st.session_state.m_content = ""
            st.session_state._clear_m_content = False
        
        st.caption("👇 选择角色 → 输入内容 → 点添加。已录入内容在右侧主界面预览")
        
        role = st.selectbox("角色", ["客户", "坐席"], key="m_role", label_visibility="collapsed")
        ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts = st.text_input("时间", value=ts_now, key="m_time", label_visibility="collapsed")
        content = st.text_area("对话内容", key="m_content", placeholder="输入对话...", height=68, label_visibility="collapsed")
        
        col_add, col_swap, col_clr = st.columns([3, 1, 1])
        with col_add:
            if st.button("➕ 添加", key="btn_add", type="primary", use_container_width=True):
                if content.strip():
                    st.session_state.manual_conv.append({"role": role, "time": ts, "content": content.strip()})
                    st.session_state._clear_m_content = True
                    st.rerun()
        with col_swap:
            if st.button("🔄", key="btn_swap", help="交换角色", use_container_width=True):
                st.session_state.m_role = "坐席" if st.session_state.m_role == "客户" else "客户"
                st.rerun()
        with col_clr:
            if st.button("🗑️", key="btn_clr", help="清空全部", use_container_width=True):
                st.session_state.manual_conv = []
                st.rerun()
        
        st.metric("已录入", f"{len(st.session_state.manual_conv)} 条")
        conversation = st.session_state.manual_conv if st.session_state.manual_conv else None
    elif "导入" in input_mode:
        st.caption("支持 .xlsx / .csv，列名：角色 / 时间 / 内容")
        uploaded = st.file_uploader("选择文件", type=["xlsx","csv"], label_visibility="collapsed")
        if uploaded:
            try:
                df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
                rm = {"角色":"role","role":"role","说话方":"role","时间":"time","time":"time","timestamp":"time","时间戳":"time","内容":"content","content":"content","对话内容":"content"}
                cm = {}
                for c in df.columns:
                    cl = str(c).strip().lower()
                    orig_rm = {"角色":"role","时间":"time","内容":"content"}
                    if c.strip() in orig_rm: cm[orig_rm[c.strip()]] = c
                    elif cl in rm: cm[rm[cl]] = c
                if {"role","time","content"} - set(cm.keys()):
                    st.error("列名识别失败！检测到：%s" % list(df.columns))
                else:
                    conversation = [{"role":str(r[cm["role"]]).strip(),"time":str(r[cm["time"]]).strip(),"content":str(r[cm["content"]]).strip()} for _,r in df.iterrows()]
                    st.success(f"✅ 导入 {len(conversation)} 条")
            except Exception as e:
                st.error(f"解析失败: {e}")
        with st.expander("下载模板"):
            tpl = pd.DataFrame({"角色":["客户","坐席"],"时间":["2026-10-03 09:15","2026-10-03 09:15:35"],"内容":["你好我想问问理财","您好请问之前买过吗？"]})
            st.dataframe(tpl, hide_index=True, use_container_width=True)
            st.download_button("⬇️ CSV模板", tpl.to_csv(index=False).encode("utf-8-sig"), "对话导入模板.csv", "text/csv", use_container_width=True)
    else:
        conversation = None
        batch_convs = {}

        st.caption("👇 选择预设样本 或 上传多份对话文件")

        batch_samples = st.multiselect(
            "预设样本（可多选）",
            list(SAMPLE_CONVERSATIONS.keys()),
            default=list(SAMPLE_CONVERSATIONS.keys()),
            label_visibility="collapsed",
            key="batch_samples"
        )
        for s in batch_samples:
            batch_convs[f"预设·{s}"] = SAMPLE_CONVERSATIONS[s]

        st.markdown('<div style="margin:6px 0"></div>', unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "📂 上传对话文件（可多选，每个文件=一条对话）",
            type=["xlsx", "csv"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="batch_uploads"
        )
        if uploaded_files:
            for uf in uploaded_files:
                try:
                    df = pd.read_csv(uf) if uf.name.endswith(".csv") else pd.read_excel(uf)
                    parsed = parse_conversation_df(df)
                    if parsed:
                        batch_convs[f"文件·{uf.name}"] = parsed
                except Exception:
                    pass

        if batch_convs:
            st.success(f"✅ 已准备 {len(batch_convs)} 条对话")
        else:
            st.info("请选择样本或上传文件")

        st.session_state.batch_convs = batch_convs if batch_convs else None
    
    st.divider()
    if conversation: st.metric("当前对话", f"{len(conversation)} 条")
    st.caption(f"模型: {st.session_state.get('model','-')}")
    st.caption("API: " + ("🟢 已配置" if st.session_state.get("api_key") else "🔴 未配置"))

st.markdown("""
<div class="hero">
  <h1>🧠 客户之声洞察</h1>
  <p>多智能体协同 · 让每一次客户交互都产生洞察</p>
  <div class="hero-stats">
    <div><div class="hero-stat">6</div><div class="hero-stat-label">智能体</div></div>
    <div><div class="hero-stat">100%</div><div class="hero-stat-label">质检覆盖</div></div>
    <div><div class="hero-stat">24/7</div><div class="hero-stat-label">实时分析</div></div>
    <div><div class="hero-stat">60%</div><div class="hero-stat-label">效率提升</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.get("input_mode_raw", "").startswith("✍️") and st.session_state.get("manual_conv"):
    st.markdown("### 📝 逐条录入预览")
    head_col1, head_col2, head_col3 = st.columns([4, 1, 1])
    with head_col1:
        st.caption(f"共 {len(st.session_state.manual_conv)} 条对话，可单条删除或整体导出")
    with head_col2:
        df_m = pd.DataFrame(st.session_state.manual_conv)
        st.download_button("📥 导出CSV", df_m.to_csv(index=False).encode("utf-8-sig"),
                          "手工对话记录.csv", "text/csv", use_container_width=True, key="dl_manual")
    with head_col3:
        if st.button("✨ 清空全部", use_container_width=True, key="clr_manual_main"):
            st.session_state.manual_conv = []
            st.rerun()
    
    for i, t in enumerate(st.session_state.manual_conv):
        is_c = t["role"] == "客户"
        av_cls = "avatar-customer" if is_c else "avatar-agent"
        bb_cls = "bubble-customer" if is_c else "bubble-agent"
        ic = "👤" if is_c else "🎧"
        align = "" if is_c else "flex-direction:row-reverse;"
        txt_align = "text-align:right;" if is_c else ""
        
        row = st.columns([1, 10, 1])
        with row[0]:
            st.markdown(f'<div class="avatar {av_cls}" style="width:32px;height:32px;font-size:14px;margin-top:4px">{ic}</div>', unsafe_allow_html=True)
        with row[1]:
            st.markdown(
                f'<div style="{txt_align}">'
                f'<div class="bubble-time">{t["role"]} · {t["time"]}</div>'
                f'<div class="bubble {bb_cls}">{t["content"]}</div>'
                f'</div>', unsafe_allow_html=True)
        with row[2]:
            if st.button("🗑️", key=f"delm_{i}", help="删除此条"):
                st.session_state.manual_conv.pop(i)
                st.rerun()
    
    st.divider()

if conversation is not None:
    is_manual_mode = st.session_state.get("input_mode_raw", "").startswith("✍️")
    if not is_manual_mode:
        st.markdown("### 💬 原始对话")
        for t in conversation:
            is_customer = t["role"] == "客户"
            avatar_cls = "avatar-customer" if is_customer else "avatar-agent"
            bubble_cls = "bubble-customer" if is_customer else "bubble-agent"
            icon = "👤" if is_customer else "🎧"
            wrap_align = "" if is_customer else "flex-direction:row-reverse;"
            bubble_align = "text-align:right;" if is_customer else ""
            st.markdown(f'''
            <div class="bubble-wrap" style="{wrap_align}">
              <div class="avatar {avatar_cls}">{icon}</div>
              <div class="bubble-box" style="{bubble_align}">
                <div class="bubble-time">{t["role"]} · {t["time"]}</div>
                <div class="bubble {bubble_cls}">{t["content"]}</div>
              </div>
            </div>
            ''', unsafe_allow_html=True)
    
    conv_text = conv_to_text(conversation)
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🚀 一键全分析",
        "📋 质检分析",
        "📚 知识萃取",
        "🎯 营销线索",
        "🔗 服务断点",
        "💡 需求收集",
        "⚠️ 舆情监测",
    ])
    
    with tab1:
        st.markdown("### 🚀 一键运行全部六大智能体")
        run_all = st.button("⚡ 运行全部智能体分析", type="primary", use_container_width=True)
        if run_all:
            results = {}
            agents = [("质检", QUALITY_SYSTEM), ("知识", KNOWLEDGE_SYSTEM), ("线索", LEAD_SYSTEM),
                      ("断点", BREAKPOINT_SYSTEM), ("需求", DEMAND_SYSTEM), ("风险", RISK_SYSTEM)]
            progress = st.progress(0)
            for i, (name, sys_prompt) in enumerate(agents):
                with st.spinner(f"🤖 【{name}分析】大模型推理中..."):
                    results[name] = call_llm_json(sys_prompt, conv_text)
                progress.progress((i+1)/len(agents))
            progress.empty()
            
            a1, a2, a3, a4, a5, a6 = st.columns(6)
            q = results.get("质检") or {}
            ov = round((q.get("礼貌度",0)+q.get("专业度",0)+q.get("合规性",0)+q.get("问题解决率",0))/4) if q else 0
            a1.markdown(f'<div class="metric-box"><div class="val">{ov}</div><div class="lbl">📋 综合质检分</div></div>', unsafe_allow_html=True)
            a2.markdown(f'<div class="metric-box"><div class="val">{len(results.get("知识") or [])}</div><div class="lbl">📚 知识条目</div></div>', unsafe_allow_html=True)
            a3.markdown(f'<div class="metric-box"><div class="val">{len(results.get("线索") or [])}</div><div class="lbl">🎯 营销线索</div></div>', unsafe_allow_html=True)
            a4.markdown(f'<div class="metric-box"><div class="val">{len(results.get("断点") or [])}</div><div class="lbl">🔗 服务断点</div></div>', unsafe_allow_html=True)
            a5.markdown(f'<div class="metric-box"><div class="val">{len(results.get("需求") or [])}</div><div class="lbl">💡 客户需求</div></div>', unsafe_allow_html=True)
            lvl = (results.get("风险") or {}).get("情绪等级", "-")
            risk_color = "#ef4444" if "高危" in lvl else "#f59e0b" if "中危" in lvl else "#10b981"
            a6.markdown(f'<div class="metric-box"><div class="val" style="color:{risk_color}">{lvl}</div><div class="lbl">⚠️ 风险等级</div></div>', unsafe_allow_html=True)
            
            with st.expander("📋 质检分析详情", expanded=True):
                if q:
                    c1,c2,c3,c4,c5 = st.columns(5)
                    c1.markdown(score_circle(q.get("礼貌度",0))+" 礼貌度", unsafe_allow_html=True)
                    c2.markdown(score_circle(q.get("专业度",0))+" 专业度", unsafe_allow_html=True)
                    c3.markdown(score_circle(q.get("合规性",0))+" 合规性", unsafe_allow_html=True)
                    c4.markdown(score_circle(q.get("问题解决率",0))+" 解决率", unsafe_allow_html=True)
                    c5.markdown(f"**综合 {ov} 分**")
                    if q.get("问题项"):
                        st.markdown("**⚠️ 待改进**")
                        for it in q["问题项"]: st.markdown(tag(it["内容"], it.get("等级","yellow")), unsafe_allow_html=True)
                    if q.get("亮点项"):
                        st.markdown("**✨ 亮点**")
                        for hl in q["亮点项"]: st.markdown(tag(hl["内容"], "green"), unsafe_allow_html=True)
            
            with st.expander("📚 知识萃取 / 🎯 营销线索 / 🔗 服务断点 / 💡 需求收集", expanded=False):
                col_k, col_l = st.columns(2)
                with col_k:
                    st.markdown("### 📚 知识萃取")
                    for k in (results.get("知识") or []):
                        rc = {"极高":"red","高":"yellow","中":"blue","低":"green"}.get(k.get("复用性","中"),"blue")
                        st.markdown(f'<div class="card card-green"><strong>{k.get("类型","")}</strong> {tag("复用:"+k.get("复用性",""),rc)}<div style="margin-top:6px">{k.get("内容","")}</div></div>', unsafe_allow_html=True)
                with col_l:
                    st.markdown("### 🎯 营销线索")
                    for l in (results.get("线索") or []):
                        st.markdown(f'<div class="card card-orange"><strong>{l.get("意向产品","")}</strong> {l.get("意向等级","")}<div>👤 {l.get("客户画像","")}</div><div>📅 {l.get("跟进动作","")}</div><div>💬 {l.get("话术建议","")}</div></div>', unsafe_allow_html=True)
                
                st.markdown("### 🔗 服务断点")
                for bp in (results.get("断点") or []):
                    rc = "red" if "高" in bp.get("影响程度","") else "yellow" if "中" in bp.get("影响程度","") else "green"
                    st.markdown(f'<div class="card card-red"><strong>📍 {bp.get("断点位置","")}</strong> {tag(bp.get("影响程度",""),rc)}<div>问题：{bp.get("问题描述","")}</div><div>根因：{bp.get("根因分析","")}</div><div>💡 {bp.get("优化建议","")}</div></div>', unsafe_allow_html=True)
                
                st.markdown("### 💡 客户需求")
                dlist = results.get("需求") or []
                if dlist:
                    st.dataframe(pd.DataFrame(dlist), use_container_width=True, hide_index=True)
            
            with st.expander("⚠️ 舆情监测", expanded=True):
                r = results.get("风险") or {}
                lvl = r.get("情绪等级","-")
                c = "#ef4444" if "高危" in lvl else "#f59e0b" if "中危" in lvl else "#10b981"
                col1, col2 = st.columns([1,2])
                with col1:
                    st.markdown(f'<div class="card card-pink" style="text-align:center"><div style="font-size:32px;font-weight:800;color:{c}">{lvl}</div><div style="margin-top:8px">💡 {r.get("建议动作","-")}</div></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown("**情绪关键词**: "+" ".join(tag(kw,"yellow") for kw in r.get("情绪关键词命中",[])), unsafe_allow_html=True)
                    st.markdown("**风险词汇**: "+" ".join(tag(kw,"red") for kw in r.get("风险词汇",[])), unsafe_allow_html=True)
                if r.get("情绪走势"):
                    st.markdown("**📈 情绪走势**")
                    st.line_chart(pd.DataFrame(r["情绪走势"]).set_index("轮次")["情绪分"], height=220)
    
    def make_agent_tab(tab_name, sys_prompt, label, color_cls, color_tag):
        with tab_name:
            st.markdown(f"### {label}智能体")
            if st.button(f"🚀 运行 {label}分析", type="primary", use_container_width=True, key=f"btn_{label}"):
                with st.spinner(f"大模型分析中..."):
                    res = call_llm_json(sys_prompt, conv_text)
                if res: st.session_state[f"res_{label}"] = res
            res = st.session_state.get(f"res_{label}")
            if res:
                if isinstance(res, dict) and "礼貌度" in res:
                    c1,c2,c3,c4,c5 = st.columns(5)
                    c1.markdown(score_circle(res["礼貌度"])+" 礼貌度", unsafe_allow_html=True)
                    c2.markdown(score_circle(res["专业度"])+" 专业度", unsafe_allow_html=True)
                    c3.markdown(score_circle(res["合规性"])+" 合规性", unsafe_allow_html=True)
                    c4.markdown(score_circle(res["问题解决率"])+" 解决率", unsafe_allow_html=True)
                    ov = round((res["礼貌度"]+res["专业度"]+res["合规性"]+res["问题解决率"])/4)
                    c5.metric("综合", f"{ov}")
                    if res.get("问题项"):
                        st.markdown("**⚠️ 待改进**")
                        for it in res["问题项"]: st.markdown(tag(it["内容"], it.get("等级","yellow")), unsafe_allow_html=True)
                    if res.get("亮点项"):
                        st.markdown("**✨ 亮点**")
                        for hl in res["亮点项"]: st.markdown(tag(hl["内容"], "green"), unsafe_allow_html=True)
                elif isinstance(res, dict) and "情绪等级" in res:
                    lvl = res["情绪等级"]; c = "#ef4444" if "高危" in lvl else "#f59e0b" if "中危" in lvl else "#10b981"
                    col1, col2 = st.columns([1,2])
                    with col1: st.markdown(f'<div class="card card-pink" style="text-align:center"><div style="font-size:28px;font-weight:800;color:{c}">{lvl}</div><div style="margin-top:6px;font-size:13px">{res.get("建议动作","")}</div></div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown("**情绪关键词**: "+" ".join(tag(kw,"yellow") for kw in res.get("情绪关键词命中",[])), unsafe_allow_html=True)
                        st.markdown("**风险词汇**: "+" ".join(tag(kw,"red") for kw in res.get("风险词汇",[])), unsafe_allow_html=True)
                    if res.get("情绪走势"):
                        st.markdown("**📈 情绪走势**")
                        st.line_chart(pd.DataFrame(res["情绪走势"]).set_index("轮次")["情绪分"], height=220)
                elif isinstance(res, list):
                    for item in res:
                        if "类型" in item:
                            rc = {"极高":"red","高":"yellow","中":"blue","低":"green"}.get(item.get("复用性","中"),"blue")
                            st.markdown(f'<div class="card {color_cls}"><strong>💡 {item["类型"]}</strong> {tag("复用:"+item.get("复用性",""),rc)}<div style="margin-top:6px">{item["内容"]}</div></div>', unsafe_allow_html=True)
                        elif "客户画像" in item:
                            st.markdown(f'<div class="card card-orange"><strong>{item.get("意向产品","")}</strong> {item.get("意向等级","")}<div>👤 {item.get("客户画像","")}</div><div>📅 {item.get("跟进动作","")}</div><div>💬 {item.get("话术建议","")}</div></div>', unsafe_allow_html=True)
                        elif "断点位置" in item:
                            rc = "red" if "高" in item.get("影响程度","") else "yellow" if "中" in item.get("影响程度","") else "green"
                            st.markdown(f'<div class="card card-red"><strong>📍 {item["断点位置"]}</strong> {tag(item.get("影响程度",""),rc)}<div>问题：{item.get("问题描述","")}</div><div>根因：{item.get("根因分析","")}</div><div>💡 {item.get("优化建议","")}</div></div>', unsafe_allow_html=True)
                        elif "需求类型" in item:
                            pass
                    if res and "需求类型" in res[0]:
                        st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)
                st.json(res, expanded=False)

    make_agent_tab(tab2, QUALITY_SYSTEM, "📋 质检", "card-blue", "blue")
    make_agent_tab(tab3, KNOWLEDGE_SYSTEM, "📚 知识", "card-green", "green")
    make_agent_tab(tab4, LEAD_SYSTEM, "🎯 线索", "card-orange", "orange")
    make_agent_tab(tab5, BREAKPOINT_SYSTEM, "🔗 断点", "card-red", "red")
    make_agent_tab(tab6, DEMAND_SYSTEM, "💡 需求", "card-purple", "purple")
    make_agent_tab(tab7, RISK_SYSTEM, "⚠️ 风险", "card-pink", "pink")

elif "批量看板" in input_mode:
    batch_convs = st.session_state.get("batch_convs") or {}

    if "batch_store" not in st.session_state:
        st.session_state.batch_store = {}
    store = st.session_state.batch_store

    for name in batch_convs:
        if name not in store:
            store[name] = {"对话": batch_convs[name], "分析": {}}

    for name in list(store.keys()):
        if name not in batch_convs:
            del store[name]

    st.markdown("### 📊 批量智能分析看板（增量式 · 随分析实时刷新）")
    st.caption(f"共 {len(batch_convs)} 条对话 · 已分析 {len(store)} 条 · 点击下方任意智能体按钮 → 看板即刻更新")

    a_status = {aname: 0 for aname, _ in AGENTS_BATCH}
    for name in store:
        for aname, _ in AGENTS_BATCH:
            if aname in store[name]["分析"] and store[name]["分析"][aname] is not None:
                a_status[aname] += 1

    st.markdown("#### 🤖 逐个智能体运行（跑全部对话）")
    btn_cols = st.columns(6)
    agent_cards = [
        ("📋", "质检", QUALITY_SYSTEM, "card-blue"),
        ("📚", "知识", KNOWLEDGE_SYSTEM, "card-green"),
        ("🎯", "线索", LEAD_SYSTEM, "card-orange"),
        ("🔗", "断点", BREAKPOINT_SYSTEM, "card-red"),
        ("💡", "需求", DEMAND_SYSTEM, "card-purple"),
        ("⚠️", "风险", RISK_SYSTEM, "card-pink"),
    ]

    for i, (icon, aname, sys_prompt, card_cls) in enumerate(agent_cards):
        with btn_cols[i]:
            st.markdown(f'<div class="card {card_cls}" style="padding:12px 16px;margin:0">', unsafe_allow_html=True)
            st.markdown(f"**{icon} {aname}**")
            st.markdown(f"<div style='font-size:11px;color:#64748b'>已覆盖 {a_status[aname]}/{len(store)}</div>", unsafe_allow_html=True)
            key_btn = f"btn_single_{aname}"
            if st.button(f"▶️ 运行", key=key_btn, use_container_width=True, disabled=not store):
                ph = st.progress(0.0, text=f"{aname}智能体分析中...")
                names_list = list(store.keys())
                for idx, n in enumerate(names_list):
                    ph.progress((idx + 1) / len(names_list), text=f"【{aname}】{n}（{idx+1}/{len(names_list)}）")
                    store[n]["分析"][aname] = call_llm_json(sys_prompt, conv_to_text(store[n]["对话"]))
                ph.progress(1.0, text=f"✅ {aname}完成")
                time.sleep(0.4)
                ph.empty()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    col_go_all, col_clr_all, _ = st.columns([2, 1, 3])
    with col_go_all:
        if st.button("⚡ 一键运行全部六大智能体", type="primary", use_container_width=True, disabled=not store):
            aname_cycle = [a[1] for a in agent_cards]
            sys_map = {a[1]: a[2] for a in agent_cards}
            total = len(store) * 6
            done = 0
            ph = st.progress(0.0, text="开始全量分析...")
            for aname in aname_cycle:
                for n in store:
                    store[n]["分析"][aname] = call_llm_json(sys_map[aname], conv_to_text(store[n]["对话"]))
                    done += 1
                    ph.progress(done / total, text=f"【{aname}】{n}（{done}/{total}）")
            ph.progress(1.0, text="✅ 全部完成")
            time.sleep(0.5)
            ph.empty()
            st.rerun()
    with col_clr_all:
        if st.button("🗑️ 清空所有分析结果", use_container_width=True):
            for n in store:
                store[n]["分析"] = {}
            st.rerun()

    any_result = any(any(v is not None for v in store[n]["分析"].values()) for n in store)

    if not store:
        st.info("👈 请在左侧栏选择对话样本（默认已勾选全部3条预设）")
        st.stop()

    if not any_result:
        st.info("👆 还没有任何分析结果，点击上方任一智能体按钮开始吧！每跑完一个，下方看板就会更新。")
        st.stop()

    qualities = []
    risk_rows = []
    lead_rows = []
    demand_rows = []
    bp_rows = []
    knowledge_rows = []
    issue_rows = []

    for name, entry in store.items():
        q = entry["分析"].get("质检")
        if q:
            ov = round((q.get("礼貌度", 0) + q.get("专业度", 0) + q.get("合规性", 0) + q.get("问题解决率", 0)) / 4)
            qualities.append({"名称": name, "综合": ov,
                              "礼貌度": q.get("礼貌度", 0), "专业度": q.get("专业度", 0),
                              "合规性": q.get("合规性", 0), "解决率": q.get("问题解决率", 0)})
            for it in q.get("问题项", []) or []:
                issue_rows.append({"来源": name, "问题": it.get("内容", ""), "等级": it.get("等级", "yellow")})

        risk = entry["分析"].get("风险")
        if risk:
            risk_rows.append({"来源": name, "情绪等级": risk.get("情绪等级", "-"),
                              "建议动作": risk.get("建议动作", ""),
                              "情绪关键词": "、".join(risk.get("情绪关键词命中", []))})

        for item in (entry["分析"].get("线索") or []):
            lead_rows.append({"来源": name, "意向产品": item.get("意向产品", ""),
                              "意向等级": item.get("意向等级", ""), "客户画像": item.get("客户画像", ""),
                              "跟进动作": item.get("跟进动作", "")})

        for item in (entry["分析"].get("需求") or []):
            demand_rows.append({"来源": name, "需求类型": item.get("需求类型", ""),
                                "需求描述": item.get("需求描述", ""), "客户层级": item.get("客户层级", ""),
                                "需求频次": item.get("需求频次", ""), "优先级": item.get("优先级", "")})

        for item in (entry["分析"].get("断点") or []):
            bp_rows.append({"来源": name, "断点位置": item.get("断点位置", ""),
                            "影响程度": item.get("影响程度", ""), "问题描述": item.get("问题描述", ""),
                            "优化建议": item.get("优化建议", "")})

        for item in (entry["分析"].get("知识") or []):
            knowledge_rows.append({"来源": name, "类型": item.get("类型", ""),
                                   "复用性": item.get("复用性", ""), "内容": item.get("内容", "")})

    n_conv = len(store)
    avg_score = round(sum(q["综合"] for q in qualities) / len(qualities), 1) if qualities else 0
    red_risk = sum(1 for x in risk_rows if "高危" in x.get("情绪等级", ""))

    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-box"><div class="val">{n_conv}</div><div class="lbl">对话总数</div></div>', unsafe_allow_html=True)
    if qualities:
        c2.markdown(f'<div class="metric-box"><div class="val">{avg_score}</div><div class="lbl">平均质检分</div></div>', unsafe_allow_html=True)
    else:
        c2.markdown('<div class="metric-box"><div class="val" style="color:#94a3b8">—</div><div class="lbl">平均质检分（待跑质检）</div></div>', unsafe_allow_html=True)
    if lead_rows:
        c3.markdown(f'<div class="metric-box"><div class="val">{len(lead_rows)}</div><div class="lbl">营销线索</div></div>', unsafe_allow_html=True)
    else:
        c3.markdown('<div class="metric-box"><div class="val" style="color:#94a3b8">—</div><div class="lbl">营销线索（待跑线索）</div></div>', unsafe_allow_html=True)
    if risk_rows:
        c4.markdown(f'<div class="metric-box"><div class="val" style="color:#ef4444">{red_risk}</div><div class="lbl">高危风险对话</div></div>', unsafe_allow_html=True)
    else:
        c4.markdown('<div class="metric-box"><div class="val" style="color:#94a3b8">—</div><div class="lbl">风险（待跑风险）</div></div>', unsafe_allow_html=True)

    tab_dash, tab_conv, tab_raw = st.tabs([
        "📊 聚合看板", "📋 逐条详情", "🧾 原始JSON"
    ])

    with tab_dash:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📋 质检等级分布")
            if qualities:
                bins = {"优秀(≥90)": 0, "良好(80-89)": 0, "合格(70-79)": 0, "待改进(<70)": 0}
                for q in qualities:
                    s = q["综合"]
                    if s >= 90: bins["优秀(≥90)"] += 1
                    elif s >= 80: bins["良好(80-89)"] += 1
                    elif s >= 70: bins["合格(70-79)"] += 1
                    else: bins["待改进(<70)"] += 1
                st.bar_chart(pd.DataFrame({"等级": list(bins.keys()), "数量": list(bins.values())}).set_index("等级"), height=260)
            else:
                st.info("👆 请先运行「质检」智能体")

        with col2:
            st.markdown("### 📈 各对话综合质检分")
            if qualities:
                st.bar_chart(pd.DataFrame(qualities).set_index("名称")["综合"], height=260)
            else:
                st.info("👆 请先运行「质检」智能体")

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("### 🎯 营销线索汇总")
            if lead_rows:
                st.dataframe(pd.DataFrame(lead_rows), use_container_width=True, hide_index=True)
            else:
                st.info("👆 请先运行「线索」智能体")

        with col4:
            st.markdown("### ⚠️ 风险对话")
            if risk_rows:
                st.dataframe(pd.DataFrame(risk_rows), use_container_width=True, hide_index=True)
            else:
                st.info("👆 请先运行「风险」智能体")

        col5, col6 = st.columns(2)
        with col5:
            st.markdown("### 💡 客户需求 Top")
            if demand_rows:
                cnt = Counter(d["需求描述"] for d in demand_rows if d.get("需求描述"))
                top_d = cnt.most_common(10)
                st.dataframe(pd.DataFrame([{"需求": k, "频次": v} for k, v in top_d]), use_container_width=True, hide_index=True)
            else:
                st.info("👆 请先运行「需求」智能体")

        with col6:
            st.markdown("### 🔗 服务断点")
            if bp_rows:
                st.dataframe(pd.DataFrame(bp_rows), use_container_width=True, hide_index=True)
            else:
                st.info("👆 请先运行「断点」智能体")

        st.markdown("### 🧠 可复用知识")
        if knowledge_rows:
            st.dataframe(pd.DataFrame(knowledge_rows), use_container_width=True, hide_index=True)
        else:
            st.info("👆 请先运行「知识」智能体")

        st.markdown("### 🛠️ 待改进问题项")
        if issue_rows:
            st.dataframe(pd.DataFrame(issue_rows), use_container_width=True, hide_index=True)
        elif qualities:
            st.info("🎉 质检未发现明显问题")
        else:
            st.info("👆 请先运行「质检」智能体")

    with tab_conv:
        for name, entry in store.items():
            q = entry["分析"].get("质检") or {}
            ov = round((q.get("礼貌度", 0) + q.get("专业度", 0) + q.get("合规性", 0) + q.get("问题解决率", 0)) / 4) if q else None
            score_str = f"{ov} 分" if ov is not None else "未分析"
            st.markdown(f'<div class="card card-blue"><strong>💬 {name}</strong> — 综合质检 {score_str} · {len(entry["对话"])} 条对话</div>', unsafe_allow_html=True)
            with st.expander("查看对话与分析详情", expanded=False):
                st.markdown("**原始对话**")
                for t in entry["对话"]:
                    ic = "👤" if t["role"] == "客户" else "🎧"
                    st.markdown(f"{ic} **{t['role']}** · {t['time']}  {t['content']}")
                st.divider()
                for aname, _ in AGENTS_BATCH:
                    sub = entry["分析"].get(aname)
                    st.markdown(f"**🤖 {aname}智能体**")
                    if sub is None:
                        st.warning("⏳ 尚未运行")
                    else:
                        st.json(sub, expanded=False)

    with tab_raw:
        exportable = [{"名称": n, "对话": e["对话"], "分析": e["分析"]} for n, e in store.items()]
        st.download_button(
            "⬇️ 下载完整分析结果 JSON",
            json.dumps(exportable, ensure_ascii=False, indent=2),
            "批量分析结果.json",
            "application/json",
            use_container_width=True,
        )
        st.json(exportable, expanded=False)

st.markdown("---")
st.markdown("🧠 **客户之声洞察 v3.0** · API 可视化配置 · 一键全分析 · 渐变卡片美学 · 基于大模型智能体平台")