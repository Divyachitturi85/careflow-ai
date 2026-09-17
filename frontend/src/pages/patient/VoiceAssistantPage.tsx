import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { 
  Mic, 
  MicOff, 
  Send, 
  Bot, 
  User as UserIcon, 
  Calendar, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  Volume2, 
  VolumeX, 
  Sparkles, 
  ArrowRight,
  RefreshCw,
  PhoneCall,
  FileCheck
} from 'lucide-react';
import { AvailabilitySlot, Appointment } from '../../types';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  slots?: AvailabilitySlot[];
  appointment?: Appointment;
  isRefusal?: boolean;
  intent?: string;
  toolCalls?: Array<{ name: string; result: any }>;
}

type PipelineStage = 
  | 'IDLE'
  | 'LISTENING'
  | 'TRANSCRIBING'
  | 'POLICY_CHECK'
  | 'SCHEDULING_QUERY'
  | 'BOOKING_RESERVATION'
  | 'EHR_VERIFICATION'
  | 'CONFIRMED';

export const VoiceAssistantPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: `Hello ${user?.first_name || 'there'}! I am your CareFlow AI healthcare access assistant. How can I help you today? I can discover approved specialists, check real database availability, book your appointments, and connect you with pre-visit intake.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<PipelineStage>('IDLE');
  const [conversationId, setConversationId] = useState<string>(() => crypto.randomUUID());
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pipelineStage]);

  // Speech Recognition setup (Web Speech API)
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recog = new SpeechRecognition();
      recog.continuous = false;
      recog.interimResults = true;
      recog.lang = 'en-US';

      recog.onstart = () => {
        setIsListening(true);
        setPipelineStage('LISTENING');
      };

      recog.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join('');
        setInputText(transcript);
        setPipelineStage('TRANSCRIBING');
      };

      recog.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        setIsListening(false);
        setPipelineStage('IDLE');
      };

      recog.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recog;
    }
  }, []);

  const speakText = (text: string) => {
    if (!ttsEnabled || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel(); // Barge-in: interrupt previous speech
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  };

  const toggleListening = () => {
    stopSpeaking();
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      setPipelineStage('IDLE');
    } else {
      if (!recognitionRef.current) {
        alert('Speech recognition is not supported in this browser. Please use Chrome, Edge, or text input.');
        return;
      }
      try {
        recognitionRef.current.start();
      } catch (err) {
        console.error('Failed to start recognition:', err);
      }
    }
  };

  const handleSendMessage = async (customMessage?: string) => {
    const textToSend = customMessage || inputText;
    if (!textToSend.trim() || isLoading) return;

    stopSpeaking();
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    }

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsLoading(true);

    // Dynamic pipeline progression visualizer
    setPipelineStage('POLICY_CHECK');
    await new Promise((r) => setTimeout(r, 200));

    if (textToSend.toLowerCase().includes('book') || textToSend.toLowerCase().includes('first') || textToSend.toLowerCase().includes('pm')) {
      setPipelineStage('BOOKING_RESERVATION');
    } else {
      setPipelineStage('SCHEDULING_QUERY');
    }

    try {
      const res = await api.chatWithAI(textToSend, conversationId);

      if (res.appointment) {
        setPipelineStage('EHR_VERIFICATION');
        await new Promise((r) => setTimeout(r, 300));
        setPipelineStage('CONFIRMED');
      } else {
        setPipelineStage('IDLE');
      }

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        sender: 'assistant',
        text: res.message,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        slots: res.slots,
        appointment: res.appointment,
        isRefusal: !res.is_safe,
        intent: res.intent,
        toolCalls: res.tool_calls,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      speakText(res.message);
    } catch (err: any) {
      setPipelineStage('IDLE');
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: 'assistant',
          text: `I encountered an issue processing your request: ${err.message || 'Server error'}. Please try again.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSlotSelect = (slot: AvailabilitySlot) => {
    handleSendMessage(`Book the appointment on ${slot.formatted_time}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 sm:px-6 flex flex-col h-[calc(100vh-5rem)]">
      {/* Top Banner: Pipeline & Capabilities */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-200 mb-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className={`h-10 w-10 rounded-xl flex items-center justify-center text-white ${
              isListening ? 'bg-rose-500 animate-pulse' : 'bg-teal-600'
            }`}>
              {isListening ? <Mic className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
            </div>
            {isListening && (
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500" />
              </span>
            )}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-slate-900">Voice & Agentic AI Assistant</h2>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-teal-100 text-teal-800">
                Patient Intake
              </span>
            </div>
            {/* Live Pipeline Visualizer */}
            <div className="flex items-center space-x-1 text-xs text-slate-500 mt-0.5">
              <span className="font-medium text-slate-700">Stage:</span>
              <span className={`font-semibold ${
                pipelineStage === 'IDLE' ? 'text-slate-500' :
                pipelineStage === 'LISTENING' ? 'text-rose-600 animate-pulse' :
                pipelineStage === 'POLICY_CHECK' ? 'text-amber-600' :
                pipelineStage === 'SCHEDULING_QUERY' ? 'text-blue-600' :
                pipelineStage === 'BOOKING_RESERVATION' ? 'text-indigo-600' :
                pipelineStage === 'EHR_VERIFICATION' ? 'text-purple-600' :
                'text-emerald-600 font-bold'
              }`}>
                {pipelineStage === 'IDLE' && '● Ready (Click Mic or Type)'}
                {pipelineStage === 'LISTENING' && '● Listening to Patient Voice...'}
                {pipelineStage === 'TRANSCRIBING' && '● Transcribing Speech...'}
                {pipelineStage === 'POLICY_CHECK' && '● Clinical Boundary & Policy Inspection...'}
                {pipelineStage === 'SCHEDULING_QUERY' && '● Querying Real Availability Slots...'}
                {pipelineStage === 'BOOKING_RESERVATION' && '● Reserving Atomic Slot...'}
                {pipelineStage === 'EHR_VERIFICATION' && '● Verifying with Mock EHR System...'}
                {pipelineStage === 'CONFIRMED' && '✓ Confirmed & Synchronized!'}
              </span>
            </div>
          </div>
        </div>

        {/* TTS Toggle & Session info */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setTtsEnabled(!ttsEnabled)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 border transition-colors ${
              ttsEnabled ? 'bg-teal-50 border-teal-200 text-teal-700' : 'bg-slate-50 border-slate-200 text-slate-500'
            }`}
          >
            {ttsEnabled ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
            <span>Voice Speech: {ttsEnabled ? 'ON' : 'MUTED'}</span>
          </button>
          <button
            onClick={() => {
              setConversationId(crypto.randomUUID());
              setMessages([
                {
                  id: crypto.randomUUID(),
                  sender: 'assistant',
                  text: 'New conversation started. How can I assist you today?',
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                },
              ]);
            }}
            title="Reset Conversation"
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Main Chat Scroll Area */}
      <div className="flex-1 overflow-y-auto bg-slate-50/50 rounded-2xl p-4 border border-slate-200 mb-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div className="flex items-start space-x-2 max-w-[85%]">
              {msg.sender === 'assistant' && (
                <div className="h-8 w-8 rounded-full bg-teal-600 flex-shrink-0 flex items-center justify-center text-white text-xs shadow-sm mt-0.5">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              <div>
                {/* Text Bubble */}
                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                    msg.sender === 'user'
                      ? 'bg-teal-600 text-white rounded-tr-none'
                      : msg.isRefusal
                      ? 'bg-amber-50 border border-amber-200 text-amber-900 rounded-tl-none'
                      : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                  }`}
                >
                  {msg.isRefusal && (
                    <div className="flex items-center space-x-1.5 text-amber-700 font-semibold mb-1 text-xs">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Clinical Boundary Enforced</span>
                    </div>
                  )}

                  <div className="whitespace-pre-wrap">{msg.text}</div>
                </div>

                {/* Available Slots Cards (Interactive) */}
                {msg.slots && msg.slots.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center space-x-1">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>Real Available Slots from Scheduling Engine:</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {msg.slots.map((slot) => (
                        <div
                          key={slot.slot_id}
                          className="bg-white border border-slate-200 rounded-xl p-3 hover:border-teal-500 hover:shadow-md transition-all flex flex-col justify-between"
                        >
                          <div>
                            <div className="font-semibold text-sm text-slate-900">{slot.doctor_name}</div>
                            <div className="text-xs text-teal-600 font-medium">{slot.specialty} • {slot.hospital_name}</div>
                            <div className="text-xs text-slate-600 mt-1 flex items-center space-x-1">
                              <Clock className="h-3 w-3" />
                              <span>{slot.formatted_time}</span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleSlotSelect(slot)}
                            className="mt-3 w-full py-1.5 bg-teal-50 hover:bg-teal-600 text-teal-700 hover:text-white rounded-lg text-xs font-semibold transition-colors flex items-center justify-center space-x-1"
                          >
                            <span>Select & Book Slot</span>
                            <ArrowRight className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Confirmed Appointment Banner */}
                {msg.appointment && (
                  <div className="mt-3 bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl p-4 shadow-sm">
                    <div className="flex items-center space-x-2 text-emerald-800 font-bold text-sm">
                      <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                      <span>Appointment Confirmed & Synchronized</span>
                    </div>

                    <div className="mt-2 text-xs space-y-1 text-slate-700">
                      <div><span className="font-medium">External EHR ID:</span> <code className="bg-white px-1.5 py-0.5 rounded border border-emerald-200 font-mono text-emerald-900 font-semibold">{msg.appointment.external_appointment_id || 'EXT-APT-CONFIRMED'}</code></div>
                      <div><span className="font-medium">Internal Correlation ID:</span> <code className="text-slate-500 font-mono">{msg.appointment.correlation_id}</code></div>
                    </div>

                    {/* Pre-Visit Questionnaire CTA */}
                    <div className="mt-3 pt-3 border-t border-emerald-200/60 flex items-center justify-between">
                      <span className="text-xs text-emerald-900 font-medium">Pre-visit intake required before your visit:</span>
                      <button
                        onClick={() => navigate(`/questionnaire?appointment_id=${msg.appointment?.id}`)}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center space-x-1.5"
                      >
                        <FileCheck className="h-3.5 w-3.5" />
                        <span>Complete Intake</span>
                      </button>
                    </div>
                  </div>
                )}

                <div className="text-[10px] text-slate-400 mt-1 px-1">{msg.timestamp}</div>
              </div>

              {msg.sender === 'user' && (
                <div className="h-8 w-8 rounded-full bg-slate-200 flex-shrink-0 flex items-center justify-center text-slate-700 text-xs shadow-sm mt-0.5">
                  <UserIcon className="h-4 w-4" />
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center space-x-2 text-slate-500 text-xs italic">
            <div className="h-4 w-4 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
            <span>CareFlow AI is processing with scheduling service and safety guard...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Prompts */}
      <div className="mb-3 flex items-center space-x-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
        <span className="text-slate-400 text-[11px] font-medium whitespace-nowrap">Suggested Prompts:</span>
        <button
          onClick={() => handleSendMessage('I need to see an orthopedic doctor this week')}
          className="px-2.5 py-1 bg-white hover:bg-teal-50 border border-slate-200 hover:border-teal-300 rounded-full text-slate-700 hover:text-teal-800 transition-colors whitespace-nowrap shadow-2xs"
        >
          🔍 "Orthopedic doctor this week"
        </button>
        <button
          onClick={() => handleSendMessage('Book the first one')}
          className="px-2.5 py-1 bg-white hover:bg-teal-50 border border-slate-200 hover:border-teal-300 rounded-full text-slate-700 hover:text-teal-800 transition-colors whitespace-nowrap shadow-2xs"
        >
          ⚡ "Book the first one"
        </button>
        <button
          onClick={() => handleSendMessage('What appointments do I have?')}
          className="px-2.5 py-1 bg-white hover:bg-teal-50 border border-slate-200 hover:border-teal-300 rounded-full text-slate-700 hover:text-teal-800 transition-colors whitespace-nowrap shadow-2xs"
        >
          📋 "What appointments do I have?"
        </button>
        <button
          onClick={() => handleSendMessage('What medicine should I take for joint pain?')}
          className="px-2.5 py-1 bg-white hover:bg-amber-50 border border-slate-200 hover:border-amber-300 rounded-full text-slate-700 hover:text-amber-800 transition-colors whitespace-nowrap shadow-2xs"
        >
          🛡️ "What medicine should I take?" (Safety Refusal)
        </button>
        <button
          onClick={() => handleSendMessage('Can you connect me to a human representative?')}
          className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-full text-slate-700 transition-colors whitespace-nowrap shadow-2xs"
        >
          👤 "Human escalation"
        </button>
      </div>

      {/* Input Form with Microphone Button */}
      <div className="bg-white rounded-2xl p-2 shadow-sm border border-slate-200 flex items-center space-x-2">
        {/* Microphone Button */}
        <button
          onClick={toggleListening}
          title={isListening ? 'Stop listening' : 'Start speaking'}
          className={`h-11 w-11 rounded-xl flex items-center justify-center transition-all shadow-sm ${
            isListening
              ? 'bg-rose-600 text-white animate-pulse ring-4 ring-rose-100'
              : 'bg-teal-50 text-teal-700 hover:bg-teal-100'
          }`}
        >
          {isListening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
        </button>

        {/* Text Input */}
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isListening ? 'Listening to your speech... or type here' : 'Type your request (e.g. "I need an orthopedic doctor", "Book Friday at 3")'}
          className="flex-1 px-3 py-2 text-sm bg-transparent outline-none text-slate-900 placeholder:text-slate-400"
        />

        {/* Send Button */}
        <button
          onClick={() => handleSendMessage()}
          disabled={!inputText.trim() || isLoading}
          className="h-11 px-4 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-medium rounded-xl text-sm transition-colors flex items-center space-x-1.5 shadow-sm"
        >
          <span>Send</span>
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};
