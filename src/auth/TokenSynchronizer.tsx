import { useAuth } from "@clerk/clerk-react";
import { useEffect } from "react";
import { setClerkTokenFn } from "../services/api";

export default function TokenSynchronizer() {
  const { getToken } = useAuth();

  useEffect(() => {
    setClerkTokenFn(getToken);
  }, [getToken]);

  return null;
}
