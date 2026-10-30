import { useEffect, useState } from 'react';
import { CloudRain, FlaskConical, Home as HomeIcon, MessageCircle, Sprout } from 'lucide-react';
import Home from './pages/Home';
import Chat from './pages/Chat';
import Dosage from './pages/Dosage';
import Weather from './pages/Weather';

const PAGES = [
  { id: 'home', en: 'My Farm', ta: 'என் வயல்', Icon: HomeIcon, Page: Home },
  { id: 'chat', en: 'Ask Uzhavan', ta: 'கேளுங்கள்', Icon: MessageCircle, Page: Chat },
  { id: 'dosage', en: 'Dose Calculator', ta: 'அளவு கணிப்பு', Icon: FlaskConical, Page: Dosage },
  { id: 'weather', en: 'Weather', ta: 'வானிலை', Icon: CloudRain, Page: Weather },
] as const;

type PageId = (typeof PAGES)[number]['id'];

const pageFromHash = (): PageId => {
  const id = window.location.hash.replace('#/', '');
  return (PAGES.find((p) => p.id === id)?.id ?? 'home') as PageId;
};

export function go(page: PageId) {
  window.location.hash = `#/${page}`;
}

export default function App() {
  const [page, setPage] = useState<PageId>(pageFromHash);

  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const Current = PAGES.find((p) => p.id === page)!.Page;

  return (
    <div className="min-h-screen pb-24 md:pb-10">
      <header className="sticky top-0 z-20 border-b border-soil-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <a href="#/home" className="flex items-center gap-2.5">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-leaf-700 text-white">
              <Sprout className="h-6 w-6" aria-hidden />
            </span>
            <span className="leading-tight">
              <span className="block text-lg font-extrabold text-soil-900">
                Uzhavan <span className="tamil font-bold text-leaf-700">உழவன்</span>
              </span>
              <span className="block text-xs text-soil-700">Farm advisor · பண்ணை ஆலோசகர்</span>
            </span>
          </a>
          <nav className="hidden gap-1 md:flex" aria-label="Main">
            {PAGES.map(({ id, en, Icon }) => (
              <a
                key={id}
                href={`#/${id}`}
                aria-current={page === id ? 'page' : undefined}
                className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
                  page === id ? 'bg-leaf-700 text-white' : 'text-soil-700 hover:bg-soil-100'
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden /> {en}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <Current />
      </main>

      {/* Bottom tab bar on phones */}
      <nav
        className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t border-soil-200 bg-white md:hidden"
        aria-label="Main"
      >
        {PAGES.map(({ id, en, ta, Icon }) => (
          <a
            key={id}
            href={`#/${id}`}
            aria-current={page === id ? 'page' : undefined}
            className={`flex flex-col items-center gap-0.5 py-2 text-[11px] font-semibold ${
              page === id ? 'text-leaf-700' : 'text-soil-700'
            }`}
          >
            <Icon className="h-6 w-6" aria-hidden />
            {en.split(' ')[0]}
            <span className="tamil text-[10px] leading-none">{ta}</span>
          </a>
        ))}
      </nav>
    </div>
  );
}
