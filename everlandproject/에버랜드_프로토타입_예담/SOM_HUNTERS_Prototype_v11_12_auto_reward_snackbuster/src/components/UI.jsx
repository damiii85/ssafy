import React from 'react';
import {
  Home,
  Map,
  Gamepad2,
  Trophy,
  ShoppingBag,
  ChevronLeft,
  Bell,
} from 'lucide-react';

export function Som({ size = 96, className = '' }) {
  return (
    <img
      className={`som-img ${className}`}
      src="/assets/lilac-som.png"
      style={{ width: size }}
      alt="라일락솜"
    />
  );
}

export function Header({ title = 'SOM HUNTERS', back = false, onBack }) {
  return (
    <header>
      {back ? (
        <button className="icon" onClick={onBack} type="button" aria-label="뒤로가기">
          <ChevronLeft />
        </button>
      ) : (
        <b className="brand">SOM HUNTERS</b>
      )}
      <b className="head-title">{back ? title : ''}</b>
      {back ? <span className="head-space" /> : <Bell size={18} />}
    </header>
  );
}

export function Button({ children, onClick, secondary = false }) {
  return (
    <button
      className={`primary ${secondary ? 'secondary' : ''}`}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

export function Nav({ page, setPage, locked = false }) {
  const items = [
    ['home', Home, '홈'],
    ['quests', Gamepad2, '퀘스트'],
    ['map', Map, '지도'],
    ['results', Trophy, '결과'],
    ['shop', ShoppingBag, '솜샵'],
  ];

  return (
    <nav>
      {items.map(([id, Icon, title]) => {
        const isLocked = locked && (id === 'quests' || id === 'map');
        return (
          <button
            key={id}
            type="button"
            disabled={isLocked}
            className={`${page === id ? 'active ' : ''}${isLocked ? 'nav-locked' : ''}`}
            onClick={() => {
              if (!isLocked) setPage(id);
            }}
          >
            <Icon />
            <small>{title}{isLocked ? ' 🔒' : ''}</small>
          </button>
        );
      })}
    </nav>
  );
}

export function Layout({
  children,
  page,
  setPage,
  title,
  back = false,
  onBack,
  noNav = false,
  locked = false,
}) {
  return (
    <main className="phone">
      <Header title={title} back={back} onBack={onBack} />
      <section className="content">{children}</section>
      {!noNav && <Nav page={page} setPage={setPage} locked={locked} />}
    </main>
  );
}
