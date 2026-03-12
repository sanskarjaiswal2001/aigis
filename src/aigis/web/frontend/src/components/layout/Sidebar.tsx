import { LayoutDashboard, History, ClipboardList, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", Icon: LayoutDashboard },
  { to: "/runs", label: "Runs", Icon: History },
  { to: "/audit", label: "Audit Log", Icon: ClipboardList },
  { to: "/settings", label: "Settings", Icon: Settings },
];

export function Sidebar() {
  return (
    <nav className="w-44 bg-neutral-950 border-r border-neutral-800 flex flex-col py-3 gap-0.5 shrink-0">
      {links.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            `flex items-center gap-2.5 px-4 py-2 text-xs font-medium transition-colors ${
              isActive
                ? "text-neutral-100 bg-neutral-800"
                : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-900"
            }`
          }
        >
          {({ isActive }) => (
            <>
              <Icon size={14} className={isActive ? "text-red-500" : ""} />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
