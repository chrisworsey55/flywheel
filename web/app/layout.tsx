import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FLYWHEEL Transmission",
  description: "Agent-readable brief for the FLYWHEEL self-improving growth engine"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
