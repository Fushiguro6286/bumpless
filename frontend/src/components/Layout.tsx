import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { AboutModal } from "./About";

const NAV = [
  { to: "/", label: "New migration", end: true },
  { to: "/runs", label: "Runs" },
  { to: "/radar", label: "Radar" },
  { to: "/benchmark", label: "Benchmark" },
  { to: "/recipes", label: "Recipes" },
  { to: "/status", label: "Status" },
];

export function Logo() {
  return (
    <svg aria-hidden viewBox="0 0 32 32" className="size-7">
      <rect width="32" height="32" rx="8" className="fill-ink-800" />
      <path d="M6 21c4 0 5-10 10-10s6 10 10 10" fill="none" stroke="#34d399" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export default function Layout() {
  const [about, setAbout] = useState(false);
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-ink-800 focus:px-3 focus:py-2">Skip to content</a>
      <header className="sticky top-0 z-30 border-b border-ink-700 bg-ink-900/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <Logo /> <span className="text-lg">Bumpless</span>
          </NavLink>
          <nav aria-label="Main" className="flex flex-1 flex-wrap gap-1 text-sm">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end}
                className={({ isActive }) => `rounded-md px-3 py-1.5 transition-colors ${isActive ? "bg-ink-800 text-ink-100" : "text-ink-300 hover:text-ink-100"}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <button onClick={() => setAbout(true)} className="rounded-md px-3 py-1.5 text-sm text-ink-300 hover:text-ink-100">About</button>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
        <Outlet />
      </main>
      <footer className="border-t border-ink-700 py-6 text-center text-xs text-ink-400">
        Powered by <span className="text-ink-300">NVIDIA Nemotron</span> on <span className="text-ink-300">Nebius Token Factory</span> · Search by <span className="text-ink-300">Tavily</span> · MIT licensed
      </footer>
      {about && <AboutModal onClose={() => setAbout(false)} />}
    </div>
  );
}
