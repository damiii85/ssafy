import React,{useState,useEffect,useRef}from'react';
import{Layout,Button,Som}from'./components/UI';
import{quests,guilds}from'./data/content';

const questTypeImage={explore:'/assets/quest-types-new/explore.png',discover:'/assets/quest-types-new/Discover.png',together:'/assets/quest-types-new/together.png',reward:'/assets/quest-types-new/Reward.png'};

const distanceMeters=(a,b)=>{if(!a||!b)return null;const R=6371000;const rad=v=>v*Math.PI/180;const dLat=rad(b.lat-a.lat),dLng=rad(b.lng-a.lng);const x=Math.sin(dLat/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(dLng/2)**2;return 2*R*Math.atan2(Math.sqrt(x),Math.sqrt(1-x))};

const companionQrCodes=["EVR7K2Q9", "SOM4N8XZ", "GUILD6P2", "LARA9M5Q", "LENNY3W8", "PANDA7R4", "MAGIC2K9", "CLOUD8V3", "QUEST5H7", "EVER6T2Q", "HUNT9C4M", "FEST3Y8K"];


const Thumb=({questType})=><div className="thumb quest-type-thumb"><img src={questTypeImage[questType]||questTypeImage.photo} alt="퀘스트 유형"/></div>;

const somShopCategories=[
  {id:'season',label:'시즌한정',emoji:'🍁',items:[
    {name:'가을 레니',image:'/assets/shop-products/autumn-lenny.png'},
    {name:'가을 라라',image:'/assets/shop-products/autumn-lara.png'}
  ]},
  {id:'goods',label:'굿즈',emoji:'🧸',items:[
    {name:'바오 인형',image:'/assets/shop-products/bao-doll.png'},
    {name:'바오 머리띠',image:'/assets/shop-products/bao-headband.png'}
  ]},
  {id:'coupon',label:'쿠폰',emoji:'🎟️',items:[
    {name:'회오리 감자 교환권',image:'/assets/shop-products/snack.png'},
    {name:'스낵버스터 20% 할인권',image:'/assets/shop-products/snackbuster.png'}
  ]},
  {id:'gifticon',label:'기프티콘',emoji:'🎁',items:[
    {name:'스타벅스 5,000원 카드',image:'/assets/shop-products/starbucks.png'},
    {name:'폴바셋 5,000원 카드',image:'/assets/shop-products/paul-bassett.jpg'}
  ]}
];

function SomShop({som,setPage}){const[category,setCategory]=useState('season');
const current=somShopCategories.find(c=>c.id===category)||somShopCategories[0];
return <Layout page="shop" setPage={setPage}><p className="eyebrow">SOM SHOP</p><h1>모은 솜으로<br/>특별한 보상을 만나보세요</h1><div className="balance"><small>나의 SOM</small><b>{som} SOM</b><p>퀘스트로 모은 SOM을 원하는 상품과 바꿔보세요!</p></div><div className="shop-category-tabs">{somShopCategories.map(c=><button key={c.id} className={category===c.id?'active':''} onClick={()=>setCategory(c.id)}><span>{c.emoji}</span><b>{c.label}</b></button>)}</div><div className="shop-section-head"><div><small>{current.label.toUpperCase()}</small><h2>{current.label}</h2></div><span>{current.items.length}개 상품</span></div><div className="shop-products">{current.items.map(item=><button className="shop-product-card" key={item.name}><div className="shop-product-image"><img src={item.image} alt={item.name}/></div><div className="shop-product-info"><b>{item.name}</b><p>{current.label} 상품</p></div></button>)}</div></Layout>}
export default function App(){const[page,setPage]=useState('everland');
const[som,setSom]=useState(140);
const[homeSlide,setHomeSlide]=useState(0);
const[homePaused,setHomePaused]=useState(false);
const[homeTouchX,setHomeTouchX]=useState(null);
const[ticket,setTicket]=useState('');
const[ticketModal,setTicketModal]=useState(false);
const[ticketMode,setTicketMode]=useState('code');
const[ticketRegistered,setTicketRegistered]=useState(false);
const[ticketSuccess,setTicketSuccess]=useState(false);
const[assigned,setAssigned]=useState(false);
const[myGuild,setMyGuild]=useState(null);
const[companions,setCompanions]=useState([]);
const[companionCode,setCompanionCode]=useState('');
const[incoming,setIncoming]=useState(false);
const[qrCompanionModal,setQrCompanionModal]=useState(false);
const makeCompanionCode=()=>companionQrCodes[Math.floor(Math.random()*companionQrCodes.length)];
const[myCompanionCode,setMyCompanionCode]=useState(makeCompanionCode);
const[companionMode,setCompanionMode]=useState('qr');
const[qrView,setQrView]=useState('scan');
const[companionSent,setCompanionSent]=useState(false);
const[captured,setCaptured]=useState(false); const[caughtSomIds,setCaughtSomIds]=useState([]);
const[selectedQuest,setSelectedQuest]=useState(null);
const[proof,setProof]=useState({});
const[photoSelected,setPhotoSelected]=useState(false);
const[togetherAnswer,setTogetherAnswer]=useState('');
const[togetherMode,setTogetherMode]=useState('answer');
const[questComplete,setQuestComplete]=useState(null);
const[questToast,setQuestToast]=useState('');
const[completedQuests,setCompletedQuests]=useState([]);
const[todaySom,setTodaySom]=useState(140);
const[todayGp,setTodayGp]=useState(700);
const[companion,setCompanion]=useState('');
const[removeCompanionIndex,setRemoveCompanionIndex]=useState(null);
const[collectionTab,setCollectionTab]=useState('som');
const[somCollectionPage,setSomCollectionPage]=useState(0);
const[demoMode]=useState(true);
const[demoMoving,setDemoMoving]=useState(false);
const[demoMapPos,setDemoMapPos]=useState({x:50,y:82});
const[nearbySom,setNearbySom]=useState(null);
const[selectedSom,setSelectedSom]=useState(null);
const[userLocation,setUserLocation]=useState(null);
const[locationStatus,setLocationStatus]=useState('위치 확인 전');
const[mapView,setMapView]=useState({x:0,y:0,scale:1.55});
const[mapDrag,setMapDrag]=useState(null);
const mapViewportRef=useRef(null);
const go=p=>setPage(p);

const[cloudProgress,setCloudProgress]=useState(0);
const[cloudEnclosed,setCloudEnclosed]=useState(false);
const[cloudDrawing,setCloudDrawing]=useState(false);
const[cloudTrail,setCloudTrail]=useState([]);
const cloudTrackRef=useRef({lastAngle:null,total:0,direction:0});
const cloudZoneRef=useRef(null);

const resetCloudCapture=()=>{setCloudProgress(0);
setCloudEnclosed(false);
setCloudDrawing(false);
setCloudTrail([]);
cloudTrackRef.current={lastAngle:null,total:0,direction:0}};

const cloudPointerDown=e=>{if(cloudEnclosed)return;
const r=cloudZoneRef.current?.getBoundingClientRect();
if(!r)return;
e.currentTarget.setPointerCapture?.(e.pointerId);
setCloudDrawing(true);
const pt={x:e.clientX-r.left,y:e.clientY-r.top};
setCloudTrail([pt]);
setCloudProgress(0);
setCloudEnclosed(false)};

const cloudPointerMove=e=>{if(!cloudDrawing)return;
const r=cloudZoneRef.current?.getBoundingClientRect();
if(!r)return;
const pt={x:e.clientX-r.left,y:e.clientY-r.top};
setCloudTrail(t=>{const last=t[t.length-1];
if(last&&Math.hypot(last.x-pt.x,last.y-pt.y)<3)return t;
const next=[...t,pt].slice(-240);
const cx=r.width/2,cy=r.height/2;
const sectors=new Set();
let validRadiusPoints=0;
next.forEach(p=>{const radius=Math.hypot(p.x-cx,p.y-cy);
if(radius<55||radius>175)return;
validRadiusPoints++;
let a=Math.atan2(p.y-cy,p.x-cx);
if(a<0)a+=Math.PI*2;
sectors.add(Math.floor(a/(Math.PI*2)*48));
});
const coverage=sectors.size/48;
const start=next[0],end=next[next.length-1];
const closeDistance=start&&end?Math.hypot(start.x-end.x,start.y-end.y):Infinity;
const enoughTrail=next.length>=28&&validRadiusPoints>=20;
const loopClosed=closeDistance<=55;
const surroundsSom=next.length>=3&&pointInPolygon({x:cx,y:cy},next);
const enclosed=enoughTrail&&coverage>=0.55&&(loopClosed||coverage>=0.72);
setCloudEnclosed(enclosed);
const progress=Math.min(95,Math.round(Math.min(coverage/0.55,1)*82+(loopClosed?13:0)));
setCloudProgress(enclosed?100:progress);
return next});
};

const pointInPolygon=(pt,poly)=>{let inside=false;
for(let i=0,j=poly.length-1;
i<poly.length;
j=i++){const a=poly[i],b=poly[j];
if(((a.y>pt.y)!==(b.y>pt.y))&&(pt.x<(b.x-a.x)*(pt.y-a.y)/(b.y-a.y)+a.x))inside=!inside}return inside};

const cloudPointerUp=()=>{setCloudDrawing(false);if(cloudTrail.length>=12){setCloudEnclosed(true);setCloudProgress(100)}};

const openQuest=(q,i)=>{if(q.type==='together'){setTogetherMode(Math.random()<0.5?'answer':'hint');setTogetherAnswer('')}setSelectedQuest({...q,index:i})};

const closeQuest=()=>setSelectedQuest(null);
const finishQuest=(message='퀘스트 완료!')=>{const q=selectedQuest;if(q&&!completedQuests.includes(q.id)){setCompletedQuests(x=>[...x,q.id]);setTodaySom(v=>v+70);setTodayGp(v=>v+350);setSom(v=>v+70)}setSelectedQuest(null);setQuestComplete({message,reward:70,gp:350})};
const closeQuestComplete=()=>{setQuestComplete(null);setPage('quests')};

const uploadPhoto=e=>{const f=e.target.files?.[0];
if(f)setProof(x=>({...x,[selectedQuest.id]:`사진 선택 완료 · ${f.name}`}))};

const shareLocation=()=>{if(demoMode){setTimeout(()=>finishQuest('퀘스트를 완료했어요!'),450);return}if(!navigator.geolocation){setProof(x=>({...x,[selectedQuest.id]:'위치 기능을 지원하지 않는 브라우저예요.'}));
return}setProof(x=>({...x,[selectedQuest.id]:'현재 위치 확인 중...'}));
navigator.geolocation.getCurrentPosition(()=>finishQuest('퀘스트를 완료했어요!'),()=>setProof(x=>({...x,[selectedQuest.id]:'위치 확인에 실패했어요. 다시 시도해주세요.'}))) };

const registerCompanion=()=>{if(companion.trim())setProof(x=>({...x,[selectedQuest.id]:`${companion.trim()} 동행인 등록 완료 ✓`}))};

const QuestCard=({q,i=0})=>{const done=completedQuests.includes(q.id);return <button className={'card questrow questbutton '+(done?'quest-completed':'')} onClick={()=>openQuest(q,i)}><Thumb questType={q.type}/><div><small className="quest-category">{q.category}</small><b>{q.title}</b><p>{done?'✓ 완료':`+${q.reward} SOM　+${q.gp} GP`}</p></div><span>{done?'✓':'›'}</span></button>};

const registerTicket=()=>{if(ticket.replace(/\D/g,'').length===16){setTicketRegistered(true);setTicketModal(false);setTicketSuccess(true)}};
const loadMyTicket=()=>{setTicket('2026100198765432');setTicketMode('code')};

const addTravelCompanion=()=>{if(companionCode.trim().length===8){const nicknames=['보라솜','루이친구','가든러버','판다콩'];
const nickname=nicknames[companionCode.trim().charCodeAt(0)%nicknames.length];
setCompanions(x=>[...x,nickname]);
setCompanionCode('')}};

const homeBanners=['/assets/home-banners/bao-sticker.png','/assets/home-banners/korea-trip.png','/assets/home-banners/racing.png','/assets/home-banners/kids-costume.png'];
const moveHomeSlide=d=>setHomeSlide(i=>(i+d+homeBanners.length)%homeBanners.length);
const enterGuild=()=>{setMyCompanionCode(makeCompanionCode());setCompanionSent(false);setCompanionMode('qr');setQrView('scan');go('companions')};

useEffect(()=>{if(page!=='home'||homePaused)return;
const t=setInterval(()=>moveHomeSlide(1),4500);
return()=>clearInterval(t)},[page,homePaused]);

useEffect(()=>{if(page!=='companions')return;
const timer=setTimeout(()=>setIncoming(true),500);
return()=>clearTimeout(timer)},[page]);

useEffect(()=>{if(page!=='map')return;
if(demoMode){setUserLocation({lat:37.29430,lng:127.20130,accuracy:3});setLocationStatus('DEMO · 위치 인증 연결됨');return}
if(!navigator.geolocation){setLocationStatus('이 기기에서는 위치 기능을 지원하지 않아요.');
return}setLocationStatus('현재 위치 확인 중...');
const id=navigator.geolocation.watchPosition(pos=>{setUserLocation({lat:pos.coords.latitude,lng:pos.coords.longitude,accuracy:pos.coords.accuracy});
setLocationStatus('실시간 위치 연결됨')},()=>setLocationStatus('위치 권한을 허용해주세요.'),{enableHighAccuracy:true,maximumAge:3000,timeout:10000});
return()=>navigator.geolocation.clearWatch(id)},[page]);

const EVERLAND_BOUNDS={north:37.3000,south:37.2860,west:127.1940,east:127.2140};

const gpsToMap=loc=>{if(!loc)return null;
const x=(loc.lng-EVERLAND_BOUNDS.west)/(EVERLAND_BOUNDS.east-EVERLAND_BOUNDS.west)*100;
const y=(EVERLAND_BOUNDS.north-loc.lat)/(EVERLAND_BOUNDS.north-EVERLAND_BOUNDS.south)*100;
return{x:Math.max(2,Math.min(98,x)),y:Math.max(2,Math.min(98,y)),inside:x>=0&&x<=100&&y>=0&&y<=100}};

const somSpots=[{id:'global',name:'스페셜 솜',x:29,y:39,lat:37.29452,lng:127.20158,reward:20,image:'/assets/som-spawns/collab-som.png'},{id:'garden',name:'가을 솜',x:78,y:49,lat:37.29374,lng:127.20302,reward:30,image:'/assets/som-spawns/autumn-som.png'}];
const selectedSomDistance=selectedSom?distanceMeters(userLocation,selectedSom):null;
const somWithinRange=selectedSomDistance!==null&&selectedSomDistance<=10;
const recommendedQuests=quests.filter(q=>q.type!=='together'||companions.length>0).slice(0,3);

const visibleSomSpots=somSpots.filter(spot=>!caughtSomIds.includes(spot.id));
const mapDistanceMeters=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y)*12;
useEffect(()=>{if(page!=='map'||!demoMode||!visibleSomSpots.length){setNearbySom(null);return}const target=visibleSomSpots.reduce((best,spot)=>mapDistanceMeters(demoMapPos,spot)<mapDistanceMeters(demoMapPos,best)?spot:best,visibleSomSpots[0]);const timer=setInterval(()=>setDemoMapPos(pos=>{const dx=target.x-pos.x,dy=target.y-pos.y,dist=Math.hypot(dx,dy);if(dist<.35)return pos;const step=Math.min(1.15,dist);return{x:pos.x+dx/dist*step,y:pos.y+dy/dist*step}}),90);return()=>clearInterval(timer)},[page,demoMode,caughtSomIds]);
useEffect(()=>{if(page!=='map')return;const pos=demoMode?demoMapPos:gpsToMap(userLocation);if(!pos){setNearbySom(null);return}const close=visibleSomSpots.map(spot=>({...spot,distance:mapDistanceMeters(pos,spot)})).filter(spot=>spot.distance<=10).sort((a,b)=>a.distance-b.distance)[0]||null;setNearbySom(close);if(close)setLocationStatus('근처에 솜이 있어요 !')},[page,demoMode,demoMapPos,userLocation,caughtSomIds]);
const resetMap=()=>setMapView({x:0,y:0,scale:1.55});

const zoomMap=d=>setMapView(v=>({...v,scale:Math.max(1,Math.min(3,v.scale+d))}));

const assignGuild=()=>{const g=guilds[Math.floor(Math.random()*guilds.length)];
setMyGuild(g);
setAssigned(true);
go('assign')};

const currentGuild=myGuild||guilds[0];

const guildScores=guilds.map(g=>({...g,score:g.score+(assigned&&g.name===currentGuild.name&&captured?20:0)})).sort((a,b)=>b.score-a.score).map((g,i)=>({...g,rank:i+1}));

const battleRounds=[{round:1,time:'10:00 ~ 14:20',winner:'레니 길드',status:'completed'},{round:2,time:'14:30 ~ 18:20',status:'active'},{round:3,time:'18:30 ~ 21:50',status:'pending'}];

const GuildRanking=()=> <><div className="guild-head"><div><p className="eyebrow">TODAY'S GUILD BATTLE</p><h2>{currentGuild.name}</h2></div><span className="rank-badge">현재 {guildScores.find(g=>g.name===currentGuild.name)?.rank}위</span></div><div className="ranking compact">{guildScores.map(g=><div className={'rank-row '+(g.name===currentGuild.name?'mine':'')} key={g.name}><strong>{g.rank}</strong><span className="guild-logo-small"><img src={g.emojiImage} alt={g.name}/></span><div><b>{g.name}</b><small>{g.name===currentGuild.name?'내 길드 · ':''}오늘의 길드 포인트</small></div><em>{g.score} GP</em></div>)}</div><Button secondary onClick={()=>go('guild')}>길드전 현황 자세히 보기</Button></>;
const screens={
everland:(
  <main className="phone everland-shell everland-entry">
    <header className="everland-header-image"><img className="everland-topbar-logo" src="/assets/everland-home/topbar-left.png" alt="Everland" /><img className="everland-topbar-actions" src="/assets/everland-home/topbar-right.png" alt="티켓, 검색, 알림, MY" /></header>
    <section className="everland-content everland-entry-content">
      <button type="button" className="everland-guild-poster" onClick={() => go('home')} aria-label="길드전 입장하기">
        <img src="/assets/everland-home/guild-poster.png" alt="Ever Attack Guild Battle" />
      </button>
      <div className="everland-quick-menu" aria-label="에버랜드 빠른 메뉴">
        <button type="button"><img src="/assets/everland-home/smart-reservation.png" alt="" /><span>스마트예약</span></button>
        <button type="button" onClick={() => setTicketModal(true)}><img src="/assets/everland-home/ticket.png" alt="" /><span>티켓등록</span></button>
        <button type="button"><img src="/assets/everland-home/som.png" alt="" /><span>솜적립</span></button>
        <button type="button"><img src="/assets/everland-home/notice.png" alt="" /><span>공지사항</span></button>
        <button type="button"><img src="/assets/everland-home/smart-queue.png" alt="" /><span>스마트 줄서기</span></button>
      </div>
    </section>
  </main>
),
home:<Layout page="home" setPage={go} locked={!assigned}><div className="home-screen"><p className="eyebrow">SOM HUNTERS</p><h1>오늘, 어떤 하루를 만들까요?</h1><p className="home-sub">SOM과 함께하는 특별한 에버랜드 어드벤처!</p><div className="home-banner-slider" onTouchStart={e=>setHomeTouchX(e.touches[0].clientX)} onTouchEnd={e=>{if(homeTouchX==null)return;const dx=e.changedTouches[0].clientX-homeTouchX;if(Math.abs(dx)>35)moveHomeSlide(dx<0?1:-1);setHomeTouchX(null)}}><div className="home-banner-track" style={{transform:`translateX(-${homeSlide*100}%)`}}>{homeBanners.map((src,i)=><div className="home-banner-slide" key={src}><img src={src} alt={`에버랜드 이벤트 배너 ${i+1}`}/></div>)}</div><div className="banner-controls"><button onClick={()=>moveHomeSlide(-1)} aria-label="이전 배너">‹</button><span>{homeSlide+1} / {homeBanners.length}</span><button onClick={()=>moveHomeSlide(1)} aria-label="다음 배너">›</button><button className="pause" onClick={()=>setHomePaused(v=>!v)} aria-label={homePaused?'자동재생':'일시정지'}>{homePaused?'▶':'Ⅱ'}</button></div></div>{assigned?<div className="home-guild-status"><GuildRanking/></div>:<><button className={'ticket-launch '+(ticketRegistered?'done':'')} onClick={()=>setTicketModal(true)}><span className="ticket-icon">▣</span><span><b>{ticketRegistered?'티켓이 등록되었습니다!':'오늘 티켓 등록하기'}</b><small>{ticketRegistered?'등록된 입장권으로 GUILD에 참여할 수 있어요.':'입장권을 등록하고 길드전에 참여해보세요!'}</small></span><em>{ticketRegistered?'':'›'}</em></button><button className={'primary guild-entry '+(!ticketRegistered?'disabled':'')} disabled={!ticketRegistered} onClick={enterGuild}>GUILD 참여하기 →</button></>}</div></Layout>,
companions:<Layout title="GUILD JOIN" back onBack={()=>go('home')} noNav><div className="companion-flow"><p className="eyebrow">STEP 1 · COMPANION</p><h1>오늘 함께 온<br/>동행인이 있나요?</h1><p className="companion-intro">같이 온 일행을 연결하면<br/>같은 길드로 배정돼요.</p><div className="companion-connect-card"><b>동행인 연결하기</b><small>최대 4인까지 추가 가능합니다.</small><div className={'companion-methods '+(companionMode==='code'?'is-code':'is-qr')}><i className="method-slider"></i><button className={companionMode==='qr'?'active':''} onClick={()=>{setCompanionMode('qr');setQrView('scan');setMyCompanionCode(makeCompanionCode())}}><span>▦</span><b>QR 코드</b></button><button className={companionMode==='code'?'active':''} onClick={()=>{setCompanionMode('code');setMyCompanionCode(makeCompanionCode())}}><span>▦</span><b>인증코드</b></button></div></div>{companionMode==='qr'?<div className="companion-panel"><div className="companion-tabs"><button className={qrView==='scan'?'active':''} onClick={()=>setQrView('scan')}>상대방 QR 스캔하기</button><button className={qrView==='mine'?'active':''} onClick={()=>{setQrView('mine');setMyCompanionCode(makeCompanionCode())}}>내 QR 보여주기</button></div>{qrView==='scan'?<button className="qr-scanner" onClick={()=>setQrCompanionModal(true)}><i></i><span>상대방의 QR 코드를 스캔해 주세요.</span></button>:<div className="my-qr-only"><div className="real-qr-wrap"><img className="real-qr" src={`/assets/companion-qr/${myCompanionCode}.png`} alt="내 동행인 QR 코드"/></div><small>내 QR 코드</small><b>{myCompanionCode}</b><button onClick={()=>setMyCompanionCode(makeCompanionCode())}>↻ 새 QR 만들기</button></div>}</div>:<div className="companion-panel"><b>상대방 인증코드 입력하기</b><p>동행인에게 받은 영문 + 숫자 8자리 코드를 입력해 주세요.</p><div className="code-row"><input maxLength={8} value={companionCode} onChange={e=>setCompanionCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g,'').slice(0,8))} placeholder="8자리 코드를 입력해주세요."/><button onClick={addTravelCompanion}>요청 보내기</button></div><div className="my-code-box"><small>내 인증코드</small><strong>{myCompanionCode}</strong><button onClick={()=>setMyCompanionCode(makeCompanionCode())}>↻ 새 코드</button></div></div>}{companions.length>0&&<div className="connected-list"><b>연결된 동행인 <purple>{companions.length}명</purple></b>{companions.map((c,i)=><div className="connected-person" key={c+i}><Som size={38}/><div><b>{c}</b><small>● 연결 완료</small></div><button onClick={()=>setRemoveCompanionIndex(i)}>×</button></div>)}</div>}<Button onClick={()=>go('guildReady')}>{companions.length?'다음으로 →':'동행인 없이 계속하기 ›'}</Button></div></Layout>,
guildReady:<Layout title="GUILD JOIN" back onBack={()=>go('companions')} noNav><p className="eyebrow">STEP 2 · GUILD ASSIGN</p><h1>동행인 연결 완료!</h1><p>{companions.length?`${companions.length}명의 동행인과 함께 길드를 배정받아요.`:'혼자서도 길드전에 참여할 수 있어요.'}</p><div className="guild-preview">{guilds.map(g=><div key={g.name}><span className="guild-preview-logo"><img src={g.emojiImage} alt={g.name}/></span><b>{g.name}</b></div>)}</div><div className="soft left"><b>길드 배정 안내</b><p>레니 · 라라 · 잭 길드 중 하나로 랜덤 배정됩니다. 동행인은 같은 길드로 함께 배정돼요.</p></div><Button onClick={assignGuild}>나의 길드 배정받기 →</Button></Layout>,
assign:<Layout title="SOM HUNTERS" noNav><div className="center assign"><p className="eyebrow">GUILD ASSIGNED</p><h1>오늘 함께할 길드가<br/>정해졌어요!</h1><div className="guild-result-logo"><img src={currentGuild.coolImage} alt={currentGuild.name}/></div><p>당신은</p><h2><purple>{currentGuild.name}</purple>에 배정되었어요!</h2><Button onClick={()=>go('home')}>홈에서 길드 현황 보기</Button></div></Layout>,
hunters:<Layout page="home" setPage={go}><div className="title-with-som"><div><p className="eyebrow">HUNTERS HOME</p><h1>오늘의 설렘을<br/>수집해볼까요?</h1></div><Som size={82}/></div><div className="darkcard"><small>TODAY'S GUILD MISSION</small><b>별이 된 정원 · 퍼레이드 광장</b><p>포토스팟에서 특별한 순간을 기록해요.</p></div><h2>지금, 나에게 딱 맞는 Quest!</h2>{quests.slice(0,2).map((q,i)=><QuestCard q={q} i={i} key={q.id}/>)}<Button onClick={()=>go('aiquest')}>AI 추천 Quest 모두 보기 →</Button><Button secondary onClick={()=>go('guild')}>길드 현황 보기</Button></Layout>,
aiquest:<Layout title="AI QUEST" back onBack={()=>go('hunters')}><p className="eyebrow">AI QUEST</p><h1>지금 즐기기 좋은<br/>3가지 활동</h1><div className="chips"><b>전체</b><b>포토</b><b>체험</b><b>공연</b></div>{companions.length>0&&<div className="together-status"><b>함께하는 Quest</b><span>연결 동행인 {companions.length}명 · 참여 {Math.min(companions.length,3)}/{companions.length}</span></div>}{recommendedQuests.map((q,i)=><QuestCard q={q} i={i} key={q.id}/>)}<p className="ai-recommend-note">Quest를 하나 완료하면 AI가 새로운 Quest 1개를 추천해 항상 3개를 보여드려요.</p></Layout>,
ai:<Layout page="home" setPage={go}><div className="title-with-som"><div><h1>오늘의 설렘을<br/>수집해볼까요?</h1></div><Som size={82}/></div><div className="darkcard"><small>TODAY'S GUILD MISSION</small><b>별이 된 정원 (퍼레이드 광장)</b><p>포토스팟에서 특별한 순간을 기록해요.</p></div><h2>지금, 나에게 딱 맞는 Quest!</h2>{quests.slice(0,2).map((q,i)=><QuestCard q={q} i={i} key={q.id}/>)}<Button onClick={()=>go('detail')}>나의 추천 Quest 바로가기 →</Button></Layout>,
detail:<Layout title="QUEST DETAIL" back onBack={()=>go('aiquest')}><div className="scene detailpic image-placeholder"><span>이미지 영역</span></div><div className="chips"><b>포토</b><b>에버랜드가든</b></div><h1>정원 속 숨은<br/>포토스팟을 찾아요</h1><p>가을의 정원에서 예쁜 사진을 찍고 특별한 추억을 남겨보세요.</p><h2 className="purpletext">+30 SOM　+100 XP</h2><div className="soft left"><b>미션 안내</b><p>1. 지도의 포토스팟 위치 확인<br/>2. 포토스팟에서 사진 찍기<br/>3. 인증샷 업로드하기</p></div><Button onClick={()=>go('quests')}>Quest 시작하기</Button></Layout>,
quests:<Layout page="quests" setPage={go} locked={!assigned}><p className="eyebrow">MY QUEST</p><h1>오늘의 작은 모험들</h1><div className="quest-earn-summary"><div><small>TODAY</small><div className="today-score"><span>SOM</span><b>+ {todaySom}</b></div></div><div><small>TODAY</small><div className="today-score"><span>GP</span><b>+ {todayGp}</b></div></div></div><div className="ai-quest-heading"><small>AI가 추천하는</small><h2>오늘의 QUEST</h2></div>{recommendedQuests.map((q,i)=><QuestCard q={q} i={i} key={q.id}/>)}</Layout>,
map:<Layout page="map" setPage={go} locked={!assigned}><div className="map-page-head"><div><p className="eyebrow">LIVE PARK MAP</p><h1>에버랜드 탐험 지도</h1></div><span className={'location-pill '+(nearbySom?'on':'')}>● {nearbySom?'솜 근처 도착':'이동 중'}</span></div><div className="map live-map interactive-map" ref={mapViewportRef} onPointerDown={e=>{e.currentTarget.setPointerCapture?.(e.pointerId);setMapDrag({px:e.clientX,py:e.clientY,x:mapView.x,y:mapView.y})}} onPointerMove={e=>{if(!mapDrag)return;setMapView(v=>({...v,x:mapDrag.x+(e.clientX-mapDrag.px),y:mapDrag.y+(e.clientY-mapDrag.py)}))}} onPointerUp={()=>setMapDrag(null)} onPointerCancel={()=>setMapDrag(null)}>{nearbySom&&<div className="nearby-som-toast">☁️ 근처에 솜이 있어요 !</div>}<div className="map-world" style={{transform:`translate(${mapView.x}px,${mapView.y}px) scale(${mapView.scale})`}}><img className="everland-flat-map" src="/assets/everland-flat-map.webp" alt="SOM HUNTERS 에버랜드 평면 지도" draggable="false"/>{visibleSomSpots.map(spot=>{const canCatch=nearbySom?.id===spot.id;return <button key={spot.id} className={'som-map-marker '+(canCatch?'catchable':'locked')} style={{left:`${spot.x}%`,top:`${spot.y}%`}} onPointerDown={e=>e.stopPropagation()} onClick={()=>{if(!canCatch)return;setSelectedSom(spot);setCaptured(false);resetCloudCapture();setTimeout(()=>go('capture'),180)}} aria-label={`${spot.name} +${spot.reward} SOM`}><img src="/assets/som-spawns/basic-som.png" alt="지도에 나타난 솜"/></button>})}<div className="user-map-marker demo-moving-marker" style={{left:`${demoMapPos.x}%`,top:`${demoMapPos.y}%`}}><i></i><span></span></div></div><div className="map-controls" onPointerDown={e=>e.stopPropagation()} onPointerMove={e=>e.stopPropagation()}><button type="button" onPointerDown={e=>e.stopPropagation()} onClick={e=>{e.stopPropagation();zoomMap(.25)}}>＋</button><button type="button" onPointerDown={e=>e.stopPropagation()} onClick={e=>{e.stopPropagation();zoomMap(-.25)}}>−</button><button type="button" onPointerDown={e=>e.stopPropagation()} onClick={e=>{e.stopPropagation();resetMap()}}>⌖</button></div></div><div className="map-quest-recommend"><div className="map-quest-head"><div><small>NEARBY QUEST</small><h2>현재 위치에서 가능한 Quest</h2></div><button type="button" onClick={()=>go('aiquest')}>전체보기 ›</button></div>{quests.slice(0,2).map((q,i)=><QuestCard q={q} i={i} key={q.id}/>)}</div></Layout>,
discover:<Layout title="SOM DISCOVERY" back onBack={()=>go('map')} noNav><div className="discovery image-placeholder"><span>배경 이미지 영역</span><Som size={190}/></div><div className="bottomsheet center"><h1>앗, SOM을 발견했어요!</h1><p>주변을 자세히 둘러보면<br/>SOM을 놓치지 않고 만날 수 있어요!</p><Button onClick={()=>go('capture')}>포획하러 가기</Button></div></Layout>,
capture:<Layout title="SOM CAPTURE" back onBack={()=>go('map')} noNav><div className="camera capture-camera"><div className="som-reveal">알고보니 {selectedSom?.name||'라일락 솜'}이었다!</div><b>{(cloudEnclosed||cloudTrail.length>=12)?'포획 준비 완료! CATCH를 눌러주세요':'솜이 원 안에 들어오도록 자유롭게 그려주세요'}</b><div ref={cloudZoneRef} className={'cloud-capture-zone '+(cloudEnclosed?'ready':'')} onPointerDown={cloudPointerDown} onPointerMove={cloudPointerMove} onPointerUp={cloudPointerUp} onPointerCancel={cloudPointerUp}><svg className="cloud-drawn-trail" viewBox="0 0 320 360" preserveAspectRatio="none"><polyline points={cloudTrail.map(pt=>`${pt.x},${pt.y}`).join(' ')} /></svg><div className="focus cloud-focus">{selectedSom?<img className="capture-som-image" src={selectedSom.image} alt={selectedSom.name}/>:<Som size={165}/>}</div><div className="cloud-progress-label"><strong>{cloudEnclosed?'✓':`${cloudProgress}%`}</strong><small>{cloudEnclosed?'CATCH READY':'솜을 원 안에 넣어주세요'}</small></div></div><button className={'catch-button '+((cloudEnclosed||cloudTrail.length>=12)?'enabled':'')} disabled={!(cloudEnclosed||cloudTrail.length>=12)} aria-label="솜 잡기" onClick={()=>{if(!(cloudEnclosed||cloudTrail.length>=12))return;if(!captured){setSom(s=>s+10);setTodaySom(v=>v+10);setTodayGp(v=>v+50);if(selectedSom)setCaughtSomIds(ids=>ids.includes(selectedSom.id)?ids:[...ids,selectedSom.id])}setCaptured(true);go('complete')}}>CATCH</button></div></Layout>,
complete:<Layout title="CAPTURE COMPLETE" noNav><div className="center complete"><h1>{selectedSom?.name||'기본 솜'}과<br/>친구가 되었어요!</h1>{selectedSom?<img className="complete-caught-som" src={selectedSom.image} alt={selectedSom.name}/>:<Som size={190}/>}<div className="reward"><b>+{10} SOM</b><b>+50 GP</b></div><Button onClick={()=>go('results')}>길드전 결과 확인하기</Button><Button secondary onClick={()=>go('map')}>계속 탐험하기</Button></div></Layout>,
guild:<Layout page="guild" setPage={go}><p className="eyebrow">GUILD BATTLE</p>{!assigned?<><h1>오늘의 길드전에<br/>참여해볼까요?</h1><div className="guild-start"><p>홈에서 오늘 티켓을 등록한 뒤<br/>동행인을 연결하고 길드를 배정받아주세요.</p></div><Button onClick={()=>go('home')}>홈에서 시작하기 →</Button></>:<><div className="guild-head"><div><h1>{currentGuild.name}</h1><p>오늘도 함께 순위를 올려봐요!</p></div><span className="rank-badge">현재 {guildScores.find(g=>g.name===currentGuild.name)?.rank}위</span></div><div className="my-guild-card"><span className="guild-emoji guild-logo-large"><img src={currentGuild.emojiImage} alt={currentGuild.name}/></span><div><small>MY GUILD</small><b>{currentGuild.name}</b><strong>{guildScores.find(g=>g.name===currentGuild.name)?.score} GP</strong></div></div><h2>실시간 길드 랭킹</h2><div className="ranking">{guildScores.map(g=><div className={'rank-row '+(g.name===currentGuild.name?'mine':'')} key={g.name}><strong>{g.rank}</strong><span className="guild-logo-small"><img src={g.emojiImage} alt={g.name}/></span><div><b>{g.name}</b><small>{g.name===currentGuild.name?'내 길드 · ':''}오늘의 탐험 점수</small></div><em>{g.score} GP</em></div>)}</div><div className="soft left"><b>나의 오늘 기여도 <span className="purpletext">{captured?60:40} GP</span></b><p>퀘스트를 완료할수록 길드 점수가 올라가요.</p></div><Button onClick={()=>go('quests')}>길드 점수 올리러 가기</Button></>}</Layout>,
results:<Layout page="results" setPage={go}><p className="eyebrow">MY REWARD</p><h1>리워드</h1><p className="results-intro">오늘의 길드전 결과와 지금까지 모은 컬렉션을 한눈에 확인해보세요.</p><section className="reward-section"><div className="reward-section-head"><div><small>TODAY'S GUILD BATTLE</small><h2>오늘의 길드전 결과</h2></div><span className="reward-date">TODAY</span></div><div className="battle-summary-block">{battleRounds.map(r=>{const winnerGuild=guilds.find(g=>g.name===r.winner);return <div className={'battle-mini '+r.status} key={r.round}><div className="battle-round-head"><span>{r.round}차전</span><em>{r.status==='completed'?'종료 ✓':r.status==='active'?'● 진행중':'예정'}</em></div><small className="round-time">{r.time}</small>{r.status==='completed'?<><div className="battle-winner-logo">{winnerGuild&&<img src={winnerGuild.emojiImage} alt={winnerGuild.name}/>}</div><b className="battle-guild-name">{r.winner}</b><strong className="winner-label">WINNER</strong><small>리워드 지급 완료</small></>:r.status==='active'?<><div className="battle-symbol">⚔️</div><strong className="battle-word">BATTLE</strong><b className="battle-live-text">현재 진행 중</b><strong className="battle-timer">02:34:21</strong><small className="timer-label">종료까지 남은 시간</small></>:<><div className="battle-symbol pending-lock">🔒</div><strong className="battle-status pending-text">미진행</strong></>}</div>})}</div></section><section className="reward-section badge-section"><div className="collection-tabs"><button className={collectionTab==='som'?'active':''} onClick={()=>setCollectionTab('som')}>솜 도감</button><button className={collectionTab==='badge'?'active':''} onClick={()=>setCollectionTab('badge')}>뱃지 도감</button></div>{collectionTab==='som'?<><div className="som-collection-showcase"><div className="som-collection-title"><div><small>SOM COLLECTION</small><h2>나의 솜 도감 ☁</h2></div><span>♙ 수집한 솜 3　›</span></div><div className="som-carousel"><button className="som-arrow" onClick={()=>setSomCollectionPage(p=>(p+2)%3)}>‹</button>{somCollectionPage===0?<><div className="som-display-card"><div className="som-pedestal purple"><img src="/assets/som-spawns/basic-som.png" alt="기본 솜"/></div><b>기본 솜</b></div><div className="som-display-card featured"><i>NEW</i><div className="som-pedestal orange"><img src="/assets/som-spawns/autumn-som.png" alt="가을 솜"/></div><b>가을 솜</b></div><div className="som-display-card"><div className="som-pedestal pink"><img src="/assets/som-spawns/collab-som.png" alt="헬로키티 솜"/></div><b>헬로키티 솜</b></div></>:<><div className="som-display-card mystery"><div className="mystery-som">?</div><b>???</b></div><div className="som-display-card mystery featured"><div className="mystery-som">?</div><b>???</b></div><div className="som-display-card mystery"><div className="mystery-som">?</div><b>???</b></div></>}<button className="som-arrow" onClick={()=>setSomCollectionPage(p=>(p+1)%3)}>›</button></div><div className="som-dots">{[0,1,2].map(i=><b key={i} className={somCollectionPage===i?'active':''}></b>)}</div></div></>:<><div className="reward-section-head"><div><small>BADGE COLLECTION</small><h2>나의 뱃지 도감</h2></div></div><div className="badge-grid">{[
{name:'탐험 새싹',img:'/assets/badges/explore-sprout.png',earned:true},
{name:'추억',img:'/assets/badges/memory.png',earned:true},
{name:'함께',img:'/assets/badges/together.png',earned:true},
{name:'솜 헌터',earned:false},{name:'미식 탐험가',earned:false},{name:'시크릿 뱃지',earned:false}
].map(item=><div className={'badge-card '+(!item.earned?'badge-locked':'')} key={item.name}>{item.earned?<div className="badge-medal earned"><img src={item.img} alt={item.name}/></div>:<div className="badge-medal locked">?</div>}<b>{item.name}</b></div>)}</div></>}</section></Layout>,
shop:<SomShop som={som} setPage={go} />};

