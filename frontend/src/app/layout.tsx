import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI-Based Automatic Question Paper Difficulty Analyzer",
  description:
    "Automated question paper difficulty analyzer using revised Bloom's Taxonomy classification.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
