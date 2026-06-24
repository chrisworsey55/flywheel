import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FLYWHEEL Growth Experiment Swarm",
  description: "Honest growth-experiment evolution dashboard"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

