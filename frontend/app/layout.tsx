import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Isometric MTO Generator",
  description: "Upload a piping isometric drawing and generate an automated MTO."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
