"""사용자 배너와 대화·통계 패널 시안을 반영한 반응형 스타일."""
import streamlit as st


def apply_region_styles():
    """지역 선택 화면에만 적용하는 카드 그리드와 간격."""
    st.html('''<style>
    .st-key-region-page{max-width:1120px;margin:0 auto;gap:22px;padding:8px 0 24px}
    .region-title{text-align:center;padding:12px 0 8px}
    .region-title small{font-size:12px;letter-spacing:.12em;color:#2772c9;font-weight:800}
    .region-title h1{font-size:30px!important;margin:10px 0 6px;padding:0;line-height:1.35}
    .region-title p{font-size:14px;color:#7c8ca7;margin:0}
    .st-key-region-search [data-testid="stTextInputRootElement"]{background:white;border:1px solid #dde8f7;border-radius:12px;box-shadow:none;min-height:54px}
    .st-key-region-search [data-testid="stTextInputRootElement"]:focus-within{border-color:#1975ff}
    .st-key-region-search input{background:transparent;min-width:0;font-size:14px}
    .st-key-region-grid{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;align-items:stretch}
    .st-key-region-grid>[data-testid="stLayoutWrapper"]{min-width:0;height:176px}
    .st-key-region-grid div[class*="st-key-spot-card-"]{position:relative;height:176px;min-height:176px;padding:22px!important;border-radius:16px!important;border:1px solid #dde8f7!important;background:white;gap:0;box-shadow:none;transition:border-color .15s,box-shadow .15s}
    .st-key-region-grid div[class*="st-key-spot-card-"]:has(button:hover),.st-key-region-grid div[class*="st-key-spot-card-"]:has(button:focus-visible){border-color:#1975ff!important;box-shadow:0 3px 12px #1975ff0b}
    .st-key-region-grid [data-testid="stElementContainer"]:has(> [data-testid="stButton"]){position:absolute;inset:0;width:100%!important;height:100%;z-index:2}
    .st-key-region-grid [data-testid="stButton"]{height:100%}
    .st-key-region-grid button{height:100%;min-height:100%!important;border:0!important;background:transparent!important;border-radius:16px;cursor:pointer}
    .st-key-region-grid button p{opacity:0}
    .region-card-content{pointer-events:none;position:relative;z-index:1}
    .region-card-top{display:flex;align-items:center;gap:12px;min-height:60px}
    .region-pin{display:grid;place-items:center;flex:0 0 40px;height:40px;background:#eef5ff;border-radius:50%;color:#146cda;font-size:26px}.region-pin svg{width:22px;height:22px}
    .region-card-label{min-width:0;flex:1}.region-card-label small{display:block;color:#7c8ca7;font-size:12px;margin-bottom:5px}
    .region-card-label strong{display:block;color:#102144;font-size:18px;font-weight:800;line-height:1.35;overflow-wrap:anywhere}
    .region-arrow{color:#2772c9;font-size:20px}.region-components{position:absolute;top:65px;left:52px;color:#7c8ca7;font-size:11px}
    .region-tags{display:flex;gap:6px;border-top:1px solid #edf2f9;margin-top:24px;padding-top:13px;flex-wrap:wrap}
    .region-tags span{font-size:11px;color:#7687a2;background:#f2f6fc;border-radius:20px;padding:3px 9px}
    .st-key-region-home button{background:white;border:1px solid #d0d9e8;border-radius:10px}
    @media(min-width:641px) and (max-width:1000px){.st-key-region-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
    @media(max-width:640px){.st-key-region-page{gap:18px;padding-top:0}.region-title h1{font-size:25px!important}.st-key-region-grid{grid-template-columns:minmax(0,1fr);gap:16px}.region-card-label strong{font-size:18px}.region-title{padding:8px 0}.st-key-region-search input{font-size:12px}}
    </style>''')


