import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sine01 · AI PPT Workflow",
  description: "Visual-first AI presentation workflow prototype"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
