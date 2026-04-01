import React, { useEffect, useRef, useState } from "react";
import { Bot, MessageSquare, Send, User } from "lucide-react";
import { sendChatMessage } from "../../services/chatApi";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const WELCOME: Message = {
  role: "assistant",
  content:
    "Hi! I'm your AI learning mentor. Ask me about your progress, what to learn next, or anything about your roadmap.",
};

const PAGE_STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');
  .mentor-root { font-family: 'DM Sans', sans-serif; }
  .mentor-title { font-family: 'Sora', sans-serif; }
  .typing-dot { animation: typing-bounce 1.2s infinite ease-in-out; }
  .typing-dot:nth-child(2) { animation-delay: 0.2s; }
  .typing-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes typing-bounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30% { transform: translateY(-6px); opacity: 1; }
  }
`;

export default function AIMentorPage() {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    try {
      const reply = await sendChatMessage(text);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I ran into an error. Please try again in a moment.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="mentor-root flex flex-col h-[calc(100vh-130px)]">
      <style>{PAGE_STYLES}</style>

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-[#111118] border border-[#1e1e2e] flex items-center justify-center">
          <MessageSquare className="w-5 h-5 text-[#6366f1]" />
        </div>
        <div>
          <h1 className="mentor-title text-xl font-bold text-[#f1f5f9]">AI Mentor</h1>
          <p className="text-xs text-[#64748b]">Powered by your real learning data</p>
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 pb-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
          >
            {/* Avatar */}
            <div
              className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
                msg.role === "user"
                  ? "bg-[#6366f1]/20 border border-[#6366f1]/40"
                  : "bg-[#111118] border border-[#1e1e2e]"
              }`}
            >
              {msg.role === "user" ? (
                <User className="w-4 h-4 text-[#6366f1]" />
              ) : (
                <Bot className="w-4 h-4 text-[#64748b]" />
              )}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-[#6366f1] text-white rounded-tr-sm"
                  : "bg-[#111118] border border-[#1e1e2e] text-[#cbd5e1] rounded-tl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-3 flex-row">
            <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center bg-[#111118] border border-[#1e1e2e]">
              <Bot className="w-4 h-4 text-[#64748b]" />
            </div>
            <div className="bg-[#111118] border border-[#1e1e2e] px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-1.5">
              <span className="typing-dot w-2 h-2 rounded-full bg-[#64748b] inline-block" />
              <span className="typing-dot w-2 h-2 rounded-full bg-[#64748b] inline-block" />
              <span className="typing-dot w-2 h-2 rounded-full bg-[#64748b] inline-block" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-[#1e1e2e] pt-4">
        <div className="flex gap-3 items-end bg-[#111118] border border-[#1e1e2e] rounded-xl px-4 py-3 focus-within:border-[#6366f1]/50 transition-colors">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your progress, next steps, or any course..."
            rows={1}
            disabled={loading}
            className="flex-1 bg-transparent text-[#f1f5f9] placeholder-[#475569] text-sm resize-none outline-none max-h-32 overflow-y-auto disabled:opacity-50"
            style={{ lineHeight: "1.5" }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="w-8 h-8 rounded-lg flex items-center justify-center bg-[#6366f1] hover:bg-[#4f46e5] disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
        <p className="text-[10px] text-[#334155] mt-2 text-center">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
