import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { useTheme } from "../theme";
import Icon from "./Icon";

export default function Layout() {
  const { user, logout } = useAuth();
  const [theme, toggle] = useTheme();
  const nav = useNavigate();
  return (
    <>
      <header className="topbar">
        <div className="brand"><span className="logo-mark"><Icon name="chart" size={18} /></span>TradeDesk</div>
        <nav>
          <NavLink to="/" end><Icon name="wallet" size={16} /> Portfolio</NavLink>
          <NavLink to="/picks"><Icon name="spark" size={16} /> AI picks</NavLink>
        </nav>
        <div className="who">
          <button className="icon-btn" onClick={toggle} aria-label="Toggle dark mode" title="Toggle dark mode">
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
          <span className="avatar" title={user.email}>{user.name.trim()[0]?.toUpperCase()}</span>
          <button className="icon-btn" aria-label="Sign out" title="Sign out" onClick={async () => { await logout(); nav("/login"); }}>
            <Icon name="logout" />
          </button>
        </div>
      </header>
      <main className="page"><Outlet /></main>
    </>
  );
}
