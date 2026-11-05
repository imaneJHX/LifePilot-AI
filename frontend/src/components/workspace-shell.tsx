"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowUpRight,
  BookOpen,
  CircleHelp,
  GraduationCap,
  LayoutGrid,
  MessageSquare,
  SlidersHorizontal,
} from "lucide-react";
import { Brand, ErrorNotice, ThemeToggle } from "./ui";
import { useProfile } from "./providers";

const links = [
  { href: "/dashboard", label: "My overview", icon: LayoutGrid },
  { href: "/profile", label: "My profile", icon: SlidersHorizontal },
  { href: "/explore", label: "Explore programs", icon: GraduationCap },
  { href: "/assistant", label: "AI assistant", icon: MessageSquare },
];

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname().replace(/\/+$/, "") || "/";
  const { profile, error, retry } = useProfile();
  const title =
    links.find((link) => pathname.startsWith(link.href))?.label ?? "Workspace";
  return (
    <div className="workspace">
      <aside className="sidebar">
        <Brand />
        <div className="workspace-label">YOUR NEXT CHAPTER</div>
        <nav aria-label="Main navigation">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`nav-link ${pathname === href ? "active" : ""}`}
              aria-current={pathname === href ? "page" : undefined}
            >
              <Icon size={19} />
              <span>{label}</span>
              {href === "/assistant" && <span className="nav-new">AI</span>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <BookOpen size={22} />
            <h3>A little clarity goes a long way.</h3>
            <p>Your priorities. A clearer path forward.</p>
            <Link href="/profile">
              Shape your profile <ArrowUpRight size={15} />
            </Link>
          </div>
          <Link href="/methodology" className="nav-link">
            <CircleHelp size={18} />
            How ranking works
          </Link>
          <div className="sidebar-person">
            <span className="avatar">
              {profile?.name.slice(0, 1).toUpperCase() ?? "Y"}
            </span>
            <div>
              <strong>{profile?.name ?? "Your workspace"}</strong>
              <small>Personal study planner</small>
            </div>
            <span className="status-dot" />
          </div>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="workspace-header">
          <div className="mobile-brand">
            <Brand compact />
          </div>
          <div className="breadcrumb">
            Workspace <span>/</span> <strong>{title}</strong>
          </div>
          <div className="header-actions">
            <span className="private-label">
              <span className="status-dot" />
              Local demo
            </span>
            <ThemeToggle />
          </div>
        </header>
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={pathname === href ? "active" : ""}
              aria-current={pathname === href ? "page" : undefined}
            >
              <Icon size={18} />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
        <main id="main-content" className="workspace-content">
          {error && <ErrorNotice message={error} retry={retry} />}
          {children}
          <footer className="workspace-footer">
            <p className="catalog-footer-note">Demo recommendations use fictional programs. Real records show their review status.</p>
            <span>Made for thoughtful decisions.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
