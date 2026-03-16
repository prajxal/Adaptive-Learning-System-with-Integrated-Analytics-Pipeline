import { SignUp } from "@clerk/clerk-react";
import { AuthLayout } from "../components/auth/AuthLayout";

export function Signup() {
  return (
    <AuthLayout>
      <div className="flex justify-center w-full">
        <SignUp routing="path" path="/signup" signInUrl="/signin" />
      </div>
    </AuthLayout>
  );
}
