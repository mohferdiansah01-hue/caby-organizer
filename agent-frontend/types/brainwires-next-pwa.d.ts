declare module "@brainwires/next-pwa" {
  import type { NextConfig } from "next";
  function withPWAInit(config?: Record<string, unknown>): (nextConfig: NextConfig) => NextConfig;
  export default withPWAInit;
}
