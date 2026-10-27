"""대시보드의 배치·크기·스크롤만 조정한다. 기존 시각 스타일은 유지."""
import streamlit as st


def apply_chat_layout(view='채팅'):
    active = {'채팅': 'conversation-panel', '분석': 'insights-panel', '대화 목록': 'conversation-nav'}.get(view, 'conversation-panel')
    st.html('''<style>
    /* 이 규칙은 채팅 화면에만 적용한다. 홈·지역 선택 화면은 기존 레이아웃 유지. */
    [data-testid="stMain"]:has(.st-key-workspace){height:100dvh;overflow:hidden}
    .stMainBlockContainer:has(.st-key-workspace){height:100dvh;min-height:0;max-height:100dvh;box-sizing:border-box;display:flex;flex-direction:column}
    .stMainBlockContainer:has(.st-key-workspace)>[data-testid="stVerticalBlock"]{height:100%;min-height:0;gap:16px;flex-wrap:nowrap}
    .st-key-global-header{flex:0 0 auto;min-width:0}
    [data-testid="stLayoutWrapper"]:has(>.st-key-workspace){flex:1 1 0;min-height:0;width:100%}
    .st-key-workspace{height:100%;min-height:0;display:flex;flex-direction:column;gap:12px}
    [data-testid="stLayoutWrapper"]:has(>.st-key-workspace-controls){display:none}
    [data-testid="stLayoutWrapper"]:has(>.st-key-workspace-grid){flex:1 1 0;min-height:0;width:100%}
    .st-key-workspace-grid>[data-testid="stLayoutWrapper"]{height:100%;min-height:0;overflow:hidden}
    .st-key-workspace-grid{height:100%;min-height:0;min-width:0}
    .st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]{height:100%;min-height:0;display:grid!important;grid-template-columns:minmax(176px,16fr) minmax(440px,54fr) minmax(288px,30fr);gap:16px;align-items:stretch;flex-wrap:nowrap!important}
    .st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{width:100%!important;max-width:none!important;min-width:0!important;min-height:0;height:100%;flex:unset!important;overflow:hidden}
    .st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]>[data-testid="stVerticalBlock"]{height:100%;min-height:0}
    [data-testid="stLayoutWrapper"]:has(>.st-key-conversation-panel),
    [data-testid="stLayoutWrapper"]:has(>.st-key-conversation-nav),
    [data-testid="stLayoutWrapper"]:has(>.st-key-insights-panel){height:100%;min-height:0;overflow:hidden}
    .st-key-conversation-panel,.st-key-conversation-nav,.st-key-insights-panel{height:100%!important;min-height:0!important;max-height:100%;min-width:0;box-sizing:border-box}
    .st-key-conversation-panel,.st-key-conversation-nav{display:flex;flex-direction:column;overflow:hidden!important;flex-wrap:nowrap}
    .st-key-insights-panel{overflow-y:auto!important;overflow-x:hidden;overscroll-behavior:contain;scrollbar-gutter:stable}
    .st-key-insights-panel [data-testid="stElementContainer"],.st-key-insights-panel iframe,.st-key-insights-panel canvas,.st-key-insights-panel svg{max-width:100%;min-width:0}
    .st-key-chat-heading,.st-key-chat-composer,.st-key-history-header,.st-key-history-footer{flex:0 0 auto;min-width:0}
    [data-testid="stLayoutWrapper"]:has(>.st-key-chat-heading),[data-testid="stLayoutWrapper"]:has(>.st-key-chat-composer),
    [data-testid="stLayoutWrapper"]:has(>.st-key-history-header),[data-testid="stLayoutWrapper"]:has(>.st-key-history-footer){flex:0 0 auto;min-width:0}
    [data-testid="stLayoutWrapper"]:has(.st-key-chat-feed),[data-testid="stLayoutWrapper"]:has(.st-key-history-list){min-height:0}
    .st-key-conversation-panel>[data-testid="stLayoutWrapper"]:has(.st-key-chat-feed),
    .st-key-conversation-nav>[data-testid="stLayoutWrapper"]:has(.st-key-history-list){flex:1 1 0;min-height:0;overflow:hidden}
    .st-key-chat-feed,.st-key-history-list{height:100%!important;min-height:0!important;max-height:100%;overflow-y:auto!important;overflow-x:hidden;overscroll-behavior:contain;scrollbar-gutter:stable}
    .st-key-chat-composer{gap:10px;height:auto!important;min-height:fit-content;overflow:visible;flex:0 0 auto!important}
    .st-key-chat-composer>[data-testid="stLayoutWrapper"],.st-key-chat-composer>[data-testid="stElementContainer"]{flex:0 0 auto}
    .st-key-chat-composer [data-testid="stChatInput"]{max-height:160px;min-height:60px}
    .st-key-chat-composer textarea{max-height:128px!important;overflow-y:auto!important;overflow-wrap:anywhere}
    .st-key-quick-prompts{min-width:0;max-width:100%;overflow-x:auto;flex-wrap:nowrap!important;padding-bottom:3px;scrollbar-width:thin;overscroll-behavior-x:contain}
    .st-key-quick-prompts>[data-testid="stElementContainer"]{flex:0 0 auto!important;width:auto!important}
    .st-key-chat-feed [data-testid^="stChatMessageAvatar"]{display:none!important}
    .st-key-chat-feed [data-testid="stChatMessage"]{gap:0;padding:12px 16px;align-self:flex-start;width:fit-content;max-width:94%;min-width:0;flex:0 0 auto;overflow-wrap:anywhere}
    .st-key-chat-feed [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]){align-self:flex-end;margin-left:auto;margin-right:0;width:fit-content;max-width:84%}
    .st-key-chat-feed [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]){background:linear-gradient(120deg,#086aff,#2d7cff);color:white;flex-direction:row-reverse}
    .st-key-chat-feed [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) p{color:white}
    .st-key-chat-feed [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stCaptionContainer"] p{color:#dceaff}
    .st-key-chat-feed [data-testid="stChatMessageContent"]{min-width:0;overflow-wrap:anywhere;max-width:100%}
    .st-key-chat-feed [data-testid="stChatMessage"]:has([data-testid="stMetric"]),
    .st-key-chat-feed [data-testid="stChatMessage"]:has([data-testid="stVegaLiteChart"]){width:94%}
    .st-key-history-list button{max-width:100%;overflow-wrap:anywhere}
    .st-key-history-footer .nav-note{margin-top:0;min-height:0}
    @media(min-width:1200px){.st-key-workspace-controls{display:none}}
    @media(min-width:900px) and (max-width:1199px){
      [data-testid="stLayoutWrapper"]:has(>.st-key-workspace-controls){display:flex;flex:0 0 auto}
      .st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]{grid-template-columns:minmax(420px,64fr) minmax(280px,36fr)}
      .st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:has(.st-key-conversation-nav){display:none}
      .st-key-history-footer .nav-note{display:block}
    }
    @media(max-width:899px){
      [data-testid="stLayoutWrapper"]:has(>.st-key-workspace-controls){display:flex;flex:0 0 auto}
      .st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]{grid-template-columns:minmax(0,1fr)}
      .st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{display:none}
      .st-key-conversation-panel,.st-key-insights-panel{min-height:0!important}
      .st-key-history-footer .nav-note{display:block}
      .st-key-chat-feed [data-testid="stChatMessage"]{max-width:96%}
      .st-key-chat-composer{max-height:46%}
    }
    </style>''')
    st.html(f'''<style>
    @media(max-width:899px){{.st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:has(.st-key-{active}){{display:block}}}}
    </style>''')
    if view == '대화 목록':
        st.html('''<style>@media(min-width:900px) and (max-width:1199px){
        .st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:has(.st-key-conversation-nav){display:block}
        .st-key-workspace-grid>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:has(.st-key-conversation-panel){display:none}
        }</style>''')
