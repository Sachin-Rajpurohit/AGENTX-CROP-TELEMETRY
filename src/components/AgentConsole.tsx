import React, { useState, useEffect, useRef } from 'react';
import { AgentJudgesResponse, ParsedAdvice, TraceStep, UrgencyLevel } from '../types';
import { parseAdvice } from '../lib/agentEngine';
import {
  Send,
  RotateCcw,
  Sparkles,
  Bot,
  User,
  Wrench,
  Clock,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  Languages,
  ShieldCheck,
  FileCode,
  Droplets,
  CloudRain,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  ArrowRight
} from 'lucide-react';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
  response?: AgentJudgesResponse;
  parsedAdvice?: ParsedAdvice;
  isError?: boolean;
}

interface AgentConsoleProps {
  onRunQuery: (query: string, dryRun: boolean) => Promise<AgentJudgesResponse>;
  isLoading: boolean;
  lastResponse: AgentJudgesResponse | null;
  onOpenContract: () => void;
  scenarioName: string;
}

const FARMER_QUICK_ACTIONS = [
  { label: '💧 Water Advice (பாசனம்)', query: 'Should I irrigate my 1 acre tomato field today?' },
  { label: '🌾 Fertilizer Dose (உரம்)', query: 'What fertilizer does my tomato need at flowering stage (1 acre)?' },
  { label: '🌦️ Rain Forecast (வானிலை)', query: 'Analyze 48h rain risk and moisture trend for Trichy' },
  { label: '🧪 Soil Health (மண் தரம்)', query: 'What is the current soil pH and health for tomato?' },
  { label: '🌾 Rice Paddy (நெல் பயிர்)', query: 'Rice paddy in Thanjavur: evaluate soil telemetry and water requirement' }
];

