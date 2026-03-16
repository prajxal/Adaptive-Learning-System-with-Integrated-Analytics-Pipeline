import { useAuth } from "@clerk/clerk-react";
import { useEffect } from "react";
import { setClerkToken } from "../services/api";

export default function TokenSynchronizer() {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    async function syncToken() {
      if (!isSignedIn) {
        setClerkToken(null);
        return;
      }

      const token = await getToken();
      setClerkToken(token);
    }

    syncToken();
  }, [isSignedIn, getToken]);

  return null;
}
