import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Caby Organizer",
    short_name: "Caby",
    description: "Aplikasi kepanitiaan: pantau kerja, atur jadwal, dan kumpulkan hasil kerja tim",
    start_url: "/",
    display: "standalone",
    background_color: "#0f172a",
    theme_color: "#0d9488",
    orientation: "portrait",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}