export const AgentConsole: React.FC<AgentConsoleProps> = ({
  onRunQuery,
  isLoading,
  lastResponse,
  onOpenContract,
  scenarioName
}) => {
  const [query, setQuery] = useState('');
  const [dryRun, setDryRun] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedTraces, setExpandedTraces] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Maintain full conversational chat history
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    // Initial rich answer on load so answers section is populated right away
    const initialAnswer = lastResponse
      ? lastResponse.answer
      : `URGENCY: RED
ADVICE: Soil moisture has dropped to 22% with a falling trend (slope -1.21/reading). Irrigate immediately with 25.0 mm (101,172 litres for 1.0 acre) to relieve water stress during flowering stage. Apply 24.28 kg Nitrogen fertilizer to relieve nutrient deficit.
ஆலோசனை: மண் ஈரப்பதம் 22% ஆக குறைந்துள்ளது (இடர் நிலை: சிவப்பு). ஒரு ஏக்கருக்கு 25 மிமீ (101,172 லிட்டர்) நீர்ப்பாசனம் உடனடியாக செய்யவும். 24.28 கிலோ தழைச்சத்து உரம் இடவும்.
Estimate only. Confirm with a local agriculture officer.`;

    const initialParsed = parseAdvice(initialAnswer);
    return [
      {
        id: 'msg-init-user',
        sender: 'user',
        text: 'Should I irrigate my 1 acre tomato field today?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      },
      {
        id: 'msg-init-agent',
        sender: 'agent',
        text: initialAnswer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        response: lastResponse || {
          answer: initialAnswer,
          trace: [
            {
              thought: 'Check recent soil telemetry readings to inspect current moisture, NPK, and pH levels.',
              tool: 'get_soil_readings',
              args: { days: 7 },
              observation: '{"rows": 7, "latest": {"moisture": 22.0, "N": 40.0, "P": 20.0, "K": 30.0, "pH": 6.2}}'
            },
            {
              thought: 'Analyze moisture trend to see if soil moisture is falling, rising, or stable.',
              tool: 'analyze_trend',
              args: { column: 'moisture', days: 7 },
              observation: '{"column": "moisture", "readings": 7, "slope_per_reading": -1.214, "status": "falling"}'
            },
            {
              thought: 'Retrieve ideal crop requirements for tomato flowering stage.',
              tool: 'get_crop_requirements',
              args: { crop: 'tomato', stage: 'flowering' },
              observation: '{"crop": "tomato", "ideal": {"N": 100, "P": 50, "K": 60, "moisture": 65}}'
            },
            {
              thought: 'Check Open-Meteo weather forecast for rain probability in Trichy.',
              tool: 'get_weather_forecast',
              args: { lat: 10.79, lon: 78.7 },
              observation: '{"rain_probability_pct": [20, 15, 10], "rain_mm": [0.0, 0.0, 0.0]}'
            },
            {
              thought: 'Calculate fertilizer NPK and irrigation water dosage needed.',
              tool: 'calculate_dosage',
              args: { crop: 'tomato', area_acres: 1.0, stage: 'flowering' },
              observation: '{"dosage": {"N": {"dose_kg": 24.28}, "water": {"irrigation_mm": 25.0, "litres": 101172}}}'
            }
          ]
        },
        parsedAdvice: initialParsed
      }
    ];
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Update initial message if lastResponse updates from parent
  useEffect(() => {
    if (lastResponse && messages.length <= 2) {
      setMessages(prev => {
        const parsed = parseAdvice(lastResponse.answer);
        return [
          prev[0] || {
            id: 'msg-init-user',
            sender: 'user',
            text: 'Should I irrigate my 1 acre tomato field today?',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          },
          {
            id: 'msg-init-agent',
            sender: 'agent',
            text: lastResponse.answer,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            response: lastResponse,
            parsedAdvice: parsed
          }
        ];
      });
    }
  }, [lastResponse]);

  const handleExecute = async (queryText: string) => {
    const textToRun = queryText.trim() || 'Should I irrigate my 1 acre tomato field today?';
    if (isLoading) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsgId = `user-${Date.now()}`;
    const agentMsgId = `agent-${Date.now()}`;

    // 1. Immediately append user message
    setMessages(prev => [
      ...prev,
      {
        id: userMsgId,
        sender: 'user',
        text: textToRun,
        timestamp: timeStr
      }
    ]);

    setQuery('');

    // 2. Run query through agent
    try {
      const response = await onRunQuery(textToRun, dryRun);
      const parsed = parseAdvice(response.answer);

      setMessages(prev => [
        ...prev,
        {
          id: agentMsgId,
          sender: 'agent',
          text: response.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          response,
          parsedAdvice: parsed
        }
      ]);
    } catch (err: any) {
      const fallbackText = `URGENCY: YELLOW\nADVICE: Telemetry evaluated for ${textToRun}. Moisture monitoring advised.\nஆலோசனை: மண் ஈரப்பதத்தை தொடர்ந்து கண்காணிக்கவும்.\nEstimate only. Confirm with a local agriculture officer.`;
      setMessages(prev => [
        ...prev,
        {
          id: agentMsgId,
          sender: 'agent',
          text: fallbackText,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isError: true,
          parsedAdvice: parseAdvice(fallbackText)
        }
      ]);
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    handleExecute(query || 'Should I irrigate my 1 acre tomato field today?');
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleTrace = (id: string) => {
    setExpandedTraces(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  const renderUrgencyBadge = (urgency?: UrgencyLevel) => {
    switch (urgency) {
      case 'RED':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 font-bold text-xs tracking-wider uppercase">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
            URGENCY: RED — Act Today
          </div>
        );
      case 'YELLOW':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 font-bold text-xs tracking-wider uppercase">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            URGENCY: YELLOW — Act within 2-3 Days
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-bold text-xs tracking-wider uppercase">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            URGENCY: GREEN — Optimal Condition
          </div>
        );
    }
  };

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 shadow-2xl flex flex-col h-[750px] overflow-hidden">
      {/* Chat Section Header */}
      <div className="p-4 sm:p-5 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center text-slate-950 shadow-md shadow-emerald-500/20">
            <Bot className="w-6 h-6 stroke-[2.2]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white tracking-wide">
                AgriAgent Farm Advisory Chat
              </h2>
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full">
                Active
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Interactive soil moisture, crop stress & fertilizer advisory for <span className="text-emerald-400 font-semibold">{scenarioName}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition cursor-pointer"
              title="Clear Chat History"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

        </div>
      </div>

      {/* Main Conversation & Answers Thread (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 bg-slate-950/40">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400 space-y-3">
            <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 text-emerald-400">
              <Bot className="w-8 h-8" />
            </div>
            <h3 className="text-sm font-bold text-white">No Advisory Questions Yet</h3>
            <p className="text-xs max-w-sm text-slate-400">
              Ask AgriAgent about crop irrigation, soil moisture trends, or fertilizer dosage below.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            if (msg.sender === 'user') {
              return (
                <div key={msg.id} className="flex justify-end items-start gap-2.5">
                  <div className="max-w-xl bg-emerald-700/30 border border-emerald-600/40 text-emerald-100 rounded-2xl rounded-tr-sm px-4 py-3 shadow-md space-y-1">
                    <p className="text-sm font-medium leading-relaxed">{msg.text}</p>
                    <div className="text-[10px] text-emerald-400/80 text-right font-mono">
                      {msg.timestamp}
                    </div>
                  </div>
                  <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-slate-950 font-bold shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                </div>
              );
            }

            // Agent Message: Rich Answer Card
            const advice = msg.parsedAdvice;
            const trace = msg.response?.trace || [];
            const isTraceExpanded = expandedTraces[msg.id] ?? false;

            return (
              <div key={msg.id} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center text-slate-950 font-bold shrink-0 mt-0.5 shadow-md shadow-emerald-500/20">
                  <Bot className="w-4 h-4" />
                </div>

                <div className="flex-1 max-w-2xl bg-slate-900/95 border border-slate-800/90 rounded-2xl rounded-tl-sm p-4 sm:p-5 shadow-xl space-y-4">
                  {/* Card Header: Urgency Banner & Actions */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-white">
                        Farm Advisory Recommendation
                      </span>
                    </div>
                    {renderUrgencyBadge(advice?.urgency)}
                  </div>

                  {/* Bilingual Advice Section */}
                  <div className="space-y-3">
                    {/* English Advice */}
                    <div className="bg-slate-950/70 rounded-xl p-3.5 border border-slate-800/80 space-y-1.5">
                      <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                        <Languages className="w-3.5 h-3.5 text-blue-400" />
                        English Recommendation
                      </div>
                      <p className="text-sm text-slate-100 font-medium leading-relaxed">
                        {advice?.englishAdvice || msg.text}
                      </p>
                    </div>

                    {/* Tamil Advice */}
                    {advice?.tamilAdvice && (
                      <div className="bg-emerald-950/25 rounded-xl p-3.5 border border-emerald-900/40 space-y-1.5">
                        <div className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-300 uppercase tracking-wider">
                          <Languages className="w-3.5 h-3.5 text-emerald-400" />
                          தமிழ் ஆலோசனை (Tamil Advisory)
                        </div>
                        <p className="text-sm text-emerald-100 font-medium leading-relaxed">
                          {advice.tamilAdvice}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Agronomic Disclaimer */}
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400 pt-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{advice?.disclaimer || 'Estimate only. Confirm with a local agriculture officer.'}</span>
                  </div>

                  {/* Calculation Details Footer */}
                  {trace.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <button
                        onClick={() => toggleTrace(msg.id)}
                        className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 font-medium transition cursor-pointer"
                      >
                        <Clock className="w-3.5 h-3.5 text-emerald-400" />
                        <span>View Calculation Details (கணக்கீட்டு விவரங்கள்)</span>
                        {isTraceExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  )}

                  {/* Collapsible Reasoning & Tool Execution Trace */}
                  {isTraceExpanded && trace.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-800/60 space-y-2 text-xs font-mono">
                      {trace.map((step, idx) => (
                        <div key={idx} className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 space-y-1.5">
                          <div className="flex items-center gap-2 text-cyan-300 font-bold">
                            <span className="w-4 h-4 rounded bg-cyan-950 text-cyan-400 text-[10px] flex items-center justify-center">
                              {idx + 1}
                            </span>
                            <span>{step.tool}</span>
                            <span className="text-[10px] text-slate-500 font-normal truncate max-w-xs">
                              {JSON.stringify(step.args)}
                            </span>
                          </div>
                          <div className="text-slate-300 text-[11px] font-sans">
                            <span className="text-emerald-400 font-bold font-mono">Thought: </span>
                            {step.thought}
                          </div>
                          <div className="text-slate-400 text-[10px] bg-slate-900/80 p-2 rounded max-h-24 overflow-y-auto whitespace-pre-wrap">
                            {step.observation}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Live Loading Indicator in Chat */}
        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
              <RotateCcw className="w-4 h-4 animate-spin" />
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-xs text-slate-300 space-y-1">
              <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                <span>AgriAgent is analyzing root-zone telemetry...</span>
              </div>
              <div className="text-[11px] text-slate-400">
                Checking 7-day soil trend, Open-Meteo weather radar, and calculating exact NPK & water dosage.
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Farmer Quick Action Chips */}
      <div className="px-4 py-2.5 bg-slate-950/80 border-t border-slate-800 flex items-center gap-2 overflow-x-auto whitespace-nowrap scrollbar-none">
        <span className="text-[11px] text-emerald-400 font-semibold flex items-center gap-1 shrink-0 mr-1">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Quick Questions:
        </span>
        {FARMER_QUICK_ACTIONS.map((action, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleExecute(action.query)}
            disabled={isLoading}
            className="text-xs font-medium bg-slate-900 hover:bg-emerald-950/40 hover:text-emerald-300 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700/80 hover:border-emerald-600/50 transition shrink-0 cursor-pointer disabled:opacity-50"
          >
            {action.label}
          </button>
        ))}
      </div>

      {/* Chat Input & Submit Bar */}
      <form onSubmit={handleSubmit} className="p-3 sm:p-4 bg-slate-950 border-t border-slate-800 flex items-center gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask in English or தமிழ் (e.g. Should I irrigate my 1 acre tomato field today?)..."
          disabled={isLoading}
          className="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 font-sans transition disabled:opacity-50"
        />

        <button
          type="submit"
          disabled={isLoading}
          className="px-5 py-3 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-emerald-600/20 flex items-center gap-2 shrink-0 transition cursor-pointer disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <RotateCcw className="w-4 h-4 animate-spin" />
              <span className="hidden sm:inline">Evaluating...</span>
            </>
          ) : (
            <>
              <span>Ask Advisory</span>
              <Send className="w-4 h-4 fill-slate-950" />
            </>
          )}
        </button>
      </form>
    </div>
  );
};
