import {
  ClipboardList,
  Building2,
  MessageSquareText,
  LayoutDashboard,
  LogOut,
  PackageSearch,
  PhoneCall,
  PanelsTopLeft,
  Activity,
} from "lucide-react";
import { useEffect } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "@/modules/auth/auth-provider";
import { ErrorNotice } from "@/shared/ui/error-notice";
import { Logo } from "@/shared/ui/logo";

const navigation = [
  { href: "/admin", label: "Огляд", icon: LayoutDashboard },
  { href: "/admin/products", label: "Товари", icon: PackageSearch },
  { href: "/admin/orders", label: "Замовлення", icon: ClipboardList },
  { href: "/admin/leads", label: "Звернення", icon: PhoneCall },
  { href: "/admin/reviews", label: "Відгуки", icon: MessageSquareText },
  { href: "/admin/activity", label: "Активність", icon: Activity },
  { href: "/admin/companies", label: "Компанії", icon: Building2 },
  { href: "/admin/custom-boards", label: "Щити", icon: PanelsTopLeft },
];

export function AdminShell() {
  const { status, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  useEffect(() => {
    if (status === "guest") navigate("/admin/login", { replace: true });
  }, [navigate, status]);

  if (status !== "authenticated") {
    if (status === "unavailable") {
      return (
        <ErrorNotice
          error={null}
          fallback="Не вдалося перевірити сесію. Оновіть сторінку."
        />
      );
    }
    return <div className="admin-loader">Перевіряємо сесію…</div>;
  }

  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <Logo inverse />
        <div className="admin-sidebar__caption">Панель керування</div>
        <nav>
          {navigation.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/admin" ? pathname === href : pathname.startsWith(href);
            return (
              <Link data-active={active || undefined} to={href} key={href}>
                <Icon size={18} /> {label}
              </Link>
            );
          })}
        </nav>
        <div className="admin-sidebar__bottom">
          <Link to="/">← До магазину</Link>
          <button
            onClick={async () => {
              await logout();
              navigate("/admin/login", { replace: true });
            }}
            type="button"
          >
            <LogOut size={17} /> Вийти
          </button>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
