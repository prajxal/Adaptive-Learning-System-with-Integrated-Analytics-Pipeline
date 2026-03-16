import { SignIn } from "@clerk/clerk-react";
import { AuthLayout } from "../components/auth/AuthLayout";

export function Login() {
  return (
    <AuthLayout>
      <div className="flex justify-center w-full">
        <SignIn routing="path" path="/signin" signUpUrl="/signup" />
      </div>
    </AuthLayout>
  );
}
