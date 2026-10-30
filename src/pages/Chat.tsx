import { useEffect, useRef, useState } from 'react';
import { SendHorizontal, Sprout, User } from 'lucide-react';
import { api, type ChatReply } from '../api';
import { AdviceCard, ErrorNote, Spinner, TraceSteps, UrgencyChip } from '../components/ui';

type Message =
  | { role: 'user'; text: string }
  | { role: 'bot'; reply: ChatReply }
  | { role: 'error'; text: string };

const SUGGESTIONS = [
  'Should I irrigate my 1 acre tomato field today?',
  'My 2 acre paddy is at tillering stage. What should I do?',
  'How much fertilizer does my flowering tomato need?',
  'Will rain come in the next 2 days?',
  'Which crops suit my soil?',
];

function Avatar({ bot }: { bot?: boolean }) {
  return (
    <span
      className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${
        bot ? 'bg-leaf-700 text-white' : 'bg-soil-200 text-soil-800'
      }`}
      aria-hidden
    >
      {bot ? <Sprout className="h-5 w-5" /> : <User className="h-5 w-5" />}
    </span>
  );
}

function Welcome() {
  return (
    <div className="flex gap-3">
      <Avatar bot />
      <div className="card max-w-2xl space-y-2 p-4">
        <p className="text-lg font-bold text-soil-900">Vanakkam! I am Uzhavan, your farm advisor.</p>
        <p className="tamil text-lg font-semibold text-leaf-800">வணக்கம்! நான் உழவன், உங்கள் பண்ணை ஆலோசகர்.</p>
        <p className="text-soil-800">
          I read your soil sensor, check the rain forecast and tell you exactly how much water and fertilizer to give.
          Ask me in simple words, for example about watering, fertilizer or rain.
        </p>
        <p className="tamil text-soil-800">
          உங்கள் மண் சென்சார், மழை முன்னறிவிப்பு ஆகியவற்றைப் பார்த்து, எவ்வளவு நீர், எவ்வளவு உரம் தேவை என்று சொல்கிறேன்.
          நீர், உரம் அல்லது மழை பற்றி எளிய வார்த்தைகளில் கேளுங்கள்.
        </p>
      </div>
    </div>
  );
}

function BotReply({ reply }: { reply: ChatReply }) {
  const p = reply.parsed;
  const structured = p.advice_en || p.advice_ta;
  return (
    <div className="flex gap-3">
      <Avatar bot />
      <div className="card w-full max-w-4xl space-y-3 p-4">
        {p.urgency && <UrgencyChip urgency={p.urgency} />}
        {structured ? (
          <AdviceCard en={p.advice_en} ta={p.advice_ta} disclaimer={p.disclaimer} />
        ) : (
          <p className="whitespace-pre-line text-lg">{reply.answer}</p>
        )}
        <TraceSteps steps={reply.trace} />
      </div>
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, busy]);

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', text: q }]);
    setBusy(true);
    try {
      const reply = await api.chat(q);
      setMessages((m) => [...m, { role: 'bot', reply }]);
    } catch (e) {
      setMessages((m) => [...m, { role: 'error', text: (e as Error).message }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <div>
        <h1 className="text-2xl font-extrabold text-soil-900">
          Ask Uzhavan <span className="tamil text-xl text-leaf-700">· உழவனிடம் கேளுங்கள்</span>
        </h1>
        <p className="text-soil-700">
          Same advisor as the command line: it reads your sensor data, checks the weather and computes doses.
        </p>
      </div>

      <div className="space-y-4">
        <Welcome />
        {messages.map((m, i) =>
          m.role === 'user' ? (
            <div key={i} className="flex justify-end gap-3">
              <p className="max-w-xl rounded-2xl rounded-tr-sm bg-soil-700 px-4 py-3 text-lg text-white">{m.text}</p>
              <Avatar />
            </div>
          ) : m.role === 'bot' ? (
            <BotReply key={i} reply={m.reply} />
          ) : (
            <ErrorNote key={i} message={m.text} />
          ),
        )}
        {busy && (
          <div className="flex gap-3">
            <Avatar bot />
            <div className="card p-4">
              <Spinner label="Checking your soil, the weather and the doses… (about 10 seconds)" />
              <p className="tamil mt-1 text-sm text-soil-700">மண், வானிலை, அளவுகளைச் சரிபார்க்கிறேன்…</p>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => send(s)}
              className="rounded-full border border-leaf-200 bg-leaf-50 px-4 py-2 text-left text-sm font-semibold text-leaf-800 hover:bg-leaf-100"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="sticky bottom-20 flex gap-2 rounded-2xl border border-soil-200 bg-white p-2 shadow-md md:bottom-4"
      >
        <label htmlFor="chat-input" className="sr-only">
          Your question
        </label>
        <input
          id="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question… / உங்கள் கேள்வி…"
          maxLength={500}
          className="min-w-0 flex-1 rounded-xl px-3 py-3 text-lg outline-none placeholder:text-soil-500 focus:bg-soil-50"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="flex items-center gap-2 rounded-xl bg-leaf-700 px-5 py-3 font-bold text-white hover:bg-leaf-800 disabled:opacity-50"
        >
          <SendHorizontal className="h-5 w-5" aria-hidden />
          <span className="hidden sm:inline">Ask</span>
        </button>
      </form>
    </div>
  );
}
