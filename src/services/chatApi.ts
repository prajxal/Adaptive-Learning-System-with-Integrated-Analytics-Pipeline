import BACKEND_URL, { fetchWithAuth } from "./api";

export async function sendChatMessage(message: string): Promise<string> {
  const res = await fetchWithAuth(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => "");
    throw new Error(`Chat request failed (${res.status}): ${err}`);
  }
  const data = await res.json();
  return data.reply as string;
}
