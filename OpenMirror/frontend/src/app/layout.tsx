import type { Metadata } from "next";
import Link from "next/link";
import "@fontsource-variable/newsreader/opsz.css";
import "@fontsource-variable/newsreader/opsz-italic.css";
import "@fontsource-variable/instrument-sans/index.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./globals.css";
import { ThemeToggle } from "@/components/theme-toggle";
import { TooltipProvider } from "@/components/ui/tooltip";

export const metadata: Metadata = {
  title: "OpenMirror",
  description: "Private, local-first conversation intelligence for WhatsApp exports.",
  robots: { index: false, follow: false },
};

const themeScript = `(function(){try{var t=localStorage.getItem("openmirror-theme");var d=t?t==="dark":window.matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.classList.toggle("dark",d);document.documentElement.dataset.theme=d?"dark":"light"}catch(e){}})();`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen">
        <TooltipProvider delayDuration={150}>
          <header className="border-b border-rule">
            <div className="mx-auto flex h-14 max-w-[1240px] items-center justify-between px-4 sm:px-6">
              <Link href="/" className="flex items-baseline gap-2">
                <span className="display text-[1.3rem]">OpenMirror</span>
                <span className="kicker hidden sm:inline">Local · Private · Evidence-first</span>
              </Link>
              <div className="flex items-center gap-1">
                <span className="kicker mr-2 hidden items-center gap-1.5 md:inline-flex">
                  <span className="inline-block size-1.5 rounded-full bg-[var(--series-3)]" aria-hidden />
                  Offline mode · no AI
                </span>
                <ThemeToggle />
              </div>
            </div>
          </header>
          {children}
        </TooltipProvider>
      </body>
    </html>
  );
}