def apply_styles():
    st.html('''<style>
    .stApp{background:radial-gradient(ellipse at 90% 0%,#eaf2ff 0%,#f7faff 50%,#fff 100%);color:#122446}
    .stMainBlockContainer{max-width:1920px;width:100%;padding:1.1rem 1.8rem 1.4rem}
    [data-testid="stHeader"]{background:transparent;height:2rem}
    h1,h2,h3{color:#102144;letter-spacing:-.045em!important;font-weight:800!important}
    p{line-height:1.75}button{transition:background .15s ease!important}
    button[kind="primary"]{background:linear-gradient(115deg,#0868ff,#287bff);border-color:#1975ff;border-radius:13px}
    button[kind="primary"] p{color:white!important}
    .brand{display:flex;gap:10px;align-items:center;padding:4px 0 15px}.brand strong{font-size:23px;letter-spacing:-1px;font-weight:900;color:#0d1937}.brand small{display:block;color:#7d8da8;font-size:8px;letter-spacing:.7px}
    .brand-marker{display:block;flex-shrink:0;width:27px;height:27px;background:linear-gradient(135deg,#77b7ff,#0769ff);border-radius:50% 50% 50% 0;transform:rotate(-45deg);position:relative;margin:0 6px 8px 2px}
    .brand-marker:after{content:"";position:absolute;width:11px;height:11px;background:white;border-radius:50%;left:8px;top:8px}
    .eyebrow{font-size:11px;font-weight:800;letter-spacing:.16em;color:#2772c9;margin-bottom:22px}
    .st-key-hero{min-height:600px;height:calc(100dvh - 250px);max-height:850px;padding:clamp(35px,5vw,95px)!important;border-radius:22px;border:1px solid #e4edf9;background-size:cover;background-position:center;justify-content:center;overflow:hidden;box-shadow:0 18px 60px #193b7010}
    .st-key-hero h1{font-size:clamp(38px,4vw,65px)!important;white-space:pre-line;line-height:1.24;max-width:640px;margin-bottom:18px}
    .st-key-hero p{font-size:17px;max-width:470px;color:#385274}.st-key-hero button{margin:20px 0 6px;min-height:50px;padding:0 30px}
    .st-key-hero [data-testid="stCaptionContainer"] p{font-size:12px}
    .st-key-home-features{gap:20px;margin-top:22px}.feature{flex:1;background:#ffffffb8;border:1px solid #e2ebf8;border-radius:15px;padding:20px 24px;min-width:240px}.feature small{color:#2580ff;font-weight:800}.feature h3{font-size:17px!important;margin:6px 0}.feature p{font-size:13px;color:#7687a2;margin:0}
    .page-title{text-align:center;padding:35px 0}.page-title h1{font-size:32px!important;margin-bottom:8px}.page-title p{color:#7c8ca7;font-size:14px}
    div[class*="st-key-spot-card-"]{padding:22px!important;border-color:#dde8f7!important;background:white;border-radius:18px!important}
    div[class*="st-key-spot-card-"] button{min-height:75px;font-size:20px;border:0;background:#eef5ff;color:#146cda;width:100%}
    .st-key-conversation-nav{padding:12px 4px;min-height:690px}.st-key-conversation-nav button{white-space:normal;text-align:left;padding:13px 12px;border:0;background:transparent;justify-content:flex-start;border-radius:14px}.st-key-conversation-nav button[kind="primary"]{color:white;background:linear-gradient(115deg,#0868ff,#287bff)}
    .st-key-conversation-nav [data-testid="stCaptionContainer"]{color:#8a9bb5;font-size:11px}.st-key-conversation-nav>div{gap:8px}
    .nav-note{margin-top:45px;padding:24px 20px;min-height:190px;border-radius:18px;background:linear-gradient(145deg,#e4eeff,#f0f6ff);color:#28529a}.nav-note small{display:block;font-size:12px}.nav-note strong{display:block;margin:12px 0;font-size:16px;line-height:1.65}.nav-note span{color:#7b91b3;font-size:12px}
    .st-key-conversation-panel,.st-key-insights-panel{background:#ffffffed;border:1px solid #e2ebf8!important;border-radius:20px!important;padding:18px!important;box-shadow:0 4px 24px #25467404}
    .st-key-conversation-panel{height:calc(100dvh - 115px);min-height:690px}.st-key-insights-panel{height:calc(100dvh - 115px);min-height:690px;overflow-y:auto}
    .st-key-chat-feed{height:calc(100dvh - 335px)!important;min-height:450px;overscroll-behavior:contain}
    .st-key-chat-feed [data-testid="stChatMessage"]{border:0;background:#f2f6fc;border-radius:18px;padding:17px 14px;margin-bottom:16px;max-width:97%}
    .st-key-chat-feed [data-testid="stChatMessage"] p{font-size:14px;line-height:1.85}
    .st-key-chat-feed [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){background:linear-gradient(120deg,#086aff,#2d7cff);color:white;margin-left:12%;max-width:88%;flex-direction:row-reverse}
    .st-key-chat-feed [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p{color:white}
    .st-key-chat-feed [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stCaptionContainer"] p{color:#dceaff}
    .st-key-chat-composer [data-testid="stChatInput"],
    .st-key-chat-composer [data-testid="stChatInput"]:focus-within{background:#edf3fc;border:0!important;outline:none!important;border-radius:17px;min-height:60px;box-shadow:none!important}
    .st-key-chat-composer [data-testid="stChatInput"] textarea,
    .st-key-chat-composer [data-testid="stChatInput"] textarea:focus,
    .st-key-chat-composer [data-testid="stChatInput"] > div,
    .st-key-chat-composer [data-testid="stChatInput"] > div:focus-within,
    .st-key-chat-composer [data-testid="stChatInput"] [data-baseweb="textarea"]{border:0!important;outline:none!important;box-shadow:none!important}
    .st-key-quick-prompts{gap:6px}.st-key-quick-prompts button{border:1px solid #e3eafa;border-radius:25px;background:white;font-size:12px;min-height:32px;padding:4px 12px}
    .st-key-insights-panel [data-testid="stMetric"]{padding:12px;background:#f6f9ff;border:1px solid #e8eff9;border-radius:12px;min-height:91px}
    [data-testid="stMetricValue"]{font-size:22px!important;font-weight:800;color:#153567}[data-testid="stMetricLabel"]{font-size:12px;color:#7a8daa}
    .st-key-insights-panel [data-testid="stCaptionContainer"] p{font-size:10px;line-height:1.6;color:#8191aa}
    .spotcheck-map-status{font-size:10px;color:#8495ad;padding-top:6px}
    div[class*="st-key-summary-"]{background:white;border:1px solid #e5edf8;border-radius:14px;padding:15px!important}
    div[class*="st-key-summary-"] [data-testid="stMetricValue"]{font-size:20px!important}
    @media(max-width:1100px){[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-conversation-panel){flex-wrap:wrap}
    [data-testid="stColumn"]:has(.st-key-conversation-nav){flex:1 1 100%;min-width:0}.st-key-conversation-nav{min-height:0}.nav-note{display:none}
    [data-testid="stColumn"]:has(.st-key-conversation-panel){flex:2 1 480px;min-width:0}[data-testid="stColumn"]:has(.st-key-insights-panel){flex:1 1 300px;min-width:0}
    .st-key-conversation-panel,.st-key-insights-panel{height:auto;min-height:0}.st-key-chat-feed{height:65dvh!important;min-height:350px}}
    @media(max-width:600px){[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .brand){flex-wrap:wrap!important}[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .brand)>[data-testid="stColumn"]{flex:0 0 100%!important;width:100%!important;max-width:100%!important}
    .stMainBlockContainer{padding:1rem .7rem}.brand strong{font-size:19px}.st-key-hero{min-height:600px;height:auto;padding:36px 24px!important;background-position:60% center}.st-key-hero h1{font-size:37px!important}.st-key-hero p{font-size:15px;max-width:260px;background:#ffffff50}.st-key-conversation-panel,.st-key-insights-panel{padding:12px!important}.st-key-chat-feed [data-testid="stChatMessage"]{padding:12px 8px;max-width:100%}.st-key-chat-feed [data-testid="stChatMessage"] p{font-size:13px}.st-key-home-features{flex-direction:column}.feature{min-width:0}.st-key-insights-panel [data-testid="stMetricValue"]{font-size:20px!important}[data-testid="stColumn"]{min-width:0}}
    </style>''')


def brand():
    st.html('<div class="brand"><span class="brand-marker" aria-hidden="true"></span><div><strong>SPOT CHECK</strong><small>AI LOCATION INTELLIGENCE</small></div></div>')


def page_title(title, subtitle):
    from html import escape
    st.html(f'<div class="page-title"><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>')
