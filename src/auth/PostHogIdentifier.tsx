import { useUser } from "@clerk/clerk-react";
import { usePostHog } from "@posthog/react";
import { useEffect } from "react";

export default function PostHogIdentifier() {
  const { user, isLoaded, isSignedIn } = useUser();
  const posthog = usePostHog();

  useEffect(() => {
    if (isLoaded && isSignedIn && user) {
      posthog.identify(user.id, {
        email: user.primaryEmailAddress?.emailAddress,
        name: user.fullName,
        username: user.username
      });
    } else if (isLoaded && !isSignedIn) {
      posthog.reset();
    }
  }, [isLoaded, isSignedIn, user, posthog]);

  return null;
}
