import { Toaster as Sonner, ToasterProps } from "sonner";

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      toastOptions={{
        style: {
          background: "#111118",
          border: "1px solid #1e1e2e",
          color: "#f1f5f9",
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