const q=selectedQuest;
return <>{screens[page]||screens.home}{ticketModal&&<div className="modalback ticket-modal-back" onClick={()=>setTicketModal(false)}><section className="missionmodal ticket-modal" onClick={e=>e.stopPropagation()}><button className="modalclose" onClick={()=>setTicketModal(false)}>×</button><p className="eyebrow">TODAY TICKET</p><h2>티켓 등록하기</h2><p>에버랜드 입장 티켓을 등록하고<br/>SOM HUNTERS를 시작해보세요!</p><button className="ticket-import-btn" onClick={loadMyTicket}><span>🎟</span><div><b>내 티켓 정보 불러오기</b><small>에버랜드 앱에 등록된 티켓을 불러와요.</small></div><em>›</em></button><div className="ticket-divider"><span>또는 직접 등록</span></div><div className="ticket-mode-tabs"><button className={ticketMode==='scan'?'active':''} onClick={()=>setTicketMode('scan')}>▦ QR / 바코드 인식</button><button className={ticketMode==='code'?'active':''} onClick={()=>setTicketMode('code')}>⌨ 입장 코드 입력</button></div>{ticketMode==='code'?<><input className="ticket-code-input" inputMode="numeric" maxLength={16} value={ticket} onChange={e=>setTicket(e.target.value.replace(/\D/g,'').slice(0,16))} placeholder="입장 코드 16자리 입력"/><Button onClick={registerTicket}>등록하기</Button></>:<><div className="barcode-frame"><span>▥</span><b>QR코드 또는 바코드를<br/>카메라로 스캔해 주세요.</b></div><label className="primary uploadbtn camera-open">▣ 카메라 열기<input type="file" accept="image/*" capture="environment" onChange={()=>{setTicket('1234567890123456');setTicketMode('code')}}/></label></>}</section></div>}{ticketSuccess&&<div className="modalback"><section className="missionmodal ticket-success-modal"><div className="success-check">✓</div><p className="eyebrow">TICKET COMPLETE</p><h2>티켓 등록 완료!</h2><p>오늘의 입장권이 정상적으로 등록되었어요.<br/>함께 온 동행인을 연결해볼까요?</p><Button onClick={()=>{setTicketSuccess(false);enterGuild()}}>동행인 등록으로 이동 →</Button></section></div>}{qrCompanionModal&&<div className="modalback" onClick={()=>setQrCompanionModal(false)}><section className="missionmodal" onClick={e=>e.stopPropagation()}><button className="modalclose" onClick={()=>setQrCompanionModal(false)}>×</button><p className="eyebrow">COMPANION QR</p><h2>QR로 동행인 추가하기</h2><div className="barcode-frame"><span>▦</span><b>동행인의 QR을 카메라로<br/>스캔해 주세요.</b></div><label className="primary uploadbtn camera-open">▣ 카메라 열기<input type="file" accept="image/*" capture="environment" onChange={()=>{setCompanions(x=>[...x,'보라솜']);
setQrCompanionModal(false)}}/></label></section></div>}{removeCompanionIndex!==null&&<div className="modalback" onClick={()=>setRemoveCompanionIndex(null)}><section className="missionmodal companion-remove-modal" onClick={e=>e.stopPropagation()}><button className="modalclose" onClick={()=>setRemoveCompanionIndex(null)}>×</button><p className="eyebrow">COMPANION</p><h2>동행인을 삭제하시겠습니까?</h2><p>연결을 삭제하면 해당 동행인과의 길드 연결 정보가 해제됩니다.</p><div className="request-actions"><Button secondary onClick={()=>setRemoveCompanionIndex(null)}>취소</Button><Button onClick={()=>{setCompanions(x=>x.filter((_,i)=>i!==removeCompanionIndex));
setRemoveCompanionIndex(null)}}>삭제하기</Button></div></section></div>}{incoming&&page==='companions'&&<div className="modalback"><section className="missionmodal companion-request"><p className="eyebrow">COMPANION REQUEST</p><h2>김솜님이 동행인으로 추가하셨습니다.</h2><p>동행 요청을 수락하시겠습니까?</p><div className="request-actions"><Button secondary onClick={()=>{setCompanions(x=>x.filter(c=>c!=='김솜님'));setIncoming(false)}}>거절</Button><Button onClick={()=>{setCompanions(x=>x.includes('김솜님')?x:[...x,'김솜님']);
setIncoming(false)}}>수락하기</Button></div></section></div>}{q&&<div className="modalback" onClick={closeQuest}><section className="missionmodal" onClick={e=>e.stopPropagation()}><button className="modalclose" onClick={closeQuest}>×</button><p className="eyebrow">MISSION CHECK</p><h2>{q.detailTitle||q.title}</h2><p>{q.desc}</p><div className="missionreward"><strong>+70 SOM</strong><strong>+350 GP</strong></div><div className="mission-guide"><b>수행 방법</b><p>{q.how}</p></div>{q.type==='discover'&&<div className="proofbox photo-proof"><b>📷 사진 제출</b><p>갤러리에서 촬영한 사진을 선택해 제출해주세요.</p><button className="photo-picker" onClick={()=>setPhotoSelected(true)}>{photoSelected?<><img src="/assets/demo-rose-garden.jpg" alt="장미정원 데모 인증 사진"/><span>✓ 사진이 선택되었어요</span></>:<><span className="photo-plus">＋</span><strong>갤러리에서 사진 선택</strong><small>데모에서는 장미정원 사진이 자동으로 첨부돼요.</small></>}</button><button className="photo-submit-btn" disabled={!photoSelected} onClick={()=>{if(!photoSelected)return;if(!completedQuests.includes(q.id)){setCompletedQuests(x=>[...x,q.id]);setTodaySom(v=>v+70);setTodayGp(v=>v+350);setSom(v=>v+70)}setSelectedQuest(null);setPhotoSelected(false);setQuestComplete({message:'사진이 제출되었어요',submitted:true,photo:true});setTimeout(()=>{setQuestToast('사진 인증이 완료되었어요 ✓');setTimeout(()=>setQuestToast(''),3000)},1800)}}>제출</button><p className="ai-photo-note">AI가 제출한 사진을 확인해요. 인증까지 잠시 시간이 걸릴 수 있어요.</p></div>}{q.type==='explore'&&<div className="proofbox"><b>📍 위치 인증하기</b><Button onClick={shareLocation}>제출</Button></div>}{q.type==='reward'&&<div className="proofbox"><b>🧾 POS 자동 인증</b><p>회원 코드로 SOM을 적립하면 결제 내역 확인 후 자동 완료됩니다.</p><Button onClick={()=>finishQuest('퀘스트를 완료했어요!')}>제출</Button></div>}{q.type==='together'&&<div className="proofbox together-quiz"><div className="together-participation"><b>연결된 동행인</b><span>{companions.length}명</span></div>{togetherMode==='answer'?<><h3>정답을 입력하시오.</h3><p className="hint-wait">동행인에게 힌트가 제공됩니다.</p><div className="answer-row"><input value={togetherAnswer} onChange={e=>setTogetherAnswer(e.target.value)} placeholder="정답을 입력해주세요"/><button onClick={()=>{const a=togetherAnswer.replace(/\s/g,'').toLowerCase();if(a==='모니모rush'||a==='모니모러쉬')finishQuest('함께 퀘스트를 완료했어요!');else setProof(x=>({...x,[q.id]:'정답을 다시 확인해주세요.'}))}}>제출</button></div>{proof[q.id]&&<p className="answer-error">{proof[q.id]}</p>}</>:<><p className="hint-role-label">동행인에게 전달된 힌트</p><div className="together-hint-only"><small>HINT</small><strong>에버랜드 대표 롤러코스터</strong><p>이 힌트를 정답을 입력하는 동행인에게 알려주세요.</p></div></>}</div>}<Button secondary onClick={closeQuest}>닫기</Button></section></div>}{questComplete&&<div className="modalback"><section className="missionmodal quest-complete-modal"><div className="success-check">✓</div><p className="eyebrow">{questComplete.submitted?'SUBMISSION COMPLETE':'QUEST COMPLETE'}</p><h2>{questComplete.message}</h2>{!questComplete.submitted&&<div className="complete-reward"><small>REWARD</small><div><strong>+70 SOM</strong><strong>+350 GP</strong></div></div>}<Button onClick={closeQuestComplete}>확인</Button></section></div>}{questToast&&<div className="quest-top-toast" onClick={()=>setQuestToast('')}>🔔 {questToast}</div>}</>}